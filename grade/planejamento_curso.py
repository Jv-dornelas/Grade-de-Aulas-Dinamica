"""Completa a distribuição curricular sem inventar disponibilidade docente."""
from collections import Counter, defaultdict
from datetime import date, timedelta
from time import monotonic

from .models import AlocacaoGrade, DemandaAula
from .restricoes import MotorRestricoes
from .jornada import durante_almoco
from django.core.exceptions import ValidationError


def completar_curso(resultado, inicio, prazo):
    if resultado['status'] not in ('optimal', 'feasible'):
        return resultado
    from ortools.sat.python import cp_model
    from .gerador import _serializar
    motor = MotorRestricoes(inicio=inicio, fim=inicio + timedelta(days=6))
    fixas = list(AlocacaoGrade.objects.filter(data__range=(inicio, inicio + timedelta(days=6))))
    propostas = [AlocacaoGrade(**{**p, 'data': date.fromisoformat(p['data'])}) for p in resultado['propostas']]
    ocupadas = fixas + propostas
    contagem = Counter(a.demanda_id for a in ocupadas if a.demanda_id)
    demandas = list(DemandaAula.objects.filter(ativa=True, origem_curso=True, turma__curso__isnull=False)
                    .select_related('turma__unidade', 'disciplina'))
    modelo = cp_model.CpModel()
    opcoes, variaveis, por_demanda, por_posicao = [], [], defaultdict(list), defaultdict(list)
    for d in demandas:
        if monotonic() >= prazo:
            resultado['avisos'].append('O tempo terminou antes de completar o calendário das matérias pendentes. A cobertura docente calculada foi preservada; tente novamente.')
            return resultado
        faltam = max(0, d.quantidade_semana - contagem[d.pk])
        if not faltam:
            continue
        for offset in range(7):
            dia = inicio + timedelta(days=offset)
            for h in motor.horarios.values():
                if h.hora_inicio >= h.hora_fim or durante_almoco(h.hora_inicio, h.hora_fim):
                    continue
                if not d.turma.permite_horario(dia.weekday(), h):
                    continue
                if d.turma.materias_fixas and (d.pk, dia.weekday(), h.pk) not in motor.curriculo:
                    continue
                for sala in motor.salas_da_unidade(d.turma.unidade_id):
                    a = AlocacaoGrade(data=dia, horario=h, unidade=d.turma.unidade, sala=sala,
                                     turma=d.turma, disciplina=d.disciplina, demanda=d)
                    if any(motor.conflitam(a, b) for b in ocupadas):
                        continue
                    if len(opcoes) >= 4000:
                        resultado['avisos'].append('A distribuição das matérias pendentes excedeu o limite seguro de opções. Restrinja os calendários e tente novamente.')
                        return resultado
                    var = modelo.new_bool_var(f'sem_prof_{len(opcoes)}')
                    opcoes.append(a); variaveis.append(var)
                    por_demanda[d.pk].append(var)
                    por_posicao[(d.turma.unidade_id, a.sala_id, dia, h.pk)].append(var)
        modelo.add(sum(por_demanda[d.pk]) <= faltam)
    for grupo in por_posicao.values():
        modelo.add(sum(grupo) <= 1)
    # Horários sobrepostos também conflitam: não liberar paralelo por turma.
    for i, a in enumerate(opcoes):
        for j in range(i):
            b = opcoes[j]
            if (a.data == b.data and a.unidade_id == b.unidade_id
                    and motor.conflitam(a, b)):
                modelo.add(variaveis[i] + variaveis[j] <= 1)
    if variaveis and monotonic() < prazo:
        modelo.maximize(sum(variaveis))
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 42
        solver.parameters.max_time_in_seconds = max(.001, prazo - monotonic())
        if solver.solve(modelo) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for i, a in enumerate(opcoes):
                if solver.boolean_value(variaveis[i]):
                    a.motivo_pendencia = diagnostico(a.demanda, motor, a)
                    propostas.append(a)
    try:
        motor.validar(fixas + propostas)
    except ValidationError as exc:
        return {'status': 'invalid', 'propostas': [], 'pendencias': exc.messages, 'avisos': []}
    sem_professor = [a for a in fixas + propostas if not a.professor_id]
    contagem = Counter(a.demanda_id for a in fixas + propostas if a.demanda_id)
    nao_distribuidas = sum(max(0, d.quantidade_semana - contagem[d.pk]) for d in
                          DemandaAula.objects.filter(ativa=True))
    resultado['propostas'] = [_serializar(a) for a in sorted(propostas,
        key=lambda a: (a.data, a.horario.hora_inicio, a.unidade_id, a.professor_id or 0))]
    resultado['resumo'].update(geradas=len(propostas), sem_professor=len(sem_professor),
                              nao_distribuidas=nao_distribuidas,
                              pendentes=nao_distribuidas + len(sem_professor))
    grupos = Counter((str(a.turma), a.disciplina.nome,
                      a.motivo_pendencia or diagnostico(a.demanda, motor)) for a in sem_professor)
    resultado['pendencias'] = [f'{turma} / {disciplina}: {quantidade} aula(s) sem professor. {motivo}'
                              for (turma, disciplina, motivo), quantidade in grupos.items()]
    if nao_distribuidas:
        resultado['pendencias'].append(f'{nao_distribuidas} aulas ainda sem horário. Confira calendário, carga e ocupação da unidade; não foi possível completar a distribuição neste cálculo.')
    return resultado


def diagnostico(demanda, motor, aula=None):
    habilitados = [p for p in motor.professores if demanda.disciplina_id in motor._disciplinas[p]]
    if not habilitados:
        return 'Nenhum professor habilitado para esta disciplina.'
    elegiveis = [p for p in habilitados if motor.permitido(p, demanda.turma.unidade_id)
                 and (not demanda.professor_id or p == demanda.professor_id)]
    if not elegiveis:
        return 'Nenhum professor habilitado permitido nesta unidade ou no vínculo legado.'
    if aula and not any(motor.disponivel(p, aula.data, aula.horario_id) for p in elegiveis):
        return 'Nenhum professor habilitado com disponibilidade cadastrada neste horário.'
    return 'Não foi encontrado docente neste planejamento. Confira disponibilidade, limites, conflitos e deslocamentos; não é prova de falta de professor.'
