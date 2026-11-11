"""Ficha da unidade e seus trajetos dirigidos, consumidos pelo motor existente."""
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, render
import secrets
from django.conf import settings
from .mapas import consultar_trajeto, aplicar_trajeto

from .models import MatrizDistancia, Unidade


class UnidadeForm(forms.ModelForm):
    class Meta:
        model = Unidade
        fields = ['nome', 'responsavel', 'endereco', 'cidade', 'cep']


class TrajetoForm(forms.Form):
    destino = forms.ModelChoiceField(queryset=Unidade.objects.all().order_by('nome'), label='Outra unidade')
    ida = forms.IntegerField(min_value=0, required=False, label='Ida (min)')
    volta = forms.IntegerField(min_value=0, required=False, label='Volta (min)')
    km_ida = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2, required=False, label='Ida (km)')
    km_volta = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2, required=False, label='Volta (km)')

    def clean(self):
        dados = super().clean()
        for tempo, km in (('ida', 'km_ida'), ('volta', 'km_volta')):
            if dados.get(km) is not None and dados.get(tempo) is None:
                self.add_error(tempo, 'Informe também o tempo; o gerador usa minutos, não uma velocidade presumida.')
        return dados


TrajetosFormSet = formset_factory(TrajetoForm, extra=1)


def dados_trajetos(unidade):
    if not unidade.pk:
        return []
    dados = []
    for destino in Unidade.objects.exclude(pk=unidade.pk).order_by('nome'):
        item = {'destino': destino.pk}
        for origem, fim, tempo, km in ((unidade.pk, destino.pk, 'ida', 'km_ida'),
                                     (destino.pk, unidade.pk, 'volta', 'km_volta')):
            trajetos = list(MatrizDistancia.objects.filter(origem_id=origem, destino_id=fim))
            if trajetos:
                item[tempo] = max(t.tempo_minutos for t in trajetos)
                distancias = [t.distancia_km for t in trajetos if t.distancia_km is not None]
                item[km] = max(distancias) if distancias else None
        dados.append(item)
    return dados


def gravar_trajetos(unidade, forms_trajetos):
    destinos = set()
    for f in forms_trajetos:
        dados = f.cleaned_data
        if not dados:
            continue
        if not f.has_changed():
            continue
        destino = dados['destino']
        if destino.pk == unidade.pk or destino.pk in destinos:
            raise ValidationError('Não repita uma unidade de destino nem selecione a própria unidade.')
        destinos.add(destino.pk)
        for origem, fim, tempo, km in ((unidade, destino, 'ida', 'km_ida'), (destino, unidade, 'volta', 'km_volta')):
            if dados.get(tempo) is None:
                continue  # campo vazio não apaga trajetos existentes.
            atuais = MatrizDistancia.objects.filter(origem=origem, destino=fim)
            campos = {'tempo_minutos': dados[tempo], 'distancia_km': dados.get(km),
                      'fonte': 'manual', 'consultado_em': None, 'enderecos_hash': ''}
            if not atuais.update(**campos):
                MatrizDistancia.objects.create(origem=origem, destino=fim, **campos)


def cadastro_unidade(request, pk=None):
    unidade = get_object_or_404(Unidade, pk=pk) if pk else Unidade()
    acao_mapa = request.method == 'POST' and request.POST.get('acao') in ('consultar_trajeto', 'aplicar_trajeto')
    form = UnidadeForm(request.POST if request.method == 'POST' and not acao_mapa else None, instance=unidade)
    trajetos = TrajetosFormSet(request.POST if request.method == 'POST' and not acao_mapa else None,
                               initial=dados_trajetos(unidade), prefix='trajetos')
    erro = None
    sucesso = False
    mensagem_mapas = None
    if acao_mapa:
        try:
            if not unidade.pk:
                raise ValidationError('Salve a unidade e seu endereço antes de consultar.')
            if request.POST['acao'] == 'consultar_trajeto':
                destino = forms.ModelChoiceField(queryset=Unidade.objects.exclude(pk=unidade.pk)).clean(request.POST.get('destino'))
                previa = consultar_trajeto(unidade, destino)
                previa['token'] = secrets.token_urlsafe(24)
                request.session['trajeto_previa'] = previa
            else:
                previa = request.session.get('trajeto_previa')
                if (not previa or previa['origem_id'] != unidade.pk
                        or not secrets.compare_digest(previa['token'], request.POST.get('token', ''))):
                    raise ValidationError('Consulta não encontrada ou token inválido. Consulte novamente.')
                if request.POST.get('conferido') != 'on':
                    raise ValidationError('Confira os locais e a adequação dos tempos antes de aplicar.')
                aplicar_trajeto(previa)
                request.session.pop('trajeto_previa', None)
                mensagem_mapas = 'Trajetos de ida e volta calculados e aplicados à automação.'
                trajetos = TrajetosFormSet(initial=dados_trajetos(unidade), prefix='trajetos')
        except ValidationError as exc:
            erro = ' '.join(exc.messages)
    elif request.method == 'POST' and form.is_valid() and trajetos.is_valid():
        try:
            with transaction.atomic():
                form.save()
                gravar_trajetos(unidade, trajetos)
            sucesso = True
        except ValidationError as exc:
            erro = ' '.join(exc.messages)
    return render(request, 'grade/atualizar_unidade.html' if pk else 'grade/cadastrar_unidade.html', {
        'form_unidade': form, 'trajetos': trajetos, 'unidade': unidade, 'sucesso': sucesso, 'erro': erro,
        'turmas_unidade': unidade.turmas.select_related('curso') if unidade.pk else [],
        'destinos_mapas': Unidade.objects.exclude(pk=unidade.pk), 'mapas_habilitado': settings.GRADE_MAPAS_HABILITADO,
        'previa_trajeto': request.session.get('trajeto_previa') if request.session.get('trajeto_previa', {}).get('origem_id') == unidade.pk else None,
        'mensagem_mapas': mensagem_mapas})
