"""Prévia semanal: CP-SAT local, sem alterar as alocações existentes.

A primeira otimização maximiza a demanda atendida. Só depois de provar essa
cobertura ótima o motor fixa a quantidade de aulas e melhora as preferências.
Um resultado parcial nunca autoriza ignorar disponibilidade ou deslocamento.
"""

from .parametros import obter_proximidade
from collections import Counter, defaultdict
from datetime import date, timedelta
import math
from time import monotonic

from django.core.exceptions import ValidationError
from django.conf import settings

from .models import AlocacaoGrade, DemandaAula, HorarioAula, HorarioCurricular, Professor
from .restricoes import MotorRestricoes


MAX_CANDIDATOS = 4000
MAX_COMPARACOES = 200000
MAX_TENTATIVAS = 50000
MAX_DEMANDAS = 200
MAX_FIXAS = 500


class LimiteGeracao(Exception):
    pass


def _resultado(status, pendencias=None, **extras):
    return dict(status=status, propostas=[], avisos=[],
                pendencias=pendencias or [], **extras)


def _serializar(aula):
    return {
        'data': aula.data.isoformat(), 'horario_id': aula.horario_id,
        'unidade_id': aula.unidade_id, 'professor_id': aula.professor_id,
        'turma_id': aula.turma_id, 'disciplina_id': aula.disciplina_id,
        'demanda_id': aula.demanda_id,
        'sala_id': aula.sala_id,
        'motivo_pendencia': aula.motivo_pendencia if not aula.professor_id else '',
    }


def gerar_semana(inicio, proximidade=None, limite_segundos=10):
    """Retorna apenas novas propostas, preservando a semana gravada como fixa.

    ``optimal``: cobertura e preferências provadas ótimas no modelo cadastrado;
    ``feasible``: prévia válida sem prova de ótimo; ``unknown``: inconclusivo;
    ``invalid``: cadastros/grade fixa incompatíveis; ``empty``: sem demandas.
    O tempo inclui a construção do modelo, além da resolução; os limites de
    tamanho protegem a aplicação antes de criar uma quantidade excessiva de pares.
    """
    comeco = monotonic()
    if proximidade is None:
        proximidade = obter_proximidade()
    if not isinstance(inicio, date) or inicio.weekday() != 0:
        return _resultado('invalid', ['Selecione a segunda-feira da semana.'])
    try:
        fim = inicio + timedelta(days=6)
        segundos = float(limite_segundos)
        if not math.isfinite(segundos) or segundos <= 0 or segundos > 30:
            raise ValueError
        if isinstance(proximidade, bool) or int(proximidade) != proximidade or not 0 <= proximidade <= 240:
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        return _resultado('invalid', ['Informe até 30 segundos de cálculo e proximidade de 0 a 240 minutos.'])
    prazo = comeco + segundos

    def conferir_tempo():
        if monotonic() >= prazo:
            raise LimiteGeracao('O tempo terminou durante a preparação. Nenhuma conclusão sobre a viabilidade foi obtida; reduza a quantidade de opções ou tente novamente.')

    try:
        possui_curso = DemandaAula.objects.filter(ativa=True, origem_curso=True).exists()
        resultado = _gerar(inicio, fim, int(proximidade), prazo - min(2, segundos * .25) if possui_curso else prazo, conferir_tempo)
        if possui_curso:
            from .planejamento_curso import completar_curso
            return completar_curso(resultado, inicio, prazo)
        return resultado
    except LimiteGeracao as exc:
        return _resultado('unknown', [str(exc)], cobertura_otima=False)


def _gerar(inicio, fim, proximidade, prazo, conferir_tempo):
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        return _resultado('invalid', ['O gerador precisa da dependência OR-Tools instalada no servidor.'])

    demandas = list(DemandaAula.objects.filter(ativa=True).select_related(
        'turma__unidade', 'disciplina', 'professor').prefetch_related('turma__horarios').order_by('pk')[:MAX_DEMANDAS + 1])
    if len(demandas) > MAX_DEMANDAS:
        raise LimiteGeracao('O limite de 200 demandas por geração foi excedido. Reduza as demandas ativas.')
    if not demandas:
        return _resultado('empty', ['Vincule as turmas a um curso com matriz curricular antes de gerar a semana.'])
    for d in demandas:
        if d.origem_curso:
            item = d.turma.curso.matriz.filter(disciplina_id=d.disciplina_id).first() if d.turma.curso_id else None
            if not item or item.quantidade_semana != d.quantidade_semana:
                return _resultado('invalid', [f'{d.turma}: carga divergente da matriz. Salve o curso para sincronizar antes de gerar.'])
            if d.turma.curso.aulas_semanais == 24 and (not d.turma.turno_principal
                    or set(d.turma.dias_semana) != {0, 1, 2, 3, 4} or d.turma.dia_contraturno is None):
                return _resultado('invalid', [f'{d.turma}: configure os cinco dias úteis, turno principal e dia do contraturno para a jornada de 20 + 4 aulas.'])
    fixas = list(AlocacaoGrade.objects.filter(data__range=(inicio, fim)).select_related(
        'professor', 'horario', 'unidade', 'turma', 'disciplina', 'demanda').order_by('data', 'horario__hora_inicio', 'pk')[:MAX_FIXAS + 1])
    if len(fixas) > MAX_FIXAS or Professor.objects.count() > 300 or HorarioAula.objects.count() > 100:
        raise LimiteGeracao('A semana ultrapassa o limite desta versão: 500 aulas salvas, 300 professores ou 100 horários. Nenhuma aula foi alterada.')
    conferir_tempo()
    motor = MotorRestricoes(inicio=inicio, fim=fim)
    try:
        avisos_fixos = motor.validar(fixas, proximidade=proximidade)
    except ValidationError as exc:
        return _resultado('invalid', ['A grade já salva tem inconsistências. Corrija antes de gerar:'] + exc.messages)
    conferir_tempo()
    contagem_fixas = Counter(a.demanda_id for a in fixas if a.demanda_id)
    excedentes = []
    for aula in fixas:
        if aula.demanda_id and contagem_fixas[aula.demanda_id] > aula.demanda.quantidade_semana:
            excedentes.append(f'A demanda {aula.demanda_id} já ultrapassa a quantidade semanal nas aulas salvas.')
    if excedentes:
        return _resultado('invalid', list(dict.fromkeys(excedentes)))
    restantes = {d.pk: max(0, d.quantidade_semana - contagem_fixas[d.pk]) for d in demandas}
    curriculo = defaultdict(set)
    for item in HorarioCurricular.objects.all():
        curriculo[item.demanda_id].add((item.dia_semana, item.horario_id))
    faltas_curriculo = [f'{d.turma}: {d.disciplina.nome} precisa de {d.quantidade_semana} horários fixos; '
                       f'estão cadastrados {len(curriculo[d.pk])}. Complete a distribuição de matérias da turma.'
                       for d in demandas if d.turma.materias_fixas and restantes[d.pk]
                       and len(curriculo[d.pk]) != d.quantidade_semana]
    if faltas_curriculo:
        return _resultado('invalid', faltas_curriculo)
    professores = sorted(motor.professores.values(), key=lambda p: p.pk)
    habilitacoes = {p.pk: {disc.pk for disc in p.disciplinas.all()} for p in professores}
    fixas_por_dia = defaultdict(list)
    aulas_fixas_por_prof = Counter((a.professor_id, a.data) for a in fixas)
    for a in fixas:
        fixas_por_dia[a.data].append(a)
    candidatos = []
    por_demanda = defaultdict(list)
    por_prof_dia = defaultdict(list)
    por_dia = defaultdict(list)
    tentativas = comparacoes = 0

    def comparar():
        nonlocal comparacoes
        comparacoes += 1
        if comparacoes > MAX_COMPARACOES:
            raise LimiteGeracao('A quantidade de combinações excedeu o limite seguro. Reduza professores elegíveis ou horários das turmas e gere novamente.')
        if comparacoes % 128 == 0:
            conferir_tempo()

    for demanda in demandas:
        conferir_tempo()
        if not restantes[demanda.pk]:
            continue
        unidade_id = demanda.turma.unidade_id
        elegiveis = [p for p in professores if (
            (not demanda.professor_id or demanda.professor_id == p.pk)
            and demanda.disciplina_id in habilitacoes[p.pk]
            and motor.permitido(p.pk, unidade_id)
        )]
        for deslocamento in range(7):
            dia = inicio + timedelta(days=deslocamento)
            if dia.weekday() not in demanda.turma.dias_semana:
                continue
            for horario in (motor.horarios.values() if demanda.turma.turno_principal else demanda.turma.horarios.all()):
                if demanda.turma.materias_fixas and (dia.weekday(), horario.pk) not in curriculo[demanda.pk]:
                    continue
                if not demanda.turma.permite_horario(dia.weekday(), horario):
                    continue
                if horario.hora_inicio >= horario.hora_fim:
                    return _resultado('invalid', [f'O horário {horario.nome} precisa terminar depois de começar.'])
                for sala in motor.salas_da_unidade(unidade_id):
                    for professor in elegiveis:
                        tentativas += 1
                        if tentativas > MAX_TENTATIVAS:
                            raise LimiteGeracao('A geração ultrapassou 50 mil opções de cadastro. Reduza as opções de horários/professores antes de tentar novamente.')
                        if tentativas % 128 == 0:
                            conferir_tempo()
                        if aulas_fixas_por_prof[professor.pk, dia] >= professor.limite_aulas:
                            continue
                        if not motor.disponivel(professor.pk, dia, horario.pk):
                            continue
                        aula = AlocacaoGrade(data=dia, horario=horario,
                            unidade_id=unidade_id, sala=sala, professor=professor,
                            turma=demanda.turma, disciplina=demanda.disciplina, demanda=demanda)
                        impedida = False
                        for fixa in fixas_por_dia[dia]:
                            comparar()
                            if motor.conflitam(aula, fixa):
                                impedida = True
                                break
                        if impedida:
                            continue
                        indice = len(candidatos)
                        candidatos.append(aula)
                        if len(candidatos) > MAX_CANDIDATOS:
                            raise LimiteGeracao('A geração ultrapassou 4.000 opções de aula. Restrinja horários, salas ou professores elegíveis e tente novamente.')
                        por_demanda[demanda.pk].append(indice)
                        por_prof_dia[professor.pk, dia].append(indice)
                        por_dia[dia].append(indice)
    conferir_tempo()
    if not candidatos:
        pendencias = _pendencias(demandas, restantes, Counter())
        if pendencias:
            pendencias.append('Não há opções elegíveis para completar as demandas com os cadastros atuais.')
        resultado = _resultado('optimal', pendencias, cobertura_otima=True,
            resumo=_resumo(demandas, fixas, 0, sum(restantes.values())))
        resultado['avisos'] = avisos_fixos
        return resultado

    modelo = cp_model.CpModel()
    variaveis = [modelo.new_bool_var(f'a{i}') for i in range(len(candidatos))]
    for demanda in demandas:
        if por_demanda[demanda.pk]:
            modelo.add(sum(variaveis[i] for i in por_demanda[demanda.pk]) <= restantes[demanda.pk])
    for (prof_id, dia), indices in por_prof_dia.items():
        modelo.add(sum(variaveis[i] for i in indices) <= motor.professores[prof_id].limite_aulas - aulas_fixas_por_prof[prof_id, dia])

    # Relação simétrica: basta um dos cadastros apontar para o outro.
    parentes = {frozenset((p.pk, p.parente_vinculado_id)) for p in professores
                if p.parente_vinculado_id and p.pk != p.parente_vinculado_id}
    custos = []

    def custo_par(a, b):
        if a.unidade_id == b.unidade_id:
            return 0
        custo = 1 if a.professor_id == b.professor_id else 0
        if frozenset((a.professor_id, b.professor_id)) in parentes:
            ida = motor.tempo(a.unidade_id, b.unidade_id)
            volta = motor.tempo(b.unidade_id, a.unidade_id)
            if ida is None or volta is None or max(ida, volta) > proximidade:
                custo += 10
        return custo

    for dia, indices in por_dia.items():
        for posicao, i in enumerate(indices):
            aula = candidatos[i]
            for fixa in fixas_por_dia[dia]:
                comparar()
                custo = custo_par(aula, fixa)
                if custo:
                    custos.append(custo * variaveis[i])
            for j in indices[posicao + 1:]:
                comparar()
                outra = candidatos[j]
                if motor.conflitam(aula, outra):
                    modelo.add(variaveis[i] + variaveis[j] <= 1)
                    continue
                custo = custo_par(aula, outra)
                if custo:
                    par = modelo.new_bool_var(f'p{i}_{j}')
                    modelo.add(par <= variaveis[i])
                    modelo.add(par <= variaveis[j])
                    modelo.add(par >= variaveis[i] + variaveis[j] - 1)
                    custos.append(custo * par)
    conferir_tempo()
    cobertura = sum(variaveis)
    modelo.maximize(cobertura)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 42
    solver.parameters.max_time_in_seconds = max(0.001, (prazo - monotonic()) * (0.7 if custos else 1))
    status = solver.solve(modelo)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return _resultado('unknown', ['O tempo de cálculo não produziu uma solução verificável. Isso não comprova que a semana seja impossível.'], cobertura_otima=False)
    escolhidos = [i for i, var in enumerate(variaveis) if solver.boolean_value(var)]
    cobertura_otima = status == cp_model.OPTIMAL
    preferencia_otima = not custos
    if cobertura_otima and custos and prazo - monotonic() > 0.01:
        modelo.add(cobertura == len(escolhidos))
        modelo.minimize(sum(custos))
        for i, var in enumerate(variaveis):
            modelo.add_hint(var, int(i in escolhidos))
        solver.parameters.max_time_in_seconds = max(0.001, prazo - monotonic())
        status_preferencia = solver.solve(modelo)
        if status_preferencia in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            escolhidos = [i for i, var in enumerate(variaveis) if solver.boolean_value(var)]
            preferencia_otima = status_preferencia == cp_model.OPTIMAL
    propostas = sorted((candidatos[i] for i in escolhidos),
        key=lambda a: (a.data, a.horario.hora_inicio, a.unidade_id, a.professor_id))
    # Defesa adicional: nenhuma prévia sai sem passar pelo mesmo validador do save.
    try:
        avisos = motor.validar(fixas + propostas, proximidade=proximidade)
    except ValidationError as exc:
        return _resultado('invalid', ['A prévia não passou pela validação final:'] + exc.messages)
    contagem = Counter(a.demanda_id for a in propostas)
    pendencias = _pendencias(demandas, restantes, contagem)
    if not cobertura_otima:
        pendencias.append('O limite de cálculo foi atingido. A prévia é válida, mas ainda pode existir uma distribuição que atenda mais aulas.')
    elif pendencias:
        pendencias.append('Com os cadastros e as aulas fixas atuais, foi comprovado que não é possível atender toda a demanda sem violar as regras obrigatórias.')
    if not preferencia_otima:
        avisos.append('As preferências ainda podem ser melhoradas; o cálculo encerrou sem provar a melhor distribuição.')
    return {
        'status': 'optimal' if cobertura_otima and preferencia_otima else 'feasible',
        'propostas': [_serializar(a) for a in propostas],
        'avisos': avisos, 'pendencias': pendencias,
        'cobertura_otima': cobertura_otima,
        'resumo': _resumo(demandas, fixas, len(propostas), sum(restantes.values()) - len(propostas)),
    }


def _pendencias(demandas, restantes, contagem):
    return [f'{d.turma.nome} / {d.disciplina.nome}: faltam {restantes[d.pk] - contagem[d.pk]} professor(es)/aula(s). Verifique a distribuição fixa da matéria, habilitação, disponibilidade, limites, unidades permitidas e deslocamentos.'
            for d in demandas if restantes[d.pk] > contagem[d.pk]]


def _resumo(demandas, fixas, geradas, pendentes):
    return {'solicitadas': sum(d.quantidade_semana for d in demandas),
            'fixas': len(fixas), 'geradas': geradas, 'pendentes': pendentes}
