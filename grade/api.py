from rest_framework import viewsets
from django.db import transaction
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from .models import Unidade, Disciplina, Professor, MatrizDistancia, HorarioAula, Disponibilidade, AlocacaoGrade
from .models import Sala
from .serializers import SalaSerializer
from .serializers import (
    UnidadeSerializer, DisciplinaSerializer, ProfessorSerializer,
    MatrizDistanciaSerializer, HorarioAulaSerializer, DisponibilidadeSerializer, AlocacaoGradeSerializer,
    bloquear_concorrencia_grade, validar_dias_salvos,
)

class AdminViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminUser,)


class UnidadeViewSet(AdminViewSet):
    queryset = Unidade.objects.all()
    serializer_class = UnidadeSerializer


class SalaViewSet(AdminViewSet):
    queryset = Sala.objects.all()
    serializer_class = SalaSerializer

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as exc:
            raise ValidationError('Sala vinculada a aulas: desative para preservar o histórico.') from exc

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

    @transaction.atomic
    def perform_destroy(self, instance):
        bloquear_concorrencia_grade()
        data = instance.data
        instance.delete()
        validar_dias_salvos([data])

class AlocacaoGradeViewSet(AdminViewSet):
    queryset = AlocacaoGrade.objects.all()
    serializer_class = AlocacaoGradeSerializer
