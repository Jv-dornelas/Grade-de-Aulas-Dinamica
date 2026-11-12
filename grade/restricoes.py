"""Regras compartilhadas pela montagem manual, API, admin e gerador semanal.

Não grava dados. O lote recebido por ``validar`` representa a grade final.
Deslocamento é validado conservadoramente entre todos os pares do professor
no dia, usando o trajeto dirigido cadastrado (nunca uma estimativa implícita).
"""
from .parametros import obter_proximidade
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from itertools import combinations, product

from django.core.exceptions import ValidationError
from django.conf import settings
from .jornada import durante_almoco, jornada

from .models import (
    AlocacaoGrade, DemandaAula, Disponibilidade, DisponibilidadeHorario,
    HorarioAula, HorarioCurricular, MatrizDistancia, Professor, Turma, Unidade, Sala,
)


def segunda_da_semana(data):
    return data - timedelta(days=data.weekday())


class MotorRestricoes:
    def __init__(self, disponibilidades=None, inicio=None, fim=None):
        self.professores = {
            p.pk: p for p in Professor.objects.prefetch_related(
                'disciplinas', 'unidades_permitidas'
            )
        }
        self.horarios = {h.pk: h for h in HorarioAula.objects.all()}
        self.unidades = {u.pk: u for u in Unidade.objects.all()}
        self.salas = {s.pk: s for s in Sala.objects.all()}
        self.turmas = {
            t.pk: t for t in Turma.objects.prefetch_related('horarios')
        }
        self.demandas = {d.pk: d for d in DemandaAula.objects.all()}
        self.curriculo = set(HorarioCurricular.objects.values_list('demanda_id', 'dia_semana', 'horario_id'))
        self._disciplinas = {
            p.pk: {d.pk for d in p.disciplinas.all()}
            for p in self.professores.values()
        }
        self._permitidas = {
            p.pk: {u.pk for u in p.unidades_permitidas.all()} | {p.unidade_oficial_id}
            for p in self.professores.values()
        }
        self._horarios_turma = {
            t.pk: {h.pk for h in t.horarios.all()} for t in self.turmas.values()
        }
        self._disponibilidades = {}
        disponibilidades_db = Disponibilidade.objects.all()
        especificas_db = DisponibilidadeHorario.objects.all()
        if inicio is not None:
            disponibilidades_db = disponibilidades_db.filter(data__gte=inicio)
            especificas_db = especificas_db.filter(data__gte=inicio)
        if fim is not None:
            disponibilidades_db = disponibilidades_db.filter(data__lte=fim)
            especificas_db = especificas_db.filter(data__lte=fim)
        for d in disponibilidades_db:
            chave = (d.professor_id, d.data)
            # Bancos legados podem ter duplicados: a resposta mais restritiva vale.
            anterior = self._disponibilidades.get(chave, (True, True))
            self._disponibilidades[chave] = (
                anterior[0] and d.disponivel_manha,
                anterior[1] and d.disponivel_tarde,
            )
        self._disponibilidades.update(disponibilidades or {})
        self._disponibilidade_horario = {}
        for d in especificas_db:
            chave = (d.professor_id, d.data, d.horario_id)
            self._disponibilidade_horario[chave] = (
                self._disponibilidade_horario.get(chave, True) and d.disponivel
            )
        self._tempos = {}
        for m in MatrizDistancia.objects.select_related('origem', 'destino'):
            if m.fonte == 'OSRM-carro':
                from .mapas import assinatura_enderecos
                if m.enderecos_hash != assinatura_enderecos(m.origem, m.destino):
                    continue
            chave = (m.origem_id, m.destino_id)
            self._tempos[chave] = max(self._tempos.get(chave, 0), m.tempo_minutos)

    def disponivel(self, prof_id, data, horario_id):
        if prof_id not in self.professores:
            return False
        horario = self.horarios.get(horario_id)
        if not horario or horario.hora_inicio >= horario.hora_fim:
            return False
        if durante_almoco(horario.hora_inicio, horario.hora_fim):
            return False
        especifica = self._disponibilidade_horario.get((prof_id, data, horario_id))
        if especifica is not None:
            return especifica
        manha, tarde = self._disponibilidades.get((prof_id, data), (True, True))
        corte_turnos = jornada()['inicio_tarde']
        return ((horario.hora_inicio >= corte_turnos or manha)
                and (horario.hora_fim <= corte_turnos or tarde))

    def permitido(self, prof_id, unidade_id):
        return unidade_id is not None and unidade_id in self._permitidas.get(prof_id, set())

    def salas_da_unidade(self, unidade_id):
        salas = [s for s in self.salas.values() if s.unidade_id == unidade_id and s.ativa]
        # Sem cadastro físico: preservar a capacidade conservadora anterior.
        return salas if salas else ([None] if not any(s.unidade_id == unidade_id for s in self.salas.values()) else [])

    def tempo(self, origem, destino):
        return 0 if origem == destino else self._tempos.get((origem, destino))

    def motivo_conflito(self, a, b):
        if a.data != b.data:
            return None
        ha, hb = self.horarios[a.horario_id], self.horarios[b.horario_id]
        sobrepostos = ha.hora_inicio < hb.hora_fim and hb.hora_inicio < ha.hora_fim
        if sobrepostos:
            if a.professor_id and a.professor_id == b.professor_id:
                return 'Professor com aulas sobrepostas no mesmo dia.'
            if a.unidade_id == b.unidade_id and (not a.sala_id or not b.sala_id):
                return 'A escola já possui uma aula nesse intervalo na grade.'
            if a.sala_id and a.sala_id == b.sala_id:
                return 'A sala possui aulas sobrepostas no mesmo dia.'
            if a.turma_id and a.turma_id == b.turma_id:
                return 'A turma possui aulas sobrepostas no mesmo dia.'
        if not a.professor_id or not b.professor_id or a.professor_id != b.professor_id or a.unidade_id == b.unidade_id:
            return None
        primeira, segunda = (a, b) if ha.hora_inicio <= hb.hora_inicio else (b, a)
        h1, h2 = self.horarios[primeira.horario_id], self.horarios[segunda.horario_id]
        minutos = (datetime.combine(a.data, h2.hora_inicio)
                   - datetime.combine(a.data, h1.hora_fim)).total_seconds() / 60
        deslocamento = self.tempo(primeira.unidade_id, segunda.unidade_id)
        if deslocamento is None:
            return 'Falta cadastrar o tempo de deslocamento entre as escolas do professor.'
        if minutos < deslocamento:
            return (f'Tempo insuficiente de deslocamento: intervalo de {minutos:g} min '
                    f'para um trajeto de {deslocamento} min, inclusive com veículo próprio.')
        return None

    def conflitam(self, a, b):
        return self.motivo_conflito(a, b) is not None

    def avisos_parentesco(self, alocacoes, proximidade=None):
        """Ligação em qualquer sentido; todos os locais dos dois parentes no dia."""
        if proximidade is None:
            proximidade = obter_proximidade()
        grupos = defaultdict(lambda: defaultdict(set))
        for a in alocacoes:
            grupos[a.data][a.professor_id].add(a.unidade_id)
        pares = {
            tuple(sorted((p.pk, p.parente_vinculado_id)))
            for p in self.professores.values()
            if p.parente_vinculado_id and p.parente_vinculado_id != p.pk
        }
        avisos = []
        for data, professores in sorted(grupos.items()):
            for pa, pb in sorted(pares):
                if pa not in professores or pb not in professores:
                    continue
                distantes = []
                for ua, ub in sorted(product(professores[pa], professores[pb])):
                    ida, volta = self.tempo(ua, ub), self.tempo(ub, ua)
                    if ida is None or volta is None or max(ida, volta) > proximidade:
                        distantes.append((ua, ub))
                if distantes:
                    nomes = ' e '.join(self.professores[p].nome for p in (pa, pb))
                    avisos.append(
                        f'{data:%d/%m/%Y}: professores com vínculo familiar ou conjugal — {nomes} — '
                        f'estão em unidades distantes ou com proximidade não confirmada. '
                        f'A preferência é mantê-los na mesma unidade ou em unidades próximas, durante todo o dia.'
                    )
        return avisos

    def validar(self, alocacoes, proximidade=None):
        alocacoes = list(alocacoes)
        from .excecoes_manuais import excecoes_persistidas, limite_autorizado
        excecoes = excecoes_persistidas(alocacoes)
        autorizadas = Counter()
        salas_anteriores = {a.pk: (a.data, a.horario_id, a.unidade_id, a.sala_id)
                            for a in AlocacaoGrade.objects.filter(pk__in=[a.pk for a in alocacoes if a.pk])}
        posicoes_anteriores = {a.pk: (a.data, a.horario_id, a.demanda_id) for a in AlocacaoGrade.objects.filter(
            pk__in=[a.pk for a in alocacoes if a.pk is not None])}
        demandas_anteriores = dict(AlocacaoGrade.objects.filter(
            pk__in=[a.pk for a in alocacoes if a.pk is not None],
        ).values_list('pk', 'demanda_id'))
        erros, contagem, demanda_contagem = [], Counter(), Counter()
        validas = []
        for a in alocacoes:
            prof, horario = self.professores.get(a.professor_id), self.horarios.get(a.horario_id)
            if (a.professor_id and not prof) or not horario or a.unidade_id not in self.unidades or not a.data:
                erros.append('Informe professor, escola, data e horário válidos em todas as aulas.')
                continue
            contexto = f"{a.data:%d/%m/%Y} — {prof.nome if prof else 'Sem professor'}, {horario.nome}"
            if horario.hora_inicio >= horario.hora_fim:
                erros.append(f'{contexto}: o fim da aula deve ser posterior ao início.')
                continue
            validas.append(a)
            if a.sala_id:
                sala = self.salas.get(a.sala_id)
                antiga = salas_anteriores.get(a.pk) == (a.data, a.horario_id, a.unidade_id, a.sala_id)
                if not sala or sala.unidade_id != a.unidade_id or (not sala.ativa and not antiga):
                    erros.append(f'{contexto}: sala inexistente, inativa ou de outra unidade.')
            if prof and not self.disponivel(a.professor_id, a.data, a.horario_id):
                if durante_almoco(horario.hora_inicio, horario.hora_fim):
                    erros.append(f'{contexto}: aula invade o intervalo de uma hora de almoço.')
                else:
                    erros.append(f'{contexto}: professor sem disponibilidade nesse horário.')
            if prof and not self.permitido(a.professor_id, a.unidade_id):
                erros.append(f'{contexto}: escola fora das unidades permitidas ao professor.')
            if prof and a.disciplina_id and a.disciplina_id not in self._disciplinas[a.professor_id]:
                erros.append(f'{contexto}: professor não habilitado para a disciplina.')
            if not prof and (not a.demanda_id or not self.demandas.get(a.demanda_id) or not self.demandas[a.demanda_id].origem_curso):
                erros.append('Aula sem professor exige disciplina e turma vinculadas a uma matriz de curso.')
            if not prof and durante_almoco(horario.hora_inicio, horario.hora_fim):
                erros.append('Aula sem professor invade o intervalo de almoco.')
            vinculos = (a.turma_id, a.disciplina_id, a.demanda_id)
            if any(vinculos) and not all(vinculos):
                erros.append(f'{contexto}: informe turma, disciplina e demanda juntas; '
                             'aulas planejadas precisam manter os três vínculos.')
            if prof:
                contagem[(a.professor_id, a.data)] += 1
                if limite_autorizado(a, excecoes):
                    autorizadas[(a.professor_id, a.data)] += 1
            if any(getattr(a, campo, False) for campo in (
                'eh_excecao_horario',
                'eh_excecao_deslocamento', 'eh_excecao_area_acumulo',
            )):
                erros.append(f'{contexto}: exceções não podem contornar as restrições obrigatórias.')
            if a.eh_excecao_limite_aulas and not limite_autorizado(a, excecoes):
                erros.append(f'{contexto}: exceção de limite exige confirmação no editor manual e justificativa.')
            if a.turma_id:
                turma = self.turmas.get(a.turma_id)
                if not turma:
                    erros.append(f'{contexto}: turma inválida.')
                elif (turma.unidade_id != a.unidade_id
                      or not turma.permite_horario(a.data.weekday(), horario)):
                    erros.append(f'{contexto}: aula fora da escola, dias ou horários cadastrados para a turma.')
            if a.demanda_id:
                demanda = self.demandas.get(a.demanda_id)
                preservada = demandas_anteriores.get(a.pk) == a.demanda_id
                if not demanda or (not demanda.ativa and not preservada):
                    erros.append(f'{contexto}: demanda inexistente ou inativa.')
                else:
                    turma_demanda = self.turmas.get(demanda.turma_id)
                    mantida = posicoes_anteriores.get(a.pk) == (a.data, a.horario_id, a.demanda_id)
                    if (turma_demanda and turma_demanda.materias_fixas and not mantida
                            and (a.demanda_id, a.data.weekday(), a.horario_id) not in self.curriculo):
                        erros.append(f'{contexto}: a matéria não está cadastrada neste dia/horário fixo da turma.')
                    if (a.turma_id != demanda.turma_id or a.disciplina_id != demanda.disciplina_id
                            or (a.professor_id and demanda.professor_id and a.professor_id != demanda.professor_id)):
                        erros.append(f'{contexto}: turma, disciplina ou professor incompatíveis com a demanda.')
                    demanda_contagem[(demanda.pk, segunda_da_semana(a.data))] += 1
        for (prof_id, data), quantidade in contagem.items():
            professor = self.professores[prof_id]
            if quantidade - autorizadas[(prof_id, data)] > professor.limite_aulas:
                erros.append(f'{data:%d/%m/%Y}: {professor.nome} excedeu o limite de '
                             f'{professor.limite_aulas} aulas por dia ({quantidade} aulas).')
        for (demanda_id, semana), quantidade in demanda_contagem.items():
            limite = self.demandas[demanda_id].quantidade_semana
            if quantidade > limite:
                erros.append(f'Semana de {semana:%d/%m/%Y}: demanda {demanda_id} '
                             f'excede as {limite} aulas cadastradas ({quantidade} aulas).')
        for a, b in combinations(validas, 2):
            motivo = self.motivo_conflito(a, b)
            if motivo:
                erros.append(f'{a.data:%d/%m/%Y}: {motivo}')
        if erros:
            raise ValidationError(list(dict.fromkeys(erros)))
        avisos = self.avisos_parentesco(validas, proximidade)
        avisos.extend(f'{a.data:%d/%m/%Y}: exceção manual de limite diário registrada — {a.motivo_excecao_limite}'
                      for a in validas if limite_autorizado(a, excecoes))
        return avisos


def validar_alocacao_individual(instance):
    """Substitui o registro no conjunto semanal, cobrindo PATCH e troca de data."""
    if not instance.data:
        raise ValidationError('Informe a data da aula.')
    semanas = {segunda_da_semana(instance.data)}
    if instance.pk:
        anterior = AlocacaoGrade.objects.filter(pk=instance.pk).values(
            'data', 'turma_id', 'disciplina_id', 'demanda_id',
        ).first()
        if anterior:
            tinha_vinculo = any(anterior[c] for c in ('turma_id', 'disciplina_id', 'demanda_id'))
            if tinha_vinculo and not any((instance.turma_id, instance.disciplina_id, instance.demanda_id)):
                raise ValidationError('Não é permitido remover todos os vínculos de uma aula planejada. '
                                      'Mantenha turma, disciplina e demanda para preservar a contagem semanal.')
            semanas.add(segunda_da_semana(anterior['data']))
    datas = [inicio + timedelta(days=d) for inicio in semanas for d in range(7)]
    outras = list(AlocacaoGrade.objects.filter(data__in=datas).exclude(pk=instance.pk))
    return MotorRestricoes().validar(outras + [instance])
