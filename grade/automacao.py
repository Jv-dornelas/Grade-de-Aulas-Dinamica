"""Geração em prévia privada da sessão e confirmação sem substituir aulas salvas."""
from .parametros import obter_proximidade
from datetime import date, timedelta
import hashlib
import json
import secrets
import time

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import OperationalError, transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .gerador import gerar_semana
from .models import (AlocacaoGrade, DemandaAula, Disciplina, Disponibilidade,
                     DisponibilidadeHorario, HorarioAula, MatrizDistancia,
                     Professor, Turma, Unidade, Curso, MatrizCurricular, HorarioCurricular, Sala)
from .restricoes import MotorRestricoes
from .jornada import jornada


CHAVE_PREVIA = 'automacao_previa'
VALIDADE_SEGUNDOS = 30 * 60


class GeracaoForm(forms.Form):
    semana = forms.DateField(label='Uma data da semana', input_formats=['%Y-%m-%d'],
                             widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    proximidade = forms.IntegerField(min_value=0, max_value=240, initial=15, widget=forms.HiddenInput)

    def clean_proximidade(self):
        return obter_proximidade()

    def clean_semana(self):
        valor = self.cleaned_data['semana']
        if not date(1900, 1, 1) <= valor <= date(2100, 12, 31):
            raise forms.ValidationError('Escolha uma data entre 1900 e 2100.')
        return valor - timedelta(days=valor.weekday())


def assinatura_dados(inicio):
    """Detecta mudanças de cadastros, relações e da semana desde a prévia."""
    modelos = (Sala, HorarioCurricular, Curso, MatrizCurricular, Professor, Unidade, Disciplina, HorarioAula, Turma, DemandaAula,
               MatrizDistancia, Professor.disciplinas.through,
               Professor.unidades_permitidas.through, Turma.horarios.through)
    dados = {m._meta.label: list(m.objects.order_by('pk').values()) for m in modelos}
    dados['jornada'] = jornada()
    dados['politica_disponibilidade'] = 'disponivel-sem-restricao-explicita-v1'
    dados['semana'] = inicio.isoformat()
    dados['proximidade_parentesco'] = obter_proximidade()
    for modelo in (AlocacaoGrade, Disponibilidade, DisponibilidadeHorario):
        dados[modelo._meta.label] = list(modelo.objects.filter(
            data__range=(inicio, inicio + timedelta(days=6))).order_by('pk').values())
    texto = json.dumps(dados, cls=DjangoJSONEncoder, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(texto.encode()).hexdigest()


def assinatura_atual_previa(previa):
    if previa.get('tipo') == 'replicacao':
        from .replicacao import assinatura_replicacao
        return assinatura_replicacao(previa)
    return assinatura_dados(date.fromisoformat(previa['inicio']))


def salvar_previa(previa, token, aceitar_parcial=False):
    if not previa or not token or not secrets.compare_digest(str(previa['token']), token):
        raise ValidationError('Prévia não encontrada. Gere a semana novamente.')
    if time.time() - previa['criada_em'] > VALIDADE_SEGUNDOS:
        raise ValidationError('A prévia expirou após 30 minutos. Gere novamente.')
    resultado = previa['resultado']
    if resultado['status'] not in ('optimal', 'feasible') or not resultado['propostas']:
        raise ValidationError('Esta prévia não possui novas aulas para salvar.')
    if resultado.get('resumo', {}).get('pendentes', 0) and not aceitar_parcial:
        raise ValidationError('Confirme que deseja salvar uma grade parcial com aulas pendentes.')
    inicio = date.fromisoformat(previa['inicio'])
    with transaction.atomic():
        if assinatura_dados(inicio) != previa['assinatura']:
            raise ValidationError('Os dados foram alterados desde a prévia. Gere novamente para usar os cadastros atualizados.')
        propostas = [AlocacaoGrade(**{**item, 'data': date.fromisoformat(item['data'])})
                     for item in resultado['propostas']]
        fixas = list(AlocacaoGrade.objects.filter(data__range=(inicio, inicio + timedelta(days=6))))
        avisos = MotorRestricoes().validar(fixas + propostas, proximidade=previa['proximidade'])
        AlocacaoGrade.objects.bulk_create(propostas)
    return len(propostas), avisos


def linhas_da_previa(previa):
    if not previa:
        return []
    mapas = {campo: modelo.objects.in_bulk() for campo, modelo in (
        ('horario', HorarioAula), ('unidade', Unidade), ('professor', Professor),
        ('turma', Turma), ('disciplina', Disciplina), ('demanda', DemandaAula), ('sala', Sala))}
    return [{'data': date.fromisoformat(item['data']), 'motivo_pendencia': item.get('motivo_pendencia', ''), **{
        campo: registros.get(item.get(campo + '_id')) for campo, registros in mapas.items()
    }} for item in previa['resultado']['propostas']]


@never_cache
@staff_member_required(login_url='grade:inicio')
@require_http_methods(['GET', 'POST'])
def automacao(request):
    contexto = contexto_automacao(request)
    if not isinstance(contexto, dict):
        return contexto
    return render(request, 'grade/automacao.html', contexto)


def contexto_automacao(request, destino='grade:automacao', processar=True):
    """Mesmo fluxo de segurança para a tela integrada e a rota compatível antiga."""
    previa = request.session.get(CHAVE_PREVIA)
    erro = None
    inicial = {'semana': request.GET.get('semana') or request.GET.get('data')
               or (previa['inicio'] if previa else timezone.localdate().isoformat()),
               'proximidade': obter_proximidade()}
    form = GeracaoForm(initial=inicial)
    if request.method == 'POST' and processar:
        acao = request.POST.get('acao')
        if acao == 'descartar':
            request.session.pop(CHAVE_PREVIA, None)
            return redirect(destino)
        if acao == 'gerar':
            form = GeracaoForm(request.POST)
            if form.is_valid():
                inicio, proximidade = form.cleaned_data['semana'], form.cleaned_data['proximidade']
                assinatura = assinatura_dados(inicio)
                resultado = gerar_semana(inicio, proximidade=proximidade)
                if assinatura != assinatura_dados(inicio):
                    erro = 'Os dados mudaram durante a geração. Gere novamente.'
                    previa = None
                    request.session.pop(CHAVE_PREVIA, None)
                else:
                    previa = {'token': secrets.token_urlsafe(24), 'inicio': inicio.isoformat(),
                              'proximidade': proximidade, 'resultado': resultado,
                              'assinatura': assinatura, 'criada_em': time.time()}
                    request.session[CHAVE_PREVIA] = previa
        elif acao == 'salvar':
            try:
                with transaction.atomic():
                    total, avisos = salvar_previa(previa, request.POST.get('token', ''),
                                                  request.POST.get('aceitar_parcial') == 'on')
                    if request.POST.get('registrar_aprovacao') == 'on':
                        from .aprovacao import registrar_aprovacao
                        inicio_aprovado = date.fromisoformat(previa['inicio'])
                        registrar_aprovacao(inicio_aprovado, request.user, assinatura_dados(inicio_aprovado),
                                            request.POST.get('aceitar_parcial') == 'on')
            except ValidationError as exc:
                erro = ' '.join(exc.messages)
            except OperationalError:
                erro = 'O banco está ocupado. Tente confirmar novamente; se os dados mudaram, gere outra prévia.'
            else:
                request.session.pop(CHAVE_PREVIA, None)
                messages.success(request, f'{total} aulas adicionadas à semana. As aulas anteriores foram preservadas.')
                if request.POST.get('registrar_aprovacao') == 'on':
                    messages.success(request, 'Grade da semana aprovada com sucesso.')
                for aviso in avisos:
                    messages.warning(request, aviso)
                return redirect(destino)
        else:
            erro = 'Ação inválida.'
    nomes_status = {'optimal': 'Prévia calculada', 'feasible': 'Prévia válida — cálculo encerrado pelo limite',
                    'unknown': 'Cálculo inconclusivo', 'invalid': 'Revise os cadastros', 'empty': 'Sem demandas ativas'}
    resultado = previa['resultado'] if previa else None
    return {
        'form': form, 'previa': previa, 'linhas': linhas_da_previa(previa), 'erro': erro,
        'resultado': resultado,
        'status_texto': ('Prévia ajustada manualmente' if resultado and resultado.get('ajustada_manualmente')
                         else nomes_status.get(resultado['status'], '') if resultado else ''),
        'inicio': date.fromisoformat(previa['inicio']) if previa else None,
        'pode_salvar': bool(resultado and resultado['status'] in ('optimal', 'feasible') and resultado['propostas']),
        'banco_teste': 'automacao' in str(settings.DATABASES['default']['NAME']),
        'jornada': jornada(),
        'proximidade_admin': obter_proximidade(),
    }
