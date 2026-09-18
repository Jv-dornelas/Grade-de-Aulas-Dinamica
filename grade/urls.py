from django.urls import path
from . import views
from . import mobile

app_name = "grade"

urlpatterns = [
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
