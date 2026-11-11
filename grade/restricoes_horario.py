from datetime import timedelta

from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import DisponibilidadeHorario, AlocacaoGrade
from .restricoes import MotorRestricoes, segunda_da_semana


class RestricaoHorarioForm(forms.ModelForm):
    class Meta:
        model = DisponibilidadeHorario
        fields = ['professor', 'data', 'horario', 'disponivel']
        widgets = {'data': forms.DateInput(attrs={'type':'date'}, format='%Y-%m-%d')}
        labels = {'disponivel':'Disponível neste horário'}
        help_texts = {'disponivel':'Desmarque para bloquear. Esta decisão prevalece sobre a disponibilidade por turno.'}


def validar_datas(datas):
    for inicio in {segunda_da_semana(d) for d in datas}:
        MotorRestricoes(inicio=inicio, fim=inicio+timedelta(days=6)).validar(
            AlocacaoGrade.objects.filter(data__range=(inicio, inicio+timedelta(days=6))))


@staff_member_required(login_url='grade:inicio')
@require_http_methods(['GET','POST'])
def restricoes_horario(request, pk=None):
    objeto = get_object_or_404(DisponibilidadeHorario, pk=pk) if pk else DisponibilidadeHorario()
    antiga = objeto.data
    form = RestricaoHorarioForm(request.POST or None, instance=objeto, initial={'data':timezone.localdate()} if not pk else None)
    erro = None
    if request.method == 'POST':
        try:
            if request.POST.get('acao') == 'remover' and pk:
                with transaction.atomic():
                    objeto.delete()
                    validar_datas([antiga])
                return redirect('grade:restricoes_horario')
            if form.is_valid():
                with transaction.atomic():
                    form.save()
                    validar_datas([d for d in (antiga, objeto.data) if d])
                return redirect('grade:restricao_horario_editar', pk=objeto.pk)
        except ValidationError as exc:
            erro = ' '.join(exc.messages)
    return render(request, 'grade/restricoes_horario.html', {'form':form, 'registro_pk':pk,
        'restricoes':DisponibilidadeHorario.objects.select_related('professor','horario').order_by('-data','professor__nome'), 'erro':erro})
