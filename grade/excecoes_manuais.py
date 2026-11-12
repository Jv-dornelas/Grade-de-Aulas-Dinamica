"""Exceção de limite diário: autorizada no editor ou preservada sem alterações."""
from .models import AlocacaoGrade

CAMPOS = ('data', 'horario_id', 'professor_id', 'unidade_id', 'sala_id',
          'turma_id', 'disciplina_id', 'demanda_id', 'motivo_excecao_limite', 'autorizado_por_id')


def assinatura_excecao(aula):
    return tuple(getattr(aula, c) for c in CAMPOS)


def excecoes_persistidas(alocacoes):
    from django.contrib.admin.models import LogEntry
    from django.contrib.contenttypes.models import ContentType
    candidatas = list(AlocacaoGrade.objects.filter(
        pk__in=[a.pk for a in alocacoes if a.pk], eh_excecao_limite_aulas=True,
        autorizado_por__isnull=False).exclude(motivo_excecao_limite=''))
    if not candidatas:
        return {}
    auditoria = set(LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(AlocacaoGrade),
        object_id__in=[str(a.pk) for a in candidatas]).values_list('object_id', 'user_id', 'change_message'))
    return {a.pk: assinatura_excecao(a) for a in candidatas
            if (str(a.pk), a.autorizado_por_id,
                'Exceção manual de limite diário: ' + a.motivo_excecao_limite) in auditoria}


def limite_autorizado(aula, persistidas):
    return bool(aula.eh_excecao_limite_aulas and (aula.motivo_excecao_limite or '').strip()
                and aula.autorizado_por_id and (getattr(aula, '_limite_manual_autorizado', False)
                or (aula.pk and persistidas.get(aula.pk) == assinatura_excecao(aula))))
