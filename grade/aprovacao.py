"""Aprovação explícita da versão semanal, separada da simples gravação de aulas."""
from collections import Counter
from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import OperationalError, transaction
from django.shortcuts import redirect

from .automacao import CHAVE_PREVIA, assinatura_dados
from .distribuicao import url_grade
from .models import AlocacaoGrade, AprovacaoGrade, DemandaAula
from .restricoes import MotorRestricoes


def avaliar_semana(inicio):
    aulas = list(AlocacaoGrade.objects.filter(data__range=(inicio, inicio + timedelta(days=6))))
    contagem = Counter(a.demanda_id for a in aulas if a.demanda_id and a.professor_id)
    faltas = [{'demanda': d, 'quantidade': d.quantidade_semana - contagem[d.pk]}
              for d in DemandaAula.objects.filter(ativa=True).select_related('turma__unidade', 'disciplina')
              if contagem[d.pk] < d.quantidade_semana]
    erros, avisos = [], []
    try:
        avisos = MotorRestricoes().validar(aulas)
    except ValidationError as exc:
        erros = exc.messages
    from .indicadores import resumir_planejamento
    return {**resumir_planejamento(aulas), 'total': len(aulas), 'pendentes': sum(f['quantidade'] for f in faltas),
            'faltas': faltas, 'erros': erros, 'avisos': avisos}


@transaction.atomic
def registrar_aprovacao(inicio, usuario, assinatura, aceitar_parcial=False):
    if not usuario.is_authenticated or not usuario.is_active or not usuario.is_staff:
        raise PermissionDenied
    if assinatura_dados(inicio) != assinatura:
        raise ValidationError('A grade ou os cadastros mudaram desde a revisão. Atualize e revise novamente.')
    resumo = avaliar_semana(inicio)
    if not resumo['total']:
        raise ValidationError('Não há aulas gravadas nesta semana para aprovar.')
    if resumo['erros']:
        raise ValidationError(resumo['erros'])
    if resumo['pendentes'] and not aceitar_parcial:
        raise ValidationError('A semana está incompleta. Confira as pendências e aceite explicitamente a aprovação parcial.')
    aprovacao, criada = AprovacaoGrade.objects.get_or_create(semana=inicio, assinatura=assinatura, defaults={
        'aprovado_por': usuario, 'total_aulas': resumo['total'], 'pendentes': resumo['pendentes'],
        'parcial': bool(resumo['pendentes'])})
    if criada:
        from .notificacoes import preparar_avisos
        preparar_avisos(aprovacao)
    return aprovacao, criada


def estado_aprovacao(inicio, assinatura=None):
    assinatura = assinatura or assinatura_dados(inicio)
    vigente = AprovacaoGrade.objects.filter(semana=inicio, assinatura=assinatura).first()
    anterior = AprovacaoGrade.objects.filter(semana=inicio).first()
    return {'aprovacao_vigente': vigente, 'aprovacao_anterior': anterior,
            'aprovacao_alterada': bool(anterior and not vigente)}


def contexto_aprovacao(request, dia, previa):
    inicio = dia - timedelta(days=dia.weekday())
    assinatura = assinatura_dados(inicio)
    contexto = estado_aprovacao(inicio, assinatura)
    if contexto['aprovacao_vigente']:
        contexto['avisos_email'] = contexto['aprovacao_vigente'].avisos_email.select_related('professor')
    contexto['url_revisar_aprovacao'] = url_grade(dia, request.GET.get('por', request.POST.get('por', 'unidade')),
        request.GET.get('entidade', request.POST.get('entidade', ''))) + '&aprovar=1#revisao-aprovacao'
    revisar = request.GET.get('aprovar') == '1' or request.POST.get('acao') == 'aprovar_grade'
    contexto['revisar_aprovacao'] = revisar
    contexto['previa_bloqueia_aprovacao'] = bool(previa and previa['resultado'].get('propostas'))
    contexto['assinatura_aprovacao'] = assinatura
    if revisar:
        contexto['resumo_aprovacao'] = avaliar_semana(inicio)
    if request.method == 'POST' and request.POST.get('acao') == 'aprovar_grade':
        try:
            if contexto['previa_bloqueia_aprovacao']:
                raise ValidationError('Há uma prévia pendente. Aprove e grave essa proposta, ou descarte-a antes de aprovar a grade já gravada.')
            if request.POST.get('revisado') != 'on':
                raise ValidationError('Confirme que revisou a distribuição de toda a semana.')
            registro, criada = registrar_aprovacao(inicio, request.user, request.POST.get('assinatura', ''),
                                                   request.POST.get('aceitar_parcial_aprovacao') == 'on')
            if previa and not contexto['previa_bloqueia_aprovacao']:
                request.session.pop(CHAVE_PREVIA, None)
            messages.success(request, 'Grade aprovada com sucesso.' if criada else 'Esta versão da grade já está aprovada.')
            return redirect(contexto['url_revisar_aprovacao'])
        except ValidationError as exc:
            contexto['erro_aprovacao'] = ' '.join(exc.messages)
        except OperationalError:
            contexto['erro_aprovacao'] = 'O banco está ocupado. Atualize a revisão e tente novamente.'
    return contexto
