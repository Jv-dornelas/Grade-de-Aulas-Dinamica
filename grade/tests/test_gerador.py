from datetime import date, time, timedelta
import json
from unittest.mock import patch

from django.test import TestCase

from ..gerador import gerar_semana
from ..models import (
    AlocacaoGrade, DemandaAula, Disciplina, Disponibilidade,
    DisponibilidadeHorario, HorarioAula, MatrizDistancia, Professor, Turma, Unidade,
)


class GeradorSemanalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.inicio = date(2026, 9, 21)
        cls.escola = Unidade.objects.create(nome='Escola Central', responsavel='Coordenação')
        cls.outra_escola = Unidade.objects.create(nome='Escola distante', responsavel='Coordenação')
        cls.disciplina = Disciplina.objects.create(nome='Matemática', area='EXATAS')
        cls.h1 = HorarioAula.objects.create(nome='08h', hora_inicio=time(8), hora_fim=time(9))
        cls.h2 = HorarioAula.objects.create(nome='09h10', hora_inicio=time(9, 10), hora_fim=time(10, 10))
        cls.prof = Professor.objects.create(nome='Ana', limite_aulas=3)
        cls.prof.disciplinas.add(cls.disciplina)
        cls.prof.unidades_permitidas.add(cls.escola, cls.outra_escola)
        cls.turma = Turma.objects.create(materias_fixas=False, nome='6º A', unidade=cls.escola, dias_semana=[0, 1, 2, 3, 4])
        cls.turma.horarios.add(cls.h1, cls.h2)
        cls.demanda = DemandaAula.objects.create(turma=cls.turma, disciplina=cls.disciplina, quantidade_semana=4)
        for dia in range(5):
            Disponibilidade.objects.create(professor=cls.prof, data=cls.inicio + timedelta(days=dia), disponivel_manha=True)

    def fixar(self, **alteracoes):
        campos = dict(data=self.inicio, horario=self.h1, professor=self.prof,
            unidade=self.escola, turma=self.turma, disciplina=self.disciplina, demanda=self.demanda)
        campos.update(alteracoes)
        return AlocacaoGrade.objects.create(**campos)

    def test_demanda_semanal_exata_sem_mutacao_do_banco(self):
        antes = list(AlocacaoGrade.objects.values())
        resultado = gerar_semana(self.inicio)
        self.assertEqual(resultado['status'], 'optimal', resultado)
        self.assertEqual(len(resultado['propostas']), 4)
        self.assertEqual(resultado['resumo']['pendentes'], 0)
        self.assertTrue(all(a['demanda_id'] == self.demanda.pk for a in resultado['propostas']))
        self.assertEqual(antes, list(AlocacaoGrade.objects.values()))
        json.dumps(resultado)  # A prévia pode ser assinada/guardada em sessão.

    def test_aula_existente_preservada_e_contada_na_demanda(self):
        fixa = self.fixar()
        antes = list(AlocacaoGrade.objects.values())
        resultado = gerar_semana(self.inicio)
        self.assertEqual(len(resultado['propostas']), 3, resultado)
        self.assertEqual(resultado['resumo']['fixas'], 1)
        self.assertFalse(any(a['data'] == self.inicio.isoformat() and a['horario_id'] == self.h1.pk for a in resultado['propostas']))
        self.assertEqual(antes, list(AlocacaoGrade.objects.values()))
        self.assertTrue(AlocacaoGrade.objects.filter(pk=fixa.pk).exists())

    def test_sem_restricao_cadastrada_professor_disponivel_por_padrao(self):
        Disponibilidade.objects.all().delete()
        resultado = gerar_semana(self.inicio)
        self.assertEqual(len(resultado['propostas']), 4)
        self.assertEqual(resultado['resumo']['pendentes'], 0)

    def test_bloqueio_de_horario_especifico_prevalece_sobre_turno(self):
        self.turma.dias_semana = [0]
        self.turma.save()
        self.turma.horarios.set([self.h1])
        DisponibilidadeHorario.objects.create(professor=self.prof, data=self.inicio, horario=self.h1, disponivel=False)
        resultado = gerar_semana(self.inicio)
        self.assertEqual(resultado['propostas'], [])

    def test_professor_precisa_da_disciplina_e_unidade_permitida(self):
        self.prof.disciplinas.clear()
        self.assertEqual(gerar_semana(self.inicio)['propostas'], [])
        self.prof.disciplinas.add(self.disciplina)
        self.prof.unidades_permitidas.clear()
        self.assertEqual(gerar_semana(self.inicio)['propostas'], [])

    def test_turma_sem_horarios_nao_gera_aulas_arbitrarias(self):
        self.turma.horarios.clear()
        self.assertEqual(gerar_semana(self.inicio)['propostas'], [])

    def test_deslocamento_bloqueia_aulas_consecutivas_ate_com_carro(self):
        self.turma.dias_semana = [0]
        self.turma.save()
        self.turma.horarios.set([self.h1])
        self.demanda.quantidade_semana = 1
        self.demanda.save()
        turma2 = Turma.objects.create(materias_fixas=False, nome='7º B', unidade=self.outra_escola, dias_semana=[0])
        turma2.horarios.add(self.h2)
        DemandaAula.objects.create(turma=turma2, disciplina=self.disciplina, quantidade_semana=1)
        MatrizDistancia.objects.create(origem=self.escola, destino=self.outra_escola, tempo_minutos=40)
        resultado = gerar_semana(self.inicio)
        self.assertEqual(resultado['status'], 'optimal', resultado)
        self.assertEqual(len(resultado['propostas']), 1)
        self.assertEqual(resultado['resumo']['pendentes'], 1)

    def test_ausencia_de_matriz_nao_inventa_tempo_de_viagem(self):
        self.fixar()
        self.turma.dias_semana = [0]
        self.turma.unidade = self.outra_escola
        self.turma.save()
        # A demanda da fixa não pode mudar: substitui por aula manual para esse cenário.
        AlocacaoGrade.objects.update(turma=None, disciplina=None, demanda=None)
        self.turma.horarios.set([self.h2])
        resultado = gerar_semana(self.inicio)
        self.assertEqual(resultado['propostas'], [], resultado)

    def test_limite_diario_impede_exceder_mesmo_com_muita_demanda(self):
        self.prof.limite_aulas = 1
        self.prof.save()
        self.turma.dias_semana = [0, 1]
        self.turma.save()
        resultado = gerar_semana(self.inicio)
        self.assertEqual(len(resultado['propostas']), 2, resultado)
        self.assertEqual(len({a['data'] for a in resultado['propostas']}), 2)

    def test_fixadas_inconsistentes_impedem_geracao(self):
        self.fixar()
        self.fixar(horario=self.h1, unidade=self.outra_escola, turma=None, disciplina=None, demanda=None)
        resultado = gerar_semana(self.inicio)
        self.assertEqual(resultado['status'], 'invalid', resultado)
        self.assertEqual(resultado['propostas'], [])
        self.assertEqual(AlocacaoGrade.objects.count(), 2)

    def test_excesso_de_demanda_ja_salva_nao_e_apagado(self):
        self.demanda.quantidade_semana = 1
        self.demanda.save()
        self.fixar()
        self.fixar(horario=self.h2)
        resultado = gerar_semana(self.inicio)
        self.assertEqual(resultado['status'], 'invalid', resultado)
        self.assertEqual(AlocacaoGrade.objects.count(), 2)

    def test_parentesco_unilateral_e_preferencia_nos_dois_sentidos(self):
        parente = Professor.objects.create(nome='Bruno', limite_aulas=3)
        parente.disciplinas.add(self.disciplina)
        parente.unidades_permitidas.add(self.escola, self.outra_escola)
        self.prof.parente_vinculado = parente
        self.prof.save()
        Disponibilidade.objects.create(professor=parente, data=self.inicio, disponivel_manha=True)
        self.turma.dias_semana = [0]
        self.turma.save()
        self.turma.horarios.set([self.h2])
        self.demanda.quantidade_semana = 1
        self.demanda.professor = parente
        self.demanda.save()
        self.fixar(turma=None, disciplina=None, demanda=None, unidade=self.outra_escola)
        resultado = gerar_semana(self.inicio)
        self.assertEqual(len(resultado['propostas']), 1, resultado)
        self.assertTrue(resultado['avisos'], resultado)
        # Inverte qual professor está fixado, conservando o vínculo em só um cadastro.
        AlocacaoGrade.objects.all().delete()
        self.demanda.professor = self.prof
        self.demanda.save()
        self.fixar(professor=parente, turma=None, disciplina=None, demanda=None, unidade=self.outra_escola)
        resultado = gerar_semana(self.inicio)
        self.assertEqual(len(resultado['propostas']), 1, resultado)
        self.assertTrue(resultado['avisos'], resultado)

    def test_parentesco_melhora_preferencia_sem_sacrificar_cobertura(self):
        parente = Professor.objects.create(nome='Bruno', limite_aulas=3)
        parente.disciplinas.add(self.disciplina)
        parente.unidades_permitidas.add(self.escola, self.outra_escola)
        self.prof.parente_vinculado = parente
        self.prof.save()
        Disponibilidade.objects.create(professor=parente, data=self.inicio, disponivel_manha=True)
        self.turma.dias_semana = [0]
        self.turma.save()
        self.turma.horarios.set([self.h2])
        self.demanda.quantidade_semana = 1
        self.demanda.save()
        # Ana está longe do parente. Para a demanda na escola Central pode alocar
        # Ana (um trajeto permitido) ou Bruno (parentesco distante). Menor custo: Ana.
        self.fixar(turma=None, disciplina=None, demanda=None, unidade=self.outra_escola)
        MatrizDistancia.objects.create(origem=self.outra_escola, destino=self.escola, tempo_minutos=5)
        MatrizDistancia.objects.create(origem=self.escola, destino=self.outra_escola, tempo_minutos=40)
        resultado = gerar_semana(self.inicio)
        self.assertEqual(len(resultado['propostas']), 1, resultado)
        self.assertEqual(resultado['propostas'][0]['professor_id'], self.prof.pk, resultado)

    def test_cobertura_tem_prioridade_sobre_preferencia_por_parentes(self):
        parente = Professor.objects.create(nome='Bruno', limite_aulas=3)
        parente.disciplinas.add(self.disciplina)
        parente.unidades_permitidas.add(self.outra_escola)
        self.prof.parente_vinculado = parente
        self.prof.save()
        Disponibilidade.objects.create(professor=parente, data=self.inicio, disponivel_manha=True)
        self.turma.dias_semana = [0]
        self.turma.save()
        self.turma.horarios.set([self.h1])
        self.demanda.quantidade_semana = 1
        self.demanda.professor = self.prof
        self.demanda.save()
        distante = Turma.objects.create(materias_fixas=False, nome='8º B', unidade=self.outra_escola, dias_semana=[0])
        distante.horarios.add(self.h1)
        DemandaAula.objects.create(turma=distante, disciplina=self.disciplina,
            quantidade_semana=1, professor=parente)
        resultado = gerar_semana(self.inicio)
        self.assertEqual(len(resultado['propostas']), 2, resultado)
        self.assertEqual(resultado['resumo']['pendentes'], 0)
        self.assertTrue(resultado['avisos'])

    def test_sem_demanda_nao_preenche_escolas(self):
        DemandaAula.objects.all().delete()
        resultado = gerar_semana(self.inicio)
        self.assertEqual(resultado['status'], 'empty')
        self.assertEqual(resultado['propostas'], [])

    def test_limite_de_tamanho_retorna_inconclusivo_sem_mutacao(self):
        with patch('grade.gerador.MAX_CANDIDATOS', 1):
            resultado = gerar_semana(self.inicio)
        self.assertEqual(resultado['status'], 'unknown', resultado)
        self.assertFalse(resultado['cobertura_otima'])
        self.assertEqual(resultado['propostas'], [])
        self.assertEqual(AlocacaoGrade.objects.count(), 0)

    def test_tempo_de_preparacao_nao_e_chamado_de_impossibilidade(self):
        with patch('grade.gerador.monotonic', side_effect=[0, 20]):
            resultado = gerar_semana(self.inicio, limite_segundos=1)
        self.assertEqual(resultado['status'], 'unknown', resultado)
        self.assertFalse(resultado['cobertura_otima'])
        self.assertEqual(resultado['propostas'], [])

    def test_solver_sem_resultado_nao_afirma_impossibilidade(self):
        from ortools.sat.python import cp_model
        with patch.object(cp_model.CpSolver, 'solve', return_value=cp_model.UNKNOWN):
            resultado = gerar_semana(self.inicio)
        self.assertEqual(resultado['status'], 'unknown', resultado)
        self.assertFalse(resultado['cobertura_otima'])
        self.assertEqual(resultado['propostas'], [])
        self.assertEqual(AlocacaoGrade.objects.count(), 0)

    def test_segunda_feira_e_parametros_obrigatorios(self):
        self.assertEqual(gerar_semana(self.inicio + timedelta(days=1))['status'], 'invalid')
        self.assertEqual(gerar_semana(self.inicio, proximidade=-1)['status'], 'invalid')
        self.assertEqual(gerar_semana(self.inicio, limite_segundos=float('nan'))['status'], 'invalid')
