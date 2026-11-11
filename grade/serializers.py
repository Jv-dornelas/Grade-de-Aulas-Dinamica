from copy import copy

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from rest_framework import serializers
from .models import Unidade, Disciplina, Professor, MatrizDistancia, HorarioAula, Disponibilidade, AlocacaoGrade, Sala
from .restricoes import MotorRestricoes, validar_alocacao_individual


def validar_dias_salvos(datas):
    try:
        MotorRestricoes().validar(AlocacaoGrade.objects.filter(data__in=datas))
    except ModelValidationError as exc:
        raise serializers.ValidationError(exc.messages) from exc


def bloquear_concorrencia_grade():
    # O mesmo lock é usado pela montagem manual; protege contra dois saves simultâneos.
    list(Professor.objects.select_for_update().order_by('pk'))

class UnidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidade
        fields = '__all__'


class SalaSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        proposta = copy(self.instance) if self.instance else Sala()
        for campo, valor in attrs.items():
            setattr(proposta, campo, valor)
        try:
            proposta.full_clean()
        except ModelValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return attrs

    class Meta:
        model = Sala
        fields = '__all__'

class DisciplinaSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        proposta = copy(self.instance) if self.instance else Disciplina()
        for campo, valor in attrs.items():
            setattr(proposta, campo, valor)
        try:
            proposta.clean()
        except ModelValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        if 'nome' in attrs:
            attrs['nome'] = proposta.nome
        return attrs

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
    def validate(self, attrs):
        inicio = attrs.get('hora_inicio', getattr(self.instance, 'hora_inicio', None))
        fim = attrs.get('hora_fim', getattr(self.instance, 'hora_fim', None))
        if inicio and fim and inicio >= fim:
            raise serializers.ValidationError('A hora final deve ser posterior à inicial, no mesmo dia.')
        if inicio and fim and HorarioAula.objects.filter(hora_inicio=inicio, hora_fim=fim).exclude(
                pk=getattr(self.instance, 'pk', None)).exists():
            raise serializers.ValidationError('Já existe um horário com esse início e fim. Reutilize o cadastro existente.')
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        bloquear_concorrencia_grade()
        instance = super().update(instance, validated_data)
        validar_dias_salvos(AlocacaoGrade.objects.filter(horario=instance).values_list('data', flat=True))
        return instance

    class Meta:
        model = HorarioAula
        fields = '__all__'

class DisponibilidadeSerializer(serializers.ModelSerializer):
    @transaction.atomic
    def create(self, validated_data):
        bloquear_concorrencia_grade()
        instance = super().create(validated_data)
        validar_dias_salvos([instance.data])
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        bloquear_concorrencia_grade()
        anterior = instance.data
        instance = super().update(instance, validated_data)
        validar_dias_salvos([anterior, instance.data])
        return instance

    class Meta:
        model = Disponibilidade
        fields = '__all__'

class AlocacaoGradeSerializer(serializers.ModelSerializer):
    avisos = serializers.ListField(child=serializers.CharField(), read_only=True)

    def validate(self, attrs):
        proposta = copy(self.instance) if self.instance else AlocacaoGrade()
        for campo, valor in attrs.items():
            setattr(proposta, campo, valor)
        self._validar(proposta)
        return attrs

    @staticmethod
    def _validar(proposta):
        try:
            return validar_alocacao_individual(proposta)
        except ModelValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    @transaction.atomic
    def create(self, validated_data):
        bloquear_concorrencia_grade()
        proposta = AlocacaoGrade(**validated_data)
        avisos = self._validar(proposta)
        instance = super().create(validated_data)
        instance.avisos = avisos
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        bloquear_concorrencia_grade()
        proposta = copy(instance)
        for campo, valor in validated_data.items():
            setattr(proposta, campo, valor)
        avisos = self._validar(proposta)
        instance = super().update(instance, validated_data)
        instance.avisos = avisos
        return instance

    class Meta:
        model = AlocacaoGrade
        fields = '__all__'
        read_only_fields = ('criado_em', 'atualizado_em', 'autorizado_por')
