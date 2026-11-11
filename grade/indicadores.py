"""Distingue ocupação do calendário de atendimento efetivo da matriz."""
from collections import Counter

from .models import DemandaAula


def resumir_planejamento(aulas, demandas=None):
    """Recebe as aulas de uma única semana; não agrega períodos diferentes."""
    aulas = list(aulas)
    demandas = list(demandas if demandas is not None else DemandaAula.objects.filter(ativa=True))
    distribuidas = Counter(a.demanda_id for a in aulas if a.demanda_id)
    docentes = Counter(a.demanda_id for a in aulas if a.demanda_id and a.professor_id)
    carga = sum(d.quantidade_semana for d in demandas)
    planejamento = sum(min(distribuidas[d.pk], d.quantidade_semana) for d in demandas)
    atendimento = sum(min(docentes[d.pk], d.quantidade_semana) for d in demandas)
    ids = {d.pk for d in demandas}
    return {'carga': carga, 'distribuidas': planejamento, 'com_docente': atendimento,
            'sem_docente': planejamento-atendimento, 'sem_horario': carga-planejamento,
            'pendentes': carga-atendimento, 'total_registros': len(aulas),
            'fora_matriz': sum(not a.demanda_id or a.demanda_id not in ids for a in aulas)}


def contexto_indicadores(dia, auto, aprovacao):
    from datetime import date, timedelta
    from .models import AlocacaoGrade
    inicio = dia-timedelta(days=dia.weekday())
    fim = inicio+timedelta(days=6)
    aulas = list(AlocacaoGrade.objects.filter(data__range=(inicio, fim)))
    previa = auto.get('previa')
    visivel = bool(previa and date.fromisoformat(previa['inicio']) <= inicio <= date.fromisoformat(previa.get('ultima', previa['inicio']))
                   and not auto.get('previa_desatualizada'))
    if visivel:
        aulas += [AlocacaoGrade(**{**p, 'data': date.fromisoformat(p['data'])})
                  for p in previa['resultado']['propostas'] if inicio.isoformat() <= p['data'] <= fim.isoformat()]
    resumo = resumir_planejamento(aulas)
    vigente = aprovacao.get('aprovacao_vigente')
    resumo['aceitas'] = vigente.pendentes if vigente and not visivel else 0
    resumo['inclui_previa'] = visivel
    if auto.get('previa_expirada'):
        estado, proxima = 'Prévia expirada', 'Descarte a proposta e prepare uma nova antes de salvar.'
    elif auto.get('previa_desatualizada'):
        estado, proxima = 'Prévia desatualizada', 'Descarte a proposta antiga e prepare uma nova.'
    elif visivel and previa.get('tipo') == 'replicacao':
        estado, proxima = 'Cópia em revisão — ainda não salva', 'Revise as semanas do período e confirme a replicação.'
    elif visivel:
        estado, proxima = 'Prévia em revisão — ainda não salva', 'Revise os cards e escolha salvar sem aprovar ou aprovar e gravar.'
    elif vigente and vigente.parcial:
        estado, proxima = 'Grade aprovada com pendências', 'As pendências foram aceitas, mas continuam sem solução. Ajuste a grade e aprove novamente quando resolvidas.'
    elif vigente:
        estado, proxima = 'Grade aprovada', 'Consulte, exporte o PDF ou replique esta semana. Alterações exigem nova aprovação.'
    elif aprovacao.get('aprovacao_alterada'):
        estado, proxima = 'Alterada após a aprovação', 'Revise as mudanças e aprove a versão atual.'
    elif aulas:
        estado, proxima = 'Grade gravada, aguardando aprovação.', 'Use Aprovar grade para conferir a semana salva.'
    else:
        estado, proxima = 'Semana sem planejamento salvo', 'Gere uma proposta ou replique uma semana já salva.'
    if previa and not visivel and not auto.get('previa_desatualizada'):
        proxima = 'Há uma prévia em outro período. Volte à proposta ou descarte-a antes de iniciar outra operação.'
    return {'indicadores_grade': resumo, 'estado_grade': estado, 'proxima_acao_grade': proxima}
