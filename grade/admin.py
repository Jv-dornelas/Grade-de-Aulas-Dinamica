from django.contrib import admin
from .models import Unidade, Disciplina, Professor, MatrizDistancia, HorarioAula, Disponibilidade, AlocacaoGrade

# Registra todos os modelos no painel administrativo do Django
admin.site.register(Unidade)
admin.site.register(Disciplina)
@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'usuario')
    search_fields = ('nome', 'email', 'usuario__username')
    autocomplete_fields = ('usuario',)
admin.site.register(MatrizDistancia)
admin.site.register(HorarioAula)
admin.site.register(Disponibilidade)
admin.site.register(AlocacaoGrade)
