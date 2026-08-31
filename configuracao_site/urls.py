from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from grade.api import (
    UnidadeViewSet, DisciplinaViewSet, ProfessorViewSet,
    MatrizDistanciaViewSet, HorarioAulaViewSet, DisponibilidadeViewSet, AlocacaoGradeViewSet
)

router = DefaultRouter()
router.register(r'unidades', UnidadeViewSet)
router.register(r'disciplinas', DisciplinaViewSet)
router.register(r'professores', ProfessorViewSet)
router.register(r'distancias', MatrizDistanciaViewSet)
router.register(r'horarios', HorarioAulaViewSet)
router.register(r'disponibilidades', DisponibilidadeViewSet)
router.register(r'alocacoes', AlocacaoGradeViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('', include('grade.urls')), # Mantém as rotas antigas caso queira usar os templates legados
]