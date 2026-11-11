from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Sala


class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ['unidade', 'nome', 'ativa']


@staff_member_required(login_url='grade:inicio')
@require_http_methods(['GET', 'POST'])
def salas(request, pk=None):
    sala = get_object_or_404(Sala, pk=pk) if pk else Sala()
    inicial = {'unidade': request.GET['unidade']} if not pk and request.GET.get('unidade', '').isdecimal() else None
    form = SalaForm(request.POST or None, instance=sala, initial=inicial)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('grade:sala_editar', pk=sala.pk)
    return render(request, 'grade/salas.html', {'form': form, 'sala': sala,
                  'salas': Sala.objects.select_related('unidade')})
