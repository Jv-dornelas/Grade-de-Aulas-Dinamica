from django.contrib import admin, messages
from django import forms
from .models import Unidade, Disciplina, Professor, MatrizDistancia, HorarioAula, Disponibilidade, AlocacaoGrade
from .models import Turma, DemandaAula, DisponibilidadeHorario
from .models import Sala
from .salas import SalaForm


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    form = SalaForm
    list_display = ('nome', 'unidade', 'ativa')
    list_filter = ('unidade', 'ativa')

# Registra todos os modelos no painel administrativo do Django
class TrajetoInline(admin.TabularInline):
    model = MatrizDistancia
    fk_name = 'origem'
    extra = 1


@admin.register(Unidade)
class UnidadeAdmin(admin.ModelAdmin):
    inlines = [TrajetoInline]
admin.site.register(Disciplina)
@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'usuario')
    search_fields = ('nome', 'email', 'usuario__username')
    autocomplete_fields = ('usuario',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'parente_vinculado' in form.base_fields:
            form.base_fields['parente_vinculado'].label = 'Vínculo familiar ou conjugal (opcional)'
            form.base_fields['parente_vinculado'].help_text = (
                'Selecione o outro professor. Basta cadastrar em um dos lados; prioriza ambos na mesma '
                'unidade ou em unidades próximas. Se não for possível, mantém as aulas e apresenta aviso.')
        return form
admin.site.register(MatrizDistancia)
admin.site.register(HorarioAula)
admin.site.register(Disponibilidade)

@admin.register(AlocacaoGrade)
class AlocacaoGradeAdmin(admin.ModelAdmin):
    list_display = ('data', 'horario', 'unidade', 'professor', 'turma', 'disciplina')
    list_filter = ('data', 'unidade', 'professor')
    fields = ('data', 'horario', 'unidade', 'sala', 'professor', 'turma', 'disciplina', 'demanda')

    def save_model(self, request, obj, form, change):
        from .restricoes import validar_alocacao_individual
        avisos = validar_alocacao_individual(obj)
        super().save_model(request, obj, form, change)
        for aviso in avisos:
            self.message_user(request, aviso, level=messages.WARNING)


from .forms_cursos import TurmaForm


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    form = TurmaForm
    list_display = ('nome', 'unidade', 'dias_semana')
    list_filter = ('unidade',)
    filter_horizontal = ('horarios',)


@admin.register(DemandaAula)
class DemandaAulaAdmin(admin.ModelAdmin):
    list_display = ('turma', 'disciplina', 'quantidade_semana', 'professor', 'ativa')
    list_filter = ('ativa', 'turma__unidade', 'disciplina')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DisponibilidadeHorario)
class DisponibilidadeHorarioAdmin(admin.ModelAdmin):
    list_display = ('professor', 'data', 'horario', 'disponivel')
    list_filter = ('data', 'professor', 'disponivel')


from .models import Curso, MatrizCurricular
from .models import HorarioCurricular
admin.site.register(HorarioCurricular)
from .models import AprovacaoGrade


@admin.register(AprovacaoGrade)
class AprovacaoGradeAdmin(admin.ModelAdmin):
    list_display = ('semana', 'aprovado_por', 'aprovado_em', 'total_aulas', 'parcial', 'pendentes')
    list_filter = ('semana', 'parcial')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class MatrizInline(admin.TabularInline):
    model = MatrizCurricular
    extra = 1


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    inlines = [MatrizInline]
