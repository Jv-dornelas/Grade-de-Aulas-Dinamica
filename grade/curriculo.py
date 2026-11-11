"""Sincronização idempotente, sem apagar demandas ou aulas anteriores."""
from collections import Counter
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import MatrizCurricular, Turma, DemandaAula
from .restricoes import segunda_da_semana


def sincronizar(turma):
    itens = {i.disciplina_id: i.quantidade_semana for i in turma.curso.matriz.all()} if turma.curso_id else {}
    for demanda in turma.demandas.all():
        if not demanda.origem_curso and demanda.disciplina_id in itens:
            raise ValidationError('Há demanda manual para esta disciplina. Revise-a antes de vincular a matriz; nenhum vínculo será substituído.')
    for disciplina, quantidade in itens.items():
        demanda, _ = DemandaAula.objects.get_or_create(turma=turma, disciplina_id=disciplina,
            defaults={'quantidade_semana': quantidade, 'origem_curso': True})
        contagem = Counter(segunda_da_semana(d) for d in demanda.alocacaograde_set.values_list('data', flat=True))
        if contagem and max(contagem.values()) > quantidade:
            raise ValidationError('A redução excederia a carga de uma semana já salva. Preserve a matriz histórica ou crie outro curso/turma.')
        demanda.quantidade_semana = quantidade
        demanda.ativa = True
        demanda.save(update_fields=['quantidade_semana', 'ativa'])
    turma.demandas.filter(origem_curso=True).exclude(disciplina_id__in=itens).update(ativa=False)


@receiver(post_save, sender=Turma)
def turma_salva(sender, instance, **kwargs):
    if not kwargs.get('raw'):
        sincronizar(instance)


@receiver(post_save, sender=MatrizCurricular)
@receiver(post_delete, sender=MatrizCurricular)
def matriz_salva(sender, instance, **kwargs):
    if kwargs.get('raw'):
        return
    for turma in Turma.objects.filter(curso_id=instance.curso_id):
        sincronizar(turma)
