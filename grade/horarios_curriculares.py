"""Cadastro da distribuição de matérias da turma; não escolhe professores."""
from datetime import date, timedelta
import hashlib
import json

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render

from .models import AlocacaoGrade, DemandaAula, HorarioAula, HorarioCurricular, Turma


class MateriaFixaForm(forms.Form):
    dia_semana = forms.TypedChoiceField(coerce=int, choices=[('', 'Selecione o dia')] + list(enumerate(
        ('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'))))
    horario = forms.ModelChoiceField(queryset=HorarioAula.objects.order_by('hora_inicio', 'hora_fim'))
    demanda = forms.ModelChoiceField(queryset=DemandaAula.objects.none(), label='Disciplina')

    def __init__(self, *args, turma, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['demanda'].queryset = turma.demandas.filter(ativa=True).select_related('disciplina', 'turma__unidade')


MateriasFormSet = formset_factory(MateriaFixaForm, extra=4, can_delete=True)


def assinatura_curriculo(turma):
    dados = {'turma': list(Turma.objects.filter(pk=turma.pk).values()),
             'itens': list(turma.distribuicao_curricular.order_by('pk').values()),
             'demandas': list(turma.demandas.order_by('pk').values())}
    return hashlib.sha256(json.dumps(dados, sort_keys=True).encode()).hexdigest()


@transaction.atomic
def salvar_materias(turma, itens):
    turma.distribuicao_curricular.all().delete()
    for item in itens:
        HorarioCurricular.objects.create(turma=turma, **item)
    Turma.objects.filter(pk=turma.pk).update(materias_fixas=True)


def importar_semana(turma, data):
    inicio = data - timedelta(days=data.weekday())
    aulas = list(AlocacaoGrade.objects.filter(turma=turma, data__range=(inicio, inicio + timedelta(days=6))))
    if not aulas or any(not a.demanda_id for a in aulas):
        raise ValidationError('A semana precisa ter aulas vinculadas às demandas desta turma.')
    return [{'dia_semana': a.data.weekday(), 'horario_id': a.horario_id, 'demanda_id': a.demanda_id} for a in aulas]


@staff_member_required(login_url='grade:inicio')
def materias_turma(request, pk):
    turma = get_object_or_404(Turma.objects.select_related('curso', 'unidade'), pk=pk)
    inicial = list(turma.distribuicao_curricular.values('dia_semana', 'horario', 'demanda'))
    formset = MateriasFormSet(request.POST if request.method == 'POST' else None,
        initial=inicial, prefix='materias', form_kwargs={'turma': turma})
    erro = None
    assinatura = assinatura_curriculo(turma)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                if request.POST.get('assinatura') != assinatura_curriculo(turma):
                    raise ValidationError('O cadastro mudou. Atualize antes de salvar a distribuição.')
                if request.POST.get('acao') == 'importar':
                    data = forms.DateField().clean(request.POST.get('semana'))
                    itens = importar_semana(turma, data)
                elif formset.is_valid():
                    itens = [{k: v for k, v in f.cleaned_data.items() if k != 'DELETE'} for f in formset
                             if f.cleaned_data and not f.cleaned_data.get('DELETE')]
                else:
                    itens = None
                if itens is not None:
                    salvar_materias(turma, itens)
                    messages.success(request, 'Matérias fixadas. A automação escolherá apenas os professores; aulas já salvas foram preservadas.')
                    return redirect('grade:materias_turma', pk=pk)
        except ValidationError as exc:
            erro = ' '.join(exc.messages)
    return render(request, 'grade/materias_turma.html', {'turma': turma, 'formset': formset,
        'assinatura': assinatura, 'erro': erro, 'total': turma.distribuicao_curricular.count(),
        'carga': sum(turma.demandas.filter(ativa=True).values_list('quantidade_semana', flat=True))})
