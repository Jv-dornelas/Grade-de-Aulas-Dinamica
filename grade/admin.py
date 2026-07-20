from django.contrib import admin
from .models import Unidade, Professor, HorarioAula, AlocacaoGrade, Disponibilidade # Adicione aqui

admin.site.register(Unidade)
admin.site.register(Professor)
admin.site.register(HorarioAula)
admin.site.register(AlocacaoGrade)
admin.site.register(Disponibilidade) # Adicione aqui