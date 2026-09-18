from django.shortcuts import render, redirect
from .models import (
    Unidade,
    Disciplina,
    Professor,
    HorarioAula,
    AlocacaoGrade,
    Disponibilidade
)
from datetime import datetime
from .services import GradeService, GradeServiceError, AlocacaoService


def exibir_grade(request):
    SENHA_PROTECAO = "grade2026"

    # Se o usuário tentar logar pela tela de bloqueio
    if request.method == "POST" and "senha_acesso" in request.POST:
        senha_digitada = request.POST.get("senha_acesso")

        if senha_digitada == SENHA_PROTECAO:
            request.session["grade_autorizada"] = True
            return redirect(request.get_full_path())
        else:
            return render(
                request,
                "grade/login_grade.html",
                {"erro": "Senha incorreta! Tente novamente."}
            )

    # Se o usuário não estiver autorizado, barra e manda para a tela de senha
    if not request.session.get("grade_autorizada"):
        return render(request, "grade/login_grade.html")

    # Carrega dados base
    unidades = Unidade.objects.all()
    horarios = HorarioAula.objects.all()
    professores = Professor.objects.all().order_by("nome")

    # Captura a data vinda da URL ou do formulário POST
    data_str = request.GET.get("data") or request.POST.get("data_grade")

    if data_str:
        try:
            data_atual_projeto = datetime.strptime(
                data_str,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            data_atual_projeto = datetime.strptime(
                "2026-04-25",
                "%Y-%m-%d"
            ).date()
    else:
        data_atual_projeto = datetime.strptime(
            "2026-04-25",
            "%Y-%m-%d"
        ).date()

    sucesso = False
    erro_negocio = None

    # POST - Salvar dados usando a camada de serviço
    if request.method == "POST" and "senha_acesso" not in request.POST:
        try:
            GradeService.salvar_grade_diaria(
                data_alvo=data_atual_projeto,
                post_data=request.POST,
                professores=professores,
                horarios=horarios,
                unidades=unidades
            )

            sucesso = True

        except GradeServiceError as e:
            erro_negocio = str(e)

    # Buscar dados do dia selecionado
    (
        disp_manha_salvas,
        disp_tarde_salvas,
        alocacoes_salvas
    ) = AlocacaoService.obter_dicionarios_de_visualizacao(
        data_atual_projeto
    )

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
    }

    return render(
        request,
        "grade/grade_tabela.html",
        context
    )


def cadastrar_professor(request):
    disciplinas = Disciplina.objects.all().order_by("nome")
    unidades = Unidade.objects.all().order_by("nome")
    professores = Professor.objects.all().order_by("nome")

    sucesso = False
    erro = None

    if request.method == "POST":
        try:
            nome = request.POST.get("nome", "").strip()
            telefone = request.POST.get("telefone", "").strip()
            email = request.POST.get("email", "").strip()

            meio_de_transporte = request.POST.get(
                "meio_de_transporte",
                "PARTICULAR"
            )

            limite_aulas = request.POST.get(
                "limite_aulas",
                "5"
            )

            unidade_oficial_id = request.POST.get(
                "unidade_oficial"
            )

            parente_vinculado_id = request.POST.get(
                "parente_vinculado"
            )

            observacao = request.POST.get(
                "observacao",
                ""
            ).strip()

            disciplinas_ids = request.POST.getlist(
                "disciplinas"
            )

            unidades_permitidas_ids = request.POST.getlist(
                "unidades_permitidas"
            )

            # Validação básica
            if not nome:
                raise ValueError(
                    "O nome do professor é obrigatório."
                )

            if not disciplinas_ids:
                raise ValueError(
                    "Selecione pelo menos uma disciplina."
                )

            # Criação do professor
            professor = Professor.objects.create(
                nome=nome,
                telefone=telefone or None,
                email=email or None,
                meio_de_transporte=meio_de_transporte,
                limite_aulas=int(limite_aulas),
                unidade_oficial_id=unidade_oficial_id or None,
                parente_vinculado_id=parente_vinculado_id or None,
                observacao=observacao or None
            )

            # Relaciona disciplinas
            professor.disciplinas.set(
                disciplinas_ids
            )

            # Relaciona unidades permitidas
            professor.unidades_permitidas.set(
                unidades_permitidas_ids
            )

            sucesso = True

            # Recarrega a lista de professores para o campo
            # "Parente vinculado"
            professores = Professor.objects.all().order_by("nome")

        except ValueError as e:
            erro = str(e)

        except Exception as e:
            erro = f"Não foi possível cadastrar o professor: {e}"

    contexto = {
        "disciplinas": disciplinas,
        "unidades": unidades,
        "professores": professores,
        "sucesso": sucesso,
        "erro": erro,
    }

    return render(
        request,
        "grade/cadastrar_professor.html",
        contexto
    )
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
def atualizar_professor(request, professor_id=None):
    professores = Professor.objects.all().order_by("nome")
    disciplinas = Disciplina.objects.all().order_by("nome")
    unidades = Unidade.objects.all().order_by("nome")

    sucesso = False
    erro = None

    # Se nenhum professor foi escolhido,
    # mostra a lista para seleção.
    if professor_id is None:

        contexto = {
            "professores": professores,
        }

        return render(
            request,
            "grade/selecionar_professor_atualizar.html",
            contexto
        )

    # Busca o professor escolhido
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
            "grade/selecionar_professor_atualizar.html",
            contexto
        )

    # Processa a atualização
    if request.method == "POST":

        try:
            nome = request.POST.get(
                "nome",
                ""
            ).strip()

            telefone = request.POST.get(
                "telefone",
                ""
            ).strip()

            email = request.POST.get(
                "email",
                ""
            ).strip()

            meio_de_transporte = request.POST.get(
                "meio_de_transporte",
                "PARTICULAR"
            )

            limite_aulas = request.POST.get(
                "limite_aulas",
                "5"
            )

            unidade_oficial_id = request.POST.get(
                "unidade_oficial"
            )

            parente_vinculado_id = request.POST.get(
                "parente_vinculado"
            )

            observacao = request.POST.get(
                "observacao",
                ""
            ).strip()

            disciplinas_ids = request.POST.getlist(
                "disciplinas"
            )

            unidades_permitidas_ids = request.POST.getlist(
                "unidades_permitidas"
            )

            # Validações
            if not nome:
                raise ValueError(
                    "O nome do professor é obrigatório."
                )

            if not disciplinas_ids:
                raise ValueError(
                    "Selecione pelo menos uma disciplina."
                )

            limite_aulas = int(limite_aulas)

            if limite_aulas < 1:
                raise ValueError(
                    "O limite diário deve ser maior que zero."
                )

            # Atualiza os dados básicos
            professor.nome = nome
            professor.telefone = telefone or None
            professor.email = email or None
            professor.meio_de_transporte = (
                meio_de_transporte
            )
            professor.limite_aulas = limite_aulas
            professor.unidade_oficial_id = (
                unidade_oficial_id or None
            )
            professor.parente_vinculado_id = (
                parente_vinculado_id or None
            )
            professor.observacao = (
                observacao or None
            )

            professor.save()

            # Atualiza relacionamentos
            professor.disciplinas.set(
                disciplinas_ids
            )

            professor.unidades_permitidas.set(
                unidades_permitidas_ids
            )

            sucesso = True

        except ValueError as e:
            erro = str(e)

        except Exception as e:
            erro = (
                "Não foi possível atualizar o professor: "
                f"{e}"
            )

    # Atualiza as listas depois da operação
    professores = Professor.objects.all().order_by("nome")

    contexto = {
        "professor": professor,
        "professores": professores,
        "disciplinas": disciplinas,
        "unidades": unidades,
        "sucesso": sucesso,
        "erro": erro,
    }

    return render(
        request,
        "grade/atualizar_professor.html",
        contexto
    )
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
def cadastrar_unidade(request):
    sucesso = False
    erro = None

    if request.method == "POST":
        try:
            nome = request.POST.get("nome", "").strip()
            responsavel = request.POST.get("responsavel", "").strip()
            endereco = request.POST.get("endereco", "").strip()
            cidade = request.POST.get("cidade", "").strip()
            cep = request.POST.get("cep", "").strip()

            if not nome:
                raise ValueError(
                    "O nome da unidade é obrigatório."
                )

            if not responsavel:
                raise ValueError(
                    "O responsável pela unidade é obrigatório."
                )

            Unidade.objects.create(
                nome=nome,
                responsavel=responsavel,
                endereco=endereco or None,
                cidade=cidade or None,
                cep=cep or None
            )

            sucesso = True

        except ValueError as e:
            erro = str(e)

        except Exception as e:
            erro = (
                "Não foi possível cadastrar a unidade: "
                f"{e}"
            )

    contexto = {
        "sucesso": sucesso,
        "erro": erro,
    }

    return render(
        request,
        "grade/cadastrar_unidade.html",
        contexto
    )
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
def atualizar_unidade(request, unidade_id=None):
    unidades = Unidade.objects.all().order_by("nome")

    # Se nenhuma unidade foi selecionada,
    # mostra a lista para escolha.
    if unidade_id is None:
        contexto = {
            "unidades": unidades,
        }

        return render(
            request,
            "grade/selecionar_unidade_atualizar.html",
            contexto
        )

    # Busca a unidade selecionada.
    try:
        unidade = Unidade.objects.get(id=unidade_id)

    except Unidade.DoesNotExist:
        contexto = {
            "unidades": unidades,
            "erro": "Unidade não encontrada."
        }

        return render(
            request,
            "grade/selecionar_unidade_atualizar.html",
            contexto
        )

    # Atualização
    if request.method == "POST":
        try:
            nome = request.POST.get("nome", "").strip()
            responsavel = request.POST.get("responsavel", "").strip()
            endereco = request.POST.get("endereco", "").strip()
            cidade = request.POST.get("cidade", "").strip()
            cep = request.POST.get("cep", "").strip()

            if not nome:
                raise ValueError(
                    "O nome da unidade é obrigatório."
                )

            if not responsavel:
                raise ValueError(
                    "O responsável pela unidade é obrigatório."
                )

            unidade.nome = nome
            unidade.responsavel = responsavel
            unidade.endereco = endereco or None
            unidade.cidade = cidade or None
            unidade.cep = cep or None

            unidade.save()

            sucesso = True
            erro = None

        except ValueError as e:
            sucesso = False
            erro = str(e)

        except Exception as e:
            sucesso = False
            erro = (
                "Não foi possível atualizar a unidade: "
                f"{e}"
            )

    else:
        sucesso = False
        erro = None

    contexto = {
        "unidade": unidade,
        "unidades": Unidade.objects.all().order_by("nome"),
        "sucesso": sucesso,
        "erro": erro,
    }

    return render(
        request,
        "grade/atualizar_unidade.html",
        contexto
    )
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