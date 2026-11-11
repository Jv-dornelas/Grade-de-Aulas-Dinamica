"""Consolidação explícita de cadastros idênticos, preservando os vínculos."""
from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import AlocacaoGrade, DemandaAula, Disciplina, MatrizCurricular, Professor


@transaction.atomic
def consolidar_duplicadas(aplicar=False):
    grupos = defaultdict(list)
    for d in Disciplina.objects.select_for_update().order_by('pk'):
        grupos[d.nome.strip().casefold(), d.area].append(d)
    plano = []
    for itens in grupos.values():
        if len(itens) < 2:
            continue
        ids = [d.pk for d in itens]
        for modelo, campo in [(DemandaAula, 'turma_id'), (MatrizCurricular, 'curso_id')]:
            vistos = set()
            for valor in modelo.objects.filter(disciplina_id__in=ids).values_list(campo, flat=True):
                if valor in vistos:
                    raise ValidationError('Duplicidade com cargas na mesma turma/curso. Revise manualmente; nenhuma consolidação foi aplicada.')
                vistos.add(valor)
        canonical = next((d for d in itens if MatrizCurricular.objects.filter(disciplina=d).exists()), itens[0])
        plano.append({'nome': canonical.nome, 'principal': canonical.pk,
                      'duplicadas': [pk for pk in ids if pk != canonical.pk]})
    if aplicar:
        for item in plano:
            principal, ids = item['principal'], item['duplicadas']
            for p in Professor.objects.filter(disciplinas__pk__in=ids).distinct():
                p.disciplinas.add(principal)
            for modelo in [MatrizCurricular, DemandaAula, AlocacaoGrade]:
                modelo.objects.filter(disciplina_id__in=ids).update(disciplina_id=principal)
            Disciplina.objects.filter(pk__in=ids).delete()
    return plano
