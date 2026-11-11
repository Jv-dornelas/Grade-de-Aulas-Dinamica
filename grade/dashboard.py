"""Indicadores de leitura: nenhuma geração ou alteração de dados nesta página."""
from collections import Counter
from datetime import date, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Min, Max
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .aprovacao import estado_aprovacao
from .distribuicao import url_grade
from .models import (AlocacaoGrade, Curso, DemandaAula, Disciplina,
                     Disponibilidade, Professor, Turma, Unidade)


@never_cache
@staff_member_required(login_url='grade:inicio')
@require_GET
def inicio(request):
    try:
        dia = date.fromisoformat(request.GET.get('semana', ''))
        if not date(1900, 1, 8) <= dia <= date(2100, 12, 24):
            raise ValueError
    except ValueError:
        dia = timezone.localdate()
    segunda = dia - timedelta(days=dia.weekday())
    fim = segunda + timedelta(days=6)
    aulas = AlocacaoGrade.objects.filter(data__range=(segunda, fim))
    contagem = Counter(dict(aulas.exclude(demanda_id=None).exclude(professor_id=None).values('demanda_id')
                           .annotate(total=Count('pk')).values_list('demanda_id', 'total')))
    demandas = list(DemandaAula.objects.filter(ativa=True).select_related('turma__unidade', 'disciplina'))
    carga = sum(d.quantidade_semana for d in demandas)
    atendidas = sum(min(contagem[d.pk], d.quantidade_semana) for d in demandas)
    pendencias = [{'demanda': d, 'faltam': d.quantidade_semana - contagem[d.pk]}
                  for d in demandas if contagem[d.pk] < d.quantidade_semana]
    unidades = list(Unidade.objects.order_by('nome'))
    por_unidade = {u.pk: {'unidade': u, 'previstas': 0, 'atendidas': 0, 'aulas': 0} for u in unidades}
    for d in demandas:
        item = por_unidade[d.turma.unidade_id]
        item['previstas'] += d.quantidade_semana
        item['atendidas'] += min(contagem[d.pk], d.quantidade_semana)
    for row in aulas.values('unidade_id').annotate(total=Count('pk')):
        por_unidade[row['unidade_id']]['aulas'] = row['total']
    for item in por_unidade.values():
        item['percentual'] = round(100 * item['atendidas'] / item['previstas']) if item['previstas'] else 0
        item['url'] = url_grade(segunda, 'unidade', str(item['unidade'].pk))
    dias_contagem = dict(aulas.values('data').annotate(total=Count('pk')).values_list('data', 'total'))
    dias = [{'data': segunda + timedelta(days=i), 'total': dias_contagem.get(segunda + timedelta(days=i), 0)}
            for i in range(7)]
    maximo = max((d['total'] for d in dias), default=0)
    for d in dias:
        d['percentual'] = round(100 * d['total'] / maximo) if maximo else 0
    professores_disponiveis = Disponibilidade.objects.filter(data__range=(segunda, fim)).filter(
        disponivel_manha=True).values('professor_id').union(
        Disponibilidade.objects.filter(data__range=(segunda, fim), disponivel_tarde=True).values('professor_id'))
    contexto = {
        'semana': segunda, 'fim': fim, 'anterior': segunda - timedelta(days=7),
        'proxima': segunda + timedelta(days=7), 'url_grade_semana': url_grade(segunda),
        'total_unidades': len(unidades), 'total_professores': Professor.objects.count(),
        'total_cursos': Curso.objects.count(), 'total_turmas': Turma.objects.count(),
        'total_disciplinas': Disciplina.objects.count(), 'total_aulas': aulas.count(),
        'professores_alocados': aulas.exclude(professor_id=None).values('professor_id').distinct().count(),
        'professores_disponiveis': professores_disponiveis.count(),
        'carga': carga, 'atendidas': atendidas, 'pendentes': carga - atendidas,
        'cobertura': round(100 * atendidas / carga) if carga else 0,
        'unidades': por_unidade.values(), 'dias': dias, 'pendencias': pendencias,
        'periodo': AlocacaoGrade.objects.aggregate(inicio=Min('data'), fim=Max('data')),
        'aulas_banco': AlocacaoGrade.objects.count(),
        'turmas_sem_curso': Turma.objects.filter(curso=None).count(),
        'aulas_sem_demanda': aulas.filter(demanda=None).count(),
    }
    contexto.update(estado_aprovacao(segunda))
    from .indicadores import resumir_planejamento
    contexto['planejamento'] = resumir_planejamento(aulas, demandas)
    contexto['pendencias_aceitas'] = contexto['aprovacao_vigente'].pendentes if contexto['aprovacao_vigente'] else 0
    return render(request, 'grade/inicio.html', contexto)
