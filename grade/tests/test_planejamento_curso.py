from collections import Counter
from datetime import date, timedelta
import time

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .factories import criar_cenario_grade
from ..aprovacao import avaliar_semana, registrar_aprovacao
from ..automacao import assinatura_dados, salvar_previa
from ..gerador import gerar_semana
from ..models import AlocacaoGrade, Disponibilidade, DemandaAula
from ..restricoes import MotorRestricoes


class PlanejamentoCursoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def setUp(self):
        self.client.force_login(self.gestor)

    def previa(self, resultado):
        return {'token': 'teste-curso', 'inicio': self.segunda.isoformat(), 'proximidade': 15,
                'assinatura': assinatura_dados(self.segunda), 'criada_em': time.time(), 'resultado': resultado}

    def test_sem_professor_completa_20_mais_4_sem_fingir_carga_atendida(self):
        AlocacaoGrade.objects.all().delete()
        Disponibilidade.objects.all().delete()
        self.professor.disciplinas.clear()
        r = gerar_semana(self.segunda)
        self.assertEqual(len(r['propostas']), 24, r)
        self.assertEqual(r['resumo']['pendentes'], 24)
        self.assertEqual(r['resumo']['nao_distribuidas'], 0)
        self.assertTrue(all(p['professor_id'] is None for p in r['propostas']))
        por_dia = Counter(p['data'] for p in r['propostas'])
        self.assertEqual(sorted(por_dia.values()), [4, 4, 4, 4, 8])
        for p in r['propostas']:
            self.assertTrue(self.turma.permite_horario(date.fromisoformat(p['data']).weekday(),
                next(h for h in self.horarios if h.pk == p['horario_id'])))
        previa = self.previa(r)
        with self.assertRaises(ValidationError):
            salvar_previa(previa, previa['token'])
        salvar_previa(previa, previa['token'], aceitar_parcial=True)
        self.assertEqual(avaliar_semana(self.segunda)['pendentes'], 24)
        with self.assertRaises(ValidationError):
            registrar_aprovacao(self.segunda, self.gestor, assinatura_dados(self.segunda))
        registro, _ = registrar_aprovacao(self.segunda, self.gestor, assinatura_dados(self.segunda), True)
        self.assertTrue(registro.parcial)
        self.assertEqual(registro.pendentes, 24)
        self.assertEqual(Disponibilidade.objects.count(), 0)

    def test_sem_professor_persistida_visivel_nos_quatro_modos_e_pdf(self):
        a = AlocacaoGrade.objects.create(data=self.segunda, horario=self.horarios[1], unidade=self.unidade,
            turma=self.turma, disciplina=self.disciplina, demanda=self.demanda, motivo_pendencia='Docente pendente')
        for modo in ['professor', 'curso', 'turma', 'unidade']:
            r = self.client.get(reverse('grade:exibir_grade'), {'data': self.segunda.isoformat(), 'por': modo})
            self.assertEqual(r.context['total_sem_professor'], 1)
            self.assertContains(r, 'aula-sem-professor')
            self.assertContains(r, 'Docente pendente')
            self.assertContains(r, f'editar={a.pk}')
            pdf = self.client.get(reverse('grade:grade_pdf'), {'data': self.segunda.isoformat(), 'por': modo})
            self.assertEqual(pdf.status_code, 200)
            self.assertTrue(b''.join(pdf.streaming_content).startswith(b'%PDF'))

    def test_sem_professor_reserva_unidade_mas_nao_cria_conflito_docente_entre_unidades(self):
        a = AlocacaoGrade(data=self.segunda, horario=self.horarios[1], unidade=self.unidade,
                         turma=self.turma, disciplina=self.disciplina, demanda=self.demanda)
        MotorRestricoes().validar([a])
        with self.assertRaises(ValidationError):
            MotorRestricoes().validar([a, a])
        a.demanda = None
        with self.assertRaises(ValidationError):
            MotorRestricoes().validar([a])

    def test_resolver_docente_manual_atualiza_pendencias(self):
        a = AlocacaoGrade.objects.create(data=self.segunda, horario=self.horarios[1], unidade=self.unidade,
            turma=self.turma, disciplina=self.disciplina, demanda=self.demanda)
        r = self.client.get(reverse('grade:exibir_grade'), {'data': self.segunda.isoformat(), 'editar': a.pk})
        r = self.client.post(reverse('grade:exibir_grade'), {'acao': 'salvar_aula', 'editar': a.pk,
            'estado': r.context['estado_editor'], 'data': self.segunda.isoformat(), 'horario': self.horarios[1].pk,
            'unidade': self.unidade.pk, 'demanda': self.demanda.pk, 'professor': self.professor.pk})
        self.assertEqual(r.status_code, 302)
        a.refresh_from_db()
        self.assertEqual(a.professor_id, self.professor.pk)
        self.assertEqual(a.motivo_pendencia, '')

    def test_matriz_divergente_bloqueia_geracao_sem_reescrever(self):
        DemandaAula.objects.filter(pk=self.demanda.pk).update(quantidade_semana=20)
        self.assertEqual(gerar_semana(self.segunda)['status'], 'invalid')
        self.assertEqual(DemandaAula.objects.get(pk=self.demanda.pk).quantidade_semana, 20)

    def test_uma_unidade_nao_ganha_salas_implicitas(self):
        from ..models import Turma
        AlocacaoGrade.objects.all().delete()
        Disponibilidade.objects.all().delete()
        self.professor.disciplinas.clear()
        Turma.objects.create(nome='Segunda turma', unidade=self.unidade, curso=self.curso,
            turno_principal='manha', dia_contraturno=2)
        r = gerar_semana(self.segunda)
        self.assertEqual(len(r['propostas']), 24)
        self.assertEqual(r['resumo']['pendentes'], 48)
        self.assertEqual(r['resumo']['nao_distribuidas'], 24)

    def test_adotar_curso_preserva_turma_demandas_e_aulas_antigas(self):
        from ..models import Turma
        legada = Turma.objects.create(nome='Turma antiga', unidade=self.unidade)
        demanda = DemandaAula.objects.create(turma=legada, disciplina=self.disciplina, quantidade_semana=3)
        a = AlocacaoGrade.objects.create(data=self.segunda - timedelta(days=7), horario=self.horarios[0],
            unidade=self.unidade, professor=self.professor, turma=legada, disciplina=self.disciplina, demanda=demanda)
        antes = AlocacaoGrade.objects.values().get(pk=a.pk)
        r = self.client.post(reverse('grade:turma_editar', args=[legada.pk]), {'acao': 'adotar_curso',
            'curso': self.curso.pk, 'nome': legada.nome, 'unidade': self.unidade.pk,
            'turno_principal': 'tarde', 'dia_contraturno': '4', 'dias_semana': ['0','1','2','3','4']})
        self.assertEqual(r.status_code, 302)
        nova = Turma.objects.get(nome='Turma antiga · Curso')
        self.assertEqual(nova.curso_id, self.curso.pk)
        self.assertEqual(nova.demandas.get().quantidade_semana, 24)
        self.assertEqual(nova.dia_contraturno, 4)
        demanda.refresh_from_db(); legada.refresh_from_db()
        self.assertFalse(demanda.ativa)
        self.assertIsNone(legada.curso_id)
        self.assertEqual(AlocacaoGrade.objects.values().get(pk=a.pk), antes)

    def test_nova_turma_exige_curso_e_jornada(self):
        from ..forms_cursos import TurmaForm
        f = TurmaForm({'nome':'Incompleta', 'unidade':self.unidade.pk, 'dias_semana':['0']})
        self.assertFalse(f.is_valid())
        self.assertIn('curso', f.errors)
        f = TurmaForm({'nome':'Incompleta', 'unidade':self.unidade.pk, 'curso':self.curso.pk,
                      'turno_principal':'manha', 'dias_semana':['0','1','2','3','4']})
        self.assertFalse(f.is_valid())

    def test_nova_oferta_nao_herda_disponibilidade_dos_professores(self):
        antes = list(Disponibilidade.objects.values())
        r = self.client.get(reverse('grade:exibir_grade'), {'data': '2027-02-01'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(Disponibilidade.objects.values()), antes)
