"""Autorizações manuais auditadas; nunca inferidas de parâmetros da automação."""
from .models import AlocacaoGrade
from django.db.models import Q

CAMPOS = ('data', 'horario_id', 'professor_id', 'unidade_id', 'sala_id',
          'turma_id', 'disciplina_id', 'demanda_id', 'motivo_excecao_limite', 'autorizado_por_id',
          'eh_excecao_limite_aulas', 'eh_excecao_area_acumulo', 'motivo_excecao_area_acumulo',
          'eh_excecao_horario', 'eh_excecao_deslocamento')


def assinatura_excecao(aula):
    return tuple(getattr(aula, c) for c in CAMPOS)


def excecoes_persistidas(alocacoes):
    from django.contrib.admin.models import LogEntry
    from django.contrib.contenttypes.models import ContentType
    candidatas = list(AlocacaoGrade.objects.filter(
        Q(eh_excecao_limite_aulas=True) | Q(eh_excecao_area_acumulo=True),
        pk__in=[a.pk for a in alocacoes if a.pk], autorizado_por__isnull=False))
    if not candidatas:
        return {}
    auditoria = set(LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(AlocacaoGrade),
        object_id__in=[str(a.pk) for a in candidatas]).values_list('object_id', 'user_id', 'change_message'))
    return {a.pk: assinatura_excecao(a) for a in candidatas
            if (str(a.pk), a.autorizado_por_id,
                mensagem_auditoria(a)) in auditoria}


def mensagem_auditoria(aula):
    if aula.eh_excecao_area_acumulo:
        return 'Responsabilidade por exceção manual: ' + (aula.motivo_excecao_area_acumulo or '')
    return 'Exceção manual de limite diário: ' + (aula.motivo_excecao_limite or '')


def manual_autorizado(aula, persistidas):
    return bool(aula.eh_excecao_area_acumulo and (aula.motivo_excecao_area_acumulo or '').strip()
                and aula.autorizado_por_id and (getattr(aula, '_excecao_manual_autorizada', False)
                or (aula.pk and persistidas.get(aula.pk) == assinatura_excecao(aula))))


def limite_autorizado(aula, persistidas):
    return bool(aula.eh_excecao_limite_aulas and (aula.motivo_excecao_limite or '').strip()
                and aula.autorizado_por_id and (getattr(aula, '_limite_manual_autorizado', False)
                or (aula.pk and persistidas.get(aula.pk) == assinatura_excecao(aula))))
