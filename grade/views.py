from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from .models import Unidade, Disciplina, HorarioAula, Professor, AlocacaoGrade, Disponibilidade, DisponibilidadeHorario
from datetime import date, datetime
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .restricoes import MotorRestricoes
from .jornada import jornada
from .services import GradeService, GradeServiceError, AlocacaoService

@never_cache
@staff_member_required(login_url='grade:inicio')
@require_http_methods(['GET', 'POST'])
def exibir_grade(request):
    from .automacao import CHAVE_PREVIA, VALIDADE_SEGUNDOS, assinatura_dados, assinatura_atual_previa, contexto_automacao
    from .replicacao import contexto_replicacao, aplicar_previa_replicacao
    from .distribuicao import dados_distribuicao, url_grade
    from .edicao import contexto_editor, salvar_disponibilidades
    from django.core.exceptions import ValidationError
    from django.contrib import messages

    # Carrega dados base
    unidades = Unidade.objects.all()
    horarios = HorarioAula.objects.order_by('hora_inicio', 'hora_fim', 'pk')
    professores = Professor.objects.prefetch_related('disciplinas', 'unidades_permitidas').order_by("nome")

    # Captura a data vinda da URL ou do formulário POST
    previa_sessao = request.session.get(CHAVE_PREVIA)
    data_str = (request.GET.get('data') or request.POST.get('data_grade')
                or request.GET.get('semana') or request.POST.get('semana')
                or (previa_sessao['inicio'] if previa_sessao else None))

    if data_str:
        try:
            data_atual_projeto = datetime.strptime(
                data_str,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            data_atual_projeto = timezone.localdate()
    else:
        data_atual_projeto = timezone.localdate()

    if not date(1900, 1, 8) <= data_atual_projeto <= date(2100, 12, 24):
        data_atual_projeto = timezone.localdate()

    por = request.GET.get('por', request.POST.get('por', 'unidade'))
    entidade = request.GET.get('entidade', request.POST.get('entidade', ''))
    destino = url_grade(data_atual_projeto, por, entidade, request.GET.get('visao', request.POST.get('visao')))
    replica = contexto_replicacao(request, data_atual_projeto)
    if not isinstance(replica, dict):
        return replica
    # A semana confirmada é a proposta privada do servidor, não um campo editável do POST.
    if request.POST.get('acao') == 'salvar' and previa_sessao:
        destino = url_grade(date.fromisoformat(previa_sessao['inicio']), por, entidade, request.GET.get('visao', request.POST.get('visao')))
    auto = contexto_automacao(request, destino=destino,
                             processar=(not replica['replicacao_previa'] and (request.POST.get('acao') in ('gerar', 'salvar', 'descartar') or request.method == 'GET')))
    if not isinstance(auto, dict):
        return auto
    aplicar_previa_replicacao(auto, request)
    if replica['replicacao_previa'] and request.POST.get('acao') in ('gerar', 'salvar'):
        replica['erro_replicacao'] = 'Confirme ou descarte a replicação aberta antes de gerar outra proposta.'
    previa = auto['previa']
    if request.POST.get('acao') == 'gerar' and previa and auto['form'].is_valid():
        inicio_gerado = date.fromisoformat(previa['inicio'])
        if (data_atual_projeto - inicio_gerado).days not in range(7):
            data_atual_projeto = inicio_gerado
    import time
    auto['previa_expirada'] = bool(previa and time.time()-previa['criada_em'] > VALIDADE_SEGUNDOS)
    auto['previa_desatualizada'] = bool(previa and (
        assinatura_atual_previa(previa) != previa['assinatura'] or auto['previa_expirada']))
    if auto['previa_desatualizada']:
        auto['pode_salvar'] = False
    editor = contexto_editor(request, auto, data_atual_projeto)
    if not isinstance(editor, dict):
        return editor

    sucesso = False
    erro_negocio = None
    avisos_negocio = []
    if request.POST.get('acao') == 'salvar_disponibilidade':
        try:
            salvar_disponibilidades(request, data_atual_projeto, previa)
        except ValidationError as exc:
            erro_negocio = ' '.join(exc.messages)
        else:
            messages.success(request, 'Disponibilidades do dia atualizadas. As aulas foram preservadas.')
            return redirect(destino)

    # POST - Salvar dados usando a camada de serviço
    if request.method == "POST" and 'acao' not in request.POST and "senha_acesso" not in request.POST:
        try:
            if previa:
                raise GradeServiceError('Há uma prévia pendente. Confirme ou descarte a proposta antes de salvar alterações manuais.')
            avisos_negocio = GradeService.salvar_grade_diaria(
                data_alvo=data_atual_projeto,
                post_data=request.POST,
                professores=professores,
                horarios=horarios,
                unidades=unidades
            )

            sucesso = True

        except GradeServiceError as e:
            erro_negocio = ' '.join(e.messages)

    # Buscar dados do dia selecionado
    (
        disp_manha_salvas,
        disp_tarde_salvas,
        alocacoes_salvas
    ) = AlocacaoService.obter_dicionarios_de_visualizacao(
        data_atual_projeto
    )

    if erro_negocio and not previa and 'acao' not in request.POST:
        # Mantém a tentativa na tela para o coordenador corrigir sem perder a edição.
        disp_manha_salvas = {p.pk: request.POST.get(f'disp_manha_{p.pk}') == 'on' for p in professores}
        disp_tarde_salvas = {p.pk: request.POST.get(f'disp_tarde_{p.pk}') == 'on' for p in professores}
        alocacoes_salvas = {}
        for horario in horarios:
            for unidade in unidades:
                valor = request.POST.get(f'alocacao_{horario.pk}_{unidade.pk}', '')
                if valor.isdecimal():
                    alocacoes_salvas.setdefault(horario.pk, {})[unidade.pk] = int(valor)
    especificas = {f'{d.professor_id}_{d.horario_id}': d.disponivel
                   for d in DisponibilidadeHorario.objects.filter(data=data_atual_projeto)}
    if not erro_negocio and not sucesso:
        avisos_negocio = MotorRestricoes(inicio=data_atual_projeto, fim=data_atual_projeto).avisos_parentesco(
            AlocacaoGrade.objects.filter(data=data_atual_projeto))

    context = {
        "unidades": unidades,
        "horarios": horarios,
        "professores": professores,
        "data_grade": data_atual_projeto.strftime("%Y-%m-%d"),
        "alocacoes_salvas": alocacoes_salvas,
        "disp_manha_salvas": disp_manha_salvas,
        "disp_tarde_salvas": disp_tarde_salvas,
        "sucesso": sucesso,
        "erro_negocio": erro_negocio,
        "avisos_negocio": avisos_negocio,
        "disponibilidades_especificas": especificas,
        "jornada": jornada(),
    }
    context.update(auto)
    context.update(replica)
    context.update(editor)
    context.update(dados_distribuicao(request, data_atual_projeto, auto))
    from .aprovacao import contexto_aprovacao
    aprovacao = contexto_aprovacao(request, data_atual_projeto, previa)
    if not isinstance(aprovacao, dict):
        return aprovacao
    context.update(aprovacao)
    from .indicadores import contexto_indicadores
    context.update(contexto_indicadores(data_atual_projeto, auto, aprovacao))
    if context['previa_visivel']:
        # Preenche também os selects da edição diária, sem transformar proposta em aula legada.
        for aula in auto['linhas']:
            if aula['data'] == data_atual_projeto and aula['professor']:
                alocacoes_salvas.setdefault(aula['horario'].pk, {}).setdefault(aula['unidade'].pk, aula['professor'].pk)
    context['aulas_dia'] = AlocacaoGrade.objects.filter(data=data_atual_projeto).select_related(
        'horario', 'professor', 'unidade', 'turma__curso', 'disciplina')
    from datetime import timedelta
    context['assinatura_disponibilidade'] = assinatura_dados(data_atual_projeto - timedelta(days=data_atual_projeto.weekday()))
    from .models import Turma
    from pathlib import Path
    turmas_ativas = Turma.objects.filter(demandas__ativa=True).distinct()
    context['turmas_flexiveis_home'] = turmas_ativas.filter(materias_fixas=False).count()
    context['turmas_fixas_home'] = turmas_ativas.filter(materias_fixas=True).count()
    pasta_static = Path(__file__).parent / 'static' / 'grade'
    context['versao_assets_grade'] = str(max((pasta_static / n).stat().st_mtime_ns
                                             for n in ('distribuicao.css', 'distribuicao.js')))

    return render(
        request,
        "grade/grade_tabela.html",
        context
    )


@staff_member_required(login_url='grade:inicio')
def cadastrar_professor(request):
    from .professores import cadastro_professor
    return cadastro_professor(request)

@staff_member_required(login_url='grade:inicio')
def cadastrar_disciplina(request):
    sucesso = False
    erro = None

    if request.method == "POST":
        try:
            nome = request.POST.get("nome", "").strip()
            area = request.POST.get("area", "").strip()

            # Validação básica
            if not nome:
                raise ValueError(
                    "O nome da disciplina é obrigatório."
                )

            if area not in ["EXATAS", "HUMANAS", "BIOLOGICAS"]:
                raise ValueError(
                    "Selecione uma área válida."
                )

            # Criação da disciplina
            Disciplina.objects.create(
                nome=nome,
                area=area
            )

            sucesso = True

        except ValueError as e:
            erro = str(e)

        except Exception as e:
            erro = f"Não foi possível cadastrar a disciplina: {e}"

    contexto = {
        "sucesso": sucesso,
        "erro": erro,
    }

    return render(
        request,
        "grade/cadastrar_disciplina.html",
        contexto
    )
@staff_member_required(login_url='grade:inicio')
def lista_professores(request):
    professores = (
        Professor.objects
        .prefetch_related("disciplinas", "unidades_permitidas")
        .select_related("unidade_oficial", "parente_vinculado")
        .order_by("nome")
    )

    contexto = {
        "professores": professores,
    }

    return render(
        request,
        "grade/lista_professores.html",
        contexto
    )
@staff_member_required(login_url='grade:inicio')
def atualizar_professor(request, professor_id=None):
    if professor_id is None:
        return render(request, 'grade/selecionar_professor_atualizar.html', {'professores': Professor.objects.order_by('nome')})
    from .professores import cadastro_professor
    return cadastro_professor(request, professor_id)

@staff_member_required(login_url='grade:inicio')
def excluir_professor(request, professor_id=None):
    professores = Professor.objects.all().order_by("nome")

    # Se nenhum professor foi selecionado,
    # mostra a lista para escolha.
    if professor_id is None:

        contexto = {
            "professores": professores,
        }

        return render(
            request,
            "grade/selecionar_professor_excluir.html",
            contexto
        )

    # Busca o professor escolhido.
    try:
        professor = Professor.objects.get(
            id=professor_id
        )
    except Professor.DoesNotExist:

        contexto = {
            "professores": professores,
            "erro": "Professor não encontrado."
        }

        return render(
            request,
            "grade/selecionar_professor_excluir.html",
            contexto
        )

    # A exclusão só acontece através do POST.
    if request.method == "POST":

        nome_professor = professor.nome

        try:
            professor.delete()

            return render(
                request,
                "grade/excluir_professor_sucesso.html",
                {
                    "nome_professor": nome_professor
                }
            )

        except Exception as e:

            return render(
                request,
                "grade/confirmar_exclusao_professor.html",
                {
                    "professor": professor,
                    "erro": (
                        "Não foi possível excluir o professor: "
                        f"{e}"
                    )
                }
            )

    contexto = {
        "professor": professor,
    }

    return render(
        request,
        "grade/confirmar_exclusao_professor.html",
        contexto
    )
@staff_member_required(login_url='grade:inicio')
def cadastrar_unidade(request):
    from .unidades import cadastro_unidade
    return cadastro_unidade(request)

@staff_member_required(login_url='grade:inicio')
def lista_unidades(request):
    unidades = (
        Unidade.objects
        .all()
        .order_by("nome")
    )

    contexto = {
        "unidades": unidades,
    }

    return render(
        request,
        "grade/lista_unidades.html",
        contexto
    )
@staff_member_required(login_url='grade:inicio')
def atualizar_unidade(request, unidade_id=None):
    if unidade_id is None:
        return render(request, 'grade/selecionar_unidade_atualizar.html', {'unidades': Unidade.objects.all().order_by('nome')})
    from .unidades import cadastro_unidade
    return cadastro_unidade(request, unidade_id)

@staff_member_required(login_url='grade:inicio')
def excluir_unidade(request, unidade_id=None):
    unidades = Unidade.objects.all().order_by("nome")

    # Primeira tela: selecionar a unidade
    if unidade_id is None:
        contexto = {
            "unidades": unidades,
        }

        return render(
            request,
            "grade/selecionar_unidade_excluir.html",
            contexto
        )

    # Busca a unidade selecionada
    try:
        unidade = Unidade.objects.get(id=unidade_id)

    except Unidade.DoesNotExist:
        contexto = {
            "unidades": unidades,
            "erro": "Unidade não encontrada."
        }

        return render(
            request,
            "grade/selecionar_unidade_excluir.html",
            contexto
        )

    # Confirmação da exclusão
    if request.method == "POST":
        try:
            nome_unidade = unidade.nome

            unidade.delete()

            return render(
                request,
                "grade/excluir_unidade_sucesso.html",
                {
                    "nome_unidade": nome_unidade,
                }
            )

        except Exception as e:
            contexto = {
                "unidade": unidade,
                "erro": f"Não foi possível excluir a unidade: {e}",
            }

            return render(
                request,
                "grade/confirmar_exclusao_unidade.html",
                contexto
            )

    contexto = {
        "unidade": unidade,
    }

    return render(
        request,
        "grade/confirmar_exclusao_unidade.html",
        contexto
    )
@staff_member_required(login_url='grade:inicio')
def lista_disciplinas(request):
    disciplinas = (
        Disciplina.objects
        .all()
        .order_by("nome")
    )

    contexto = {
        "disciplinas": disciplinas,
    }

    return render(
        request,
        "grade/lista_disciplinas.html",
        contexto
    )
@staff_member_required(login_url='grade:inicio')
def atualizar_disciplina(request, disciplina_id=None):
    disciplinas = Disciplina.objects.all().order_by("nome")

    # Tela para selecionar a disciplina
    if disciplina_id is None:
        contexto = {
            "disciplinas": disciplinas,
        }

        return render(
            request,
            "grade/selecionar_disciplina_atualizar.html",
            contexto
        )

    # Busca a disciplina selecionada
    try:
        disciplina = Disciplina.objects.get(id=disciplina_id)

    except Disciplina.DoesNotExist:
        contexto = {
            "disciplinas": disciplinas,
            "erro": "Disciplina não encontrada.",
        }

        return render(
            request,
            "grade/selecionar_disciplina_atualizar.html",
            contexto
        )

    # Atualização
    if request.method == "POST":
        try:
            nome = request.POST.get("nome", "").strip()
            area = request.POST.get("area", "").strip()

            if not nome:
                raise ValueError("O nome da disciplina é obrigatório.")

            if not area:
                raise ValueError("A área da disciplina é obrigatória.")

            disciplina.nome = nome
            disciplina.area = area
            disciplina.save()

            sucesso = True
            erro = None

        except ValueError as e:
            sucesso = False
            erro = str(e)

        except Exception as e:
            sucesso = False
            erro = f"Não foi possível atualizar a disciplina: {e}"

    else:
        sucesso = False
        erro = None

    contexto = {
        "disciplina": disciplina,
        "disciplinas": Disciplina.objects.all().order_by("nome"),
        "sucesso": sucesso,
        "erro": erro,
        "areas": Disciplina.AREAS_CHOICES,
    }

    return render(
        request,
        "grade/atualizar_disciplina.html",
        contexto
    )
@staff_member_required(login_url='grade:inicio')
def excluir_disciplina(request, disciplina_id=None):
    disciplinas = Disciplina.objects.all().order_by("nome")

    # Tela para selecionar a disciplina
    if disciplina_id is None:
        contexto = {
            "disciplinas": disciplinas,
        }

        return render(
            request,
            "grade/selecionar_disciplina_excluir.html",
            contexto
        )

    # Busca a disciplina selecionada
    try:
        disciplina = Disciplina.objects.get(id=disciplina_id)

    except Disciplina.DoesNotExist:
        contexto = {
            "disciplinas": disciplinas,
            "erro": "Disciplina não encontrada.",
        }

        return render(
            request,
            "grade/selecionar_disciplina_excluir.html",
            contexto
        )

    # Confirmação da exclusão
    if request.method == "POST":
        try:
            nome_disciplina = disciplina.nome

            disciplina.delete()

            return render(
                request,
                "grade/excluir_disciplina_sucesso.html",
                {
                    "nome_disciplina": nome_disciplina,
                }
            )

        except Exception as e:
            contexto = {
                "disciplina": disciplina,
                "erro": f"Não foi possível excluir a disciplina: {e}",
            }

            return render(
                request,
                "grade/confirmar_exclusao_disciplina.html",
                contexto
            )

    contexto = {
        "disciplina": disciplina,
    }

    return render(
        request,
        "grade/confirmar_exclusao_disciplina.html",
        contexto
    )
