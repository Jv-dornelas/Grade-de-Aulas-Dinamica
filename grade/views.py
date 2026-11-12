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

from .pagina_grade import exibir_grade


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
