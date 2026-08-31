from rest_framework import viewsets
from .models import Unidade, Disciplina, Professor, MatrizDistancia, HorarioAula, Disponibilidade, AlocacaoGrade
from .serializers import (
    UnidadeSerializer, DisciplinaSerializer, ProfessorSerializer,
    MatrizDistanciaSerializer, HorarioAulaSerializer, DisponibilidadeSerializer, AlocacaoGradeSerializer
)

class UnidadeViewSet(viewsets.ModelViewSet):
    queryset = Unidade.objects.all()
    serializer_class = UnidadeSerializer

class DisciplinaViewSet(viewsets.ModelViewSet):
    queryset = Disciplina.objects.all()
    serializer_class = DisciplinaSerializer

class ProfessorViewSet(viewsets.ModelViewSet):
    queryset = Professor.objects.all()
    serializer_class = ProfessorSerializer

class MatrizDistanciaViewSet(viewsets.ModelViewSet):
    queryset = MatrizDistancia.objects.all()
    serializer_class = MatrizDistanciaSerializer

class HorarioAulaViewSet(viewsets.ModelViewSet):
    queryset = HorarioAula.objects.all()
    serializer_class = HorarioAulaSerializer

class DisponibilidadeViewSet(viewsets.ModelViewSet):
    queryset = Disponibilidade.objects.all()
    serializer_class = DisponibilidadeSerializer

class AlocacaoGradeViewSet(viewsets.ModelViewSet):
    queryset = AlocacaoGrade.objects.all()
    serializer_class = AlocacaoGradeSerializer