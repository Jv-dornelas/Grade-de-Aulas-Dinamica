from rest_framework import serializers
from .models import Unidade, Disciplina, Professor, MatrizDistancia, HorarioAula, Disponibilidade, AlocacaoGrade

class UnidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidade
        fields = '__all__'

class DisciplinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disciplina
        fields = '__all__'

class ProfessorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Professor
        fields = '__all__'

class MatrizDistanciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatrizDistancia
        fields = '__all__'

class HorarioAulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorarioAula
        fields = '__all__'

class DisponibilidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disponibilidade
        fields = '__all__'

class AlocacaoGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlocacaoGrade
        fields = '__all__'