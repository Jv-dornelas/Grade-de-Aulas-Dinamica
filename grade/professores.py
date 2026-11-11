"""Ficha única de professor com os campos usados pelo planejamento."""
import hashlib
import json
from datetime import timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect

from .models import Professor, AlocacaoGrade
from .restricoes import MotorRestricoes, segunda_da_semana


def estado_professor(pk):
    if not pk:
        return ''
    p = Professor.objects.get(pk=pk)
    dados = {'campos': list(Professor.objects.filter(pk=pk).values()),
             'disciplinas': list(p.disciplinas.order_by('pk').values_list('pk', flat=True)),
             'unidades': list(p.unidades_permitidas.order_by('pk').values_list('pk', flat=True))}
    return hashlib.sha256(json.dumps(dados, sort_keys=True, default=str).encode()).hexdigest()


class ProfessorForm(forms.ModelForm):
    estado = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Professor
        fields = ['nome', 'telefone', 'email', 'disciplinas', 'meio_de_transporte', 'limite_aulas',
                  'unidade_oficial', 'unidades_permitidas', 'parente_vinculado', 'usuario', 'observacao']
        labels = {'parente_vinculado': 'Vínculo familiar ou conjugal (opcional)', 'usuario': 'Conta de acesso mobile (opcional)'}
        help_texts = {
            'disciplinas': 'Disciplinas nas quais este professor está habilitado a lecionar.',
            'unidades_permitidas': 'Unidades adicionais; a unidade oficial já é permitida.',
            'parente_vinculado': 'Selecione o familiar/cônjuge. Basta cadastrar em um dos lados. A automação prioriza proximidade, mas pode alocar longe com aviso.',
            'usuario': 'Vincule uma conta de professor existente e ainda não utilizada. A criação de contas é feita pela administração técnica.',
            'meio_de_transporte': 'Informativo. O motor usa os minutos cadastrados entre unidades; não deduz velocidade pelo veículo.',
            'observacao': 'Texto para consulta da coordenação; não é interpretado como regra automática.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado'].initial = estado_professor(self.instance.pk)
        self.fields['unidades_permitidas'].required = False
        self.fields['unidades_permitidas'].label = 'Unidades adicionais permitidas (opcional)'
        self.fields['parente_vinculado'].queryset = Professor.objects.exclude(pk=self.instance.pk)
        usuarios = get_user_model().objects.filter(is_active=True, is_staff=False, is_superuser=False)
        usuarios = usuarios.filter(Q(professor__isnull=True) | Q(pk=self.instance.usuario_id))
        if self.instance.usuario_id:
            usuarios = get_user_model().objects.filter(Q(pk__in=usuarios.values('pk')) | Q(pk=self.instance.usuario_id))
        self.fields['usuario'].queryset = usuarios.order_by('username')


def cadastro_professor(request, pk=None):
    professor = get_object_or_404(Professor, pk=pk) if pk else Professor()
    form = ProfessorForm(request.POST or None, instance=professor)
    sucesso = False
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                if pk and form.cleaned_data['estado'] != estado_professor(pk):
                    raise ValidationError('Este cadastro mudou desde a abertura. Atualize a ficha antes de salvar.')
                form.save()
                semanas = {segunda_da_semana(d) for d in AlocacaoGrade.objects.filter(professor=professor).values_list('data', flat=True)}
                for semana in semanas:
                    MotorRestricoes(inicio=semana, fim=semana+timedelta(days=6)).validar(
                        AlocacaoGrade.objects.filter(data__range=(semana, semana+timedelta(days=6))))
            messages.success(request, 'Cadastro do professor salvo com sucesso.')
            return redirect('grade:editar_professor', professor_id=professor.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
        except IntegrityError:
            if not pk:
                professor.pk = None
            form.add_error(None, 'Um dos vínculos mudou durante a gravação. Atualize a ficha e confira a conta/unidades selecionadas.')
    return render(request, 'grade/atualizar_professor.html' if pk else 'grade/cadastrar_professor.html',
                  {'professor': professor, 'form_professor': form, 'sucesso': sucesso})
