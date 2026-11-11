from django.urls import path
from . import views
from . import mobile, cursos
from .automacao import automacao
from .pdf_grade import grade_pdf
from .horarios_curriculares import materias_turma
from .acesso import EntradaView, SaidaView
from .salas import salas
from .parametros import configuracoes
from .restricoes_horario import restricoes_horario

app_name = "grade"

urlpatterns = [
    path('configuracoes/', configuracoes, name='configuracoes'),
    path('professores/restricoes/', restricoes_horario, name='restricoes_horario'),
    path('professores/restricoes/<int:pk>/', restricoes_horario, name='restricao_horario_editar'),
    path('salas/', salas, name='salas'),
    path('salas/<int:pk>/', salas, name='sala_editar'),
    path('inicio/', EntradaView.as_view(), name='inicio'),
    path('sair/', SaidaView.as_view(), name='sair'),
    path('grade.pdf', grade_pdf, name='grade_pdf'),
    path('cursos/', cursos.cursos, name='cursos'),
    path('cursos/<int:pk>/', cursos.cursos, name='curso_editar'),
    path('turmas/', cursos.turmas, name='turmas'),
    path('turmas/<int:pk>/', cursos.turmas, name='turma_editar'),
    path('turmas/<int:pk>/materias/', materias_turma, name='materias_turma'),
    path('consultar/', cursos.consultar, name='consultar'),
    path('automacao/', automacao, name='automacao'),
    path('mobile/', mobile.minha_grade, name='mobile'),
    path('mobile/entrar/', mobile.MobileLoginView.as_view(), name='mobile_login'),
    path('mobile/sair/', mobile.MobileLogoutView.as_view(), name='mobile_logout'),
    path('mobile/grade.pdf', mobile.baixar_pdf, name='mobile_pdf'),
    path('mobile/manifest.webmanifest', mobile.manifesto, name='mobile_manifest'),
    path('mobile/sw.js', mobile.service_worker, name='mobile_sw'),
    # GRADE
    path(
        "",
        views.exibir_grade,
        name="exibir_grade"
    ),

    # PROFESSORES
    path(
        "professores/cadastrar/",
        views.cadastrar_professor,
        name="cadastrar_professor"
    ),

    path(
        "professores/",
        views.lista_professores,
        name="lista_professores"
    ),

    path(
        "professores/atualizar/",
        views.atualizar_professor,
        name="atualizar_professor"
    ),

    path(
        "professores/atualizar/<int:professor_id>/",
        views.atualizar_professor,
        name="editar_professor"
    ),

    path(
        "professores/excluir/",
        views.excluir_professor,
        name="excluir_professor"
    ),

    path(
        "professores/excluir/<int:professor_id>/",
        views.excluir_professor,
        name="confirmar_exclusao_professor"
    ),

    # DISCIPLINAS
    path(
        "disciplinas/cadastrar/",
        views.cadastrar_disciplina,
        name="cadastrar_disciplina"
    ),

    path(
        "disciplinas/",
        views.lista_disciplinas,
        name="lista_disciplinas"
    ),

    path(
    "disciplinas/atualizar/",
    views.atualizar_disciplina,
    name="atualizar_disciplina"
    ),

    path(
    "disciplinas/atualizar/<int:disciplina_id>/",
    views.atualizar_disciplina,
    name="editar_disciplina"
    ),

    path(
    "disciplinas/excluir/",
    views.excluir_disciplina,
    name="excluir_disciplina"
    ),

    path(
    "disciplinas/excluir/<int:disciplina_id>/",
    views.excluir_disciplina,
    name="confirmar_exclusao_disciplina"
    ),

    # UNIDADES
    path(
        "unidades/cadastrar/",
        views.cadastrar_unidade,
        name="cadastrar_unidade"
    ),

    path(
        "unidades/",
        views.lista_unidades,
        name="lista_unidades"
    ),

    path(
        "unidades/atualizar/",
        views.atualizar_unidade,
        name="atualizar_unidade"
    ),

    path(
        "unidades/atualizar/<int:unidade_id>/",
        views.atualizar_unidade,
        name="editar_unidade"
    ),

    path(
        "unidades/excluir/",
        views.excluir_unidade,
        name="excluir_unidade"
    ),

    path(
        "unidades/excluir/<int:unidade_id>/",
        views.excluir_unidade,
        name="confirmar_exclusao_unidade"
    ),
]
