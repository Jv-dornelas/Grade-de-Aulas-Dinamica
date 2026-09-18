from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from .models import Unidade, Disciplina, Professor, MatrizDistancia, HorarioAula, Disponibilidade, AlocacaoGrade
from .serializers import (
    UnidadeSerializer, DisciplinaSerializer, ProfessorSerializer,
    MatrizDistanciaSerializer, HorarioAulaSerializer, DisponibilidadeSerializer, AlocacaoGradeSerializer
)

class AdminViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminUser,)


class UnidadeViewSet(AdminViewSet):
    queryset = Unidade.objects.all()
    serializer_class = UnidadeSerializer

class DisciplinaViewSet(AdminViewSet):
    queryset = Disciplina.objects.all()
    serializer_class = DisciplinaSerializer

class ProfessorViewSet(AdminViewSet):
    queryset = Professor.objects.all()
    serializer_class = ProfessorSerializer

class MatrizDistanciaViewSet(AdminViewSet):
    queryset = MatrizDistancia.objects.all()
    serializer_class = MatrizDistanciaSerializer

class HorarioAulaViewSet(AdminViewSet):
    queryset = HorarioAula.objects.all()
    serializer_class = HorarioAulaSerializer

class DisponibilidadeViewSet(AdminViewSet):
    queryset = Disponibilidade.objects.all()
    serializer_class = DisponibilidadeSerializer

class AlocacaoGradeViewSet(AdminViewSet):
    queryset = AlocacaoGrade.objects.all()
    serializer_class = AlocacaoGradeSerializer
