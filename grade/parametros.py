from django import forms
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .jornada import jornada
from .models import ConfiguracaoAutomacao


def obter_proximidade():
    valor = ConfiguracaoAutomacao.objects.filter(pk=1).values_list('proximidade_parentesco_minutos', flat=True).first()
    return valor if valor is not None else settings.GRADE_PROXIMIDADE_PARENTESCO_MINUTOS


class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoAutomacao
        fields = ['proximidade_parentesco_minutos']


@staff_member_required(login_url='grade:inicio')
@require_http_methods(['GET', 'POST'])
def configuracoes(request):
    objeto = ConfiguracaoAutomacao.objects.filter(pk=1).first() or ConfiguracaoAutomacao(
        proximidade_parentesco_minutos=obter_proximidade())
    form = ConfiguracaoForm(request.POST or None, instance=objeto)
    salvo = False
    if request.method == 'POST' and form.is_valid():
        form.save()
        salvo = True
    return render(request, 'grade/configuracoes.html', {'form':form, 'salvo':salvo, 'jornada':jornada()})
