"""Cópia explícita de semanas, com prévia privada e confirmação transacional."""
from datetime import date, timedelta
import hashlib
import secrets
import time

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import OperationalError, transaction
from django.shortcuts import redirect

from .automacao import CHAVE_PREVIA, VALIDADE_SEGUNDOS, assinatura_dados, linhas_da_previa
from .distribuicao import url_grade
from .gerador import _serializar
from .models import AlocacaoGrade, DemandaAula
from .restricoes import MotorRestricoes, segunda_da_semana


CHAVE_REPLICA = 'grade_replicacao_previa'
MAX_SEMANAS = 26
MAX_AULAS = 4000


class ReplicacaoForm(forms.Form):
    semana_modelo = forms.DateField(label='Semana modelo (já salva)', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    primeira_semana = forms.DateField(label='Primeira semana de destino', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    ultima_semana = forms.DateField(label='Última semana a incluir', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

    def clean(self):
        dados = super().clean()
        if self.errors:
            return dados
        for campo in ('semana_modelo', 'primeira_semana', 'ultima_semana'):
            if not date(1900, 1, 8) <= dados[campo] <= date(2100, 12, 24):
                raise forms.ValidationError('Escolha datas entre 1900 e 2100.')
            dados[campo] = segunda_da_semana(dados[campo])
        if dados['primeira_semana'] <= dados['semana_modelo']:
            raise forms.ValidationError('O destino deve começar depois da semana modelo.')
        if dados['ultima_semana'] < dados['primeira_semana']:
            raise forms.ValidationError('A última semana deve ser igual ou posterior à primeira.')
        if (dados['ultima_semana'] - dados['primeira_semana']).days // 7 >= MAX_SEMANAS:
            raise forms.ValidationError('Replique até 26 semanas por confirmação.')
        return dados


def semanas_replica(previa):
    inicio, ultima = date.fromisoformat(previa['inicio']), date.fromisoformat(previa['ultima'])
    return [inicio + timedelta(days=7*i) for i in range((ultima-inicio).days//7+1)]


def assinatura_replicacao(previa):
    semanas = [date.fromisoformat(previa['modelo'])] + semanas_replica(previa)
    return hashlib.sha256('|'.join(assinatura_dados(s) for s in semanas).encode()).hexdigest()


def identidade(a):
    return tuple(getattr(a, c) for c in ('data', 'horario_id', 'unidade_id', 'sala_id', 'professor_id',
                                       'turma_id', 'disciplina_id', 'demanda_id'))


def criar_previa(modelo, inicio, ultima):
    form = ReplicacaoForm({'semana_modelo': modelo, 'primeira_semana': inicio, 'ultima_semana': ultima})
    if not form.is_valid():
        raise ValidationError([str(e) for erros in form.errors.values() for e in erros])
    modelo, inicio, ultima = (form.cleaned_data[c] for c in ('semana_modelo', 'primeira_semana', 'ultima_semana'))
    previa = {'tipo': 'replicacao', 'modelo': modelo.isoformat(), 'inicio': inicio.isoformat(),
              'ultima': ultima.isoformat(), 'fim': (ultima+timedelta(days=6)).isoformat(),
              'token': secrets.token_urlsafe(24), 'criada_em': time.time()}
    assinatura = assinatura_replicacao(previa)
    originais = list(AlocacaoGrade.objects.filter(data__range=(modelo, modelo+timedelta(days=6)))
                     .select_related('horario', 'professor', 'turma', 'disciplina', 'demanda')[:MAX_AULAS+1])
    if not originais:
        raise ValidationError('A semana modelo não possui aulas salvas. Gere e confirme uma semana antes de replicá-la.')
    if any(a.demanda_id and not a.demanda.ativa for a in originais):
        raise ValidationError('A semana modelo contém demandas históricas inativas. Use uma semana das ofertas atuais do curso.')
    semanas = semanas_replica(previa)
    if len(originais)*len(semanas) > MAX_AULAS:
        raise ValidationError('O período ultrapassa 4.000 aulas. Escolha menos semanas.')
    fixas = list(AlocacaoGrade.objects.filter(data__range=(inicio, ultima+timedelta(days=6)))[:MAX_AULAS+1])
    if len(fixas) > MAX_AULAS:
        raise ValidationError('O período de destino possui muitas aulas. Escolha menos semanas.')
    existentes = {identidade(a) for a in fixas}
    propostas, repetidas = [], 0
    for semana in semanas:
        for a in originais:
            item = _serializar(a)
            item['data'] = semana + timedelta(days=(a.data-modelo).days)
            nova = AlocacaoGrade(**item)
            if identidade(nova) in existentes:
                repetidas += 1
            else:
                propostas.append(nova)
    resumo_semanas, avisos = [], []
    from collections import Counter
    demandas = list(DemandaAula.objects.filter(ativa=True))
    for semana in semanas:
        lote = [a for a in fixas+propostas if semana <= a.data <= semana+timedelta(days=6)]
        avisos.extend(MotorRestricoes(inicio=semana, fim=semana+timedelta(days=6)).validar(lote))
        contagem = Counter(a.demanda_id for a in lote if a.demanda_id and a.professor_id)
        pendentes = sum(max(0, d.quantidade_semana-contagem[d.pk]) for d in demandas)
        resumo_semanas.append({'inicio': semana.isoformat(), 'aulas': len(lote), 'pendentes': pendentes})
    if assinatura != assinatura_replicacao(previa):
        raise ValidationError('Os dados mudaram durante a preparação. Tente novamente.')
    previa.update(assinatura=assinatura, resultado={'status': 'feasible',
        'propostas': [_serializar(a) for a in propostas], 'avisos': list(dict.fromkeys(avisos)),
        'pendencias': [], 'resumo': {'pendentes': sum(s['pendentes'] for s in resumo_semanas)}},
        semanas=resumo_semanas, repetidas=repetidas)
    return previa


@transaction.atomic
def confirmar_replica(previa, token, revisado=False, aceitar_parcial=False):
    if not previa or not token or not secrets.compare_digest(str(previa['token']).encode(), str(token).encode()):
        raise ValidationError('Prévia de replicação não encontrada. Prepare novamente.')
    if not revisado:
        raise ValidationError('Confirme a revisão de todas as semanas do período.')
    if time.time()-previa['criada_em'] > VALIDADE_SEGUNDOS:
        raise ValidationError('A prévia expirou. Prepare a replicação novamente.')
    if assinatura_replicacao(previa) != previa['assinatura']:
        raise ValidationError('A origem, o destino ou os cadastros mudaram. Prepare novamente; nenhuma aula foi copiada.')
    if previa['resultado']['resumo']['pendentes'] and not aceitar_parcial:
        raise ValidationError('Aceite explicitamente as pendências do período antes de confirmar.')
    novas = [AlocacaoGrade(**{**p, 'data': date.fromisoformat(p['data'])}) for p in previa['resultado']['propostas']]
    for semana in semanas_replica(previa):
        existentes = list(AlocacaoGrade.objects.filter(data__range=(semana, semana+timedelta(days=6))))
        lote = [a for a in novas if semana <= a.data <= semana+timedelta(days=6)]
        MotorRestricoes(inicio=semana, fim=semana+timedelta(days=6)).validar(existentes+lote)
    AlocacaoGrade.objects.bulk_create(novas)
    return len(novas)


def contexto_replicacao(request, dia):
    semana = segunda_da_semana(dia)
    previa = request.session.get(CHAVE_REPLICA)
    form = ReplicacaoForm(initial={'semana_modelo': semana-timedelta(days=7),
                                  'primeira_semana': semana, 'ultima_semana': semana})
    erro = None
    acao = request.POST.get('acao')
    if request.method == 'POST':
        try:
            if acao == 'descartar_replicacao':
                request.session.pop(CHAVE_REPLICA, None)
                return redirect(url_grade(dia))
            if acao == 'replicar':
                if request.session.get(CHAVE_PREVIA) or previa:
                    raise ValidationError('Confirme ou descarte a prévia aberta antes de preparar outra.')
                form = ReplicacaoForm(request.POST)
                if form.is_valid():
                    previa = criar_previa(form.cleaned_data['semana_modelo'], form.cleaned_data['primeira_semana'], form.cleaned_data['ultima_semana'])
                    request.session[CHAVE_REPLICA] = previa
                    return redirect(url_grade(date.fromisoformat(previa['inicio'])))
            if acao == 'confirmar_replicacao':
                total = confirmar_replica(previa, request.POST.get('token', ''),
                    request.POST.get('revisado_replicacao') == 'on', request.POST.get('aceitar_parcial_replicacao') == 'on')
                request.session.pop(CHAVE_REPLICA, None)
                messages.success(request, f'{total} aulas replicadas. Os registros existentes foram preservados. Revise a aprovação de cada semana; aprovações não são copiadas.')
                return redirect(url_grade(date.fromisoformat(previa['inicio'])))
        except ValidationError as exc:
            erro = ' '.join(exc.messages)
        except OperationalError:
            erro = 'O banco está ocupado. Tente novamente; nenhuma confirmação foi concluída.'
    semanas = []
    if previa:
        for s in previa['semanas']:
            inicio = date.fromisoformat(s['inicio'])
            semanas.append({**s, 'inicio': inicio, 'fim': inicio+timedelta(days=6),
                            'url': url_grade(inicio, request.GET.get('por', 'unidade'), request.GET.get('entidade', ''))})
    return {'replicacao_form': form, 'replicacao_previa': previa, 'erro_replicacao': erro,
            'replicacao_semanas': semanas,
            'replicacao_inicio': date.fromisoformat(previa['inicio']) if previa else None,
            'replicacao_fim': date.fromisoformat(previa['fim']) if previa else None}


def aplicar_previa_replicacao(auto, request):
    previa = request.session.get(CHAVE_REPLICA)
    if not previa:
        return
    auto.update(previa=previa, linhas=linhas_da_previa(previa), pode_salvar=False,
                resultado=previa['resultado'], inicio=date.fromisoformat(previa['inicio']),
                status_texto='Prévia de replicação')
