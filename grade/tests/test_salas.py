from collections import defaultdict
from datetime import date, timedelta
import time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .factories import criar_cenario_grade
from ..automacao import CHAVE_PREVIA, assinatura_dados, salvar_previa
from ..gerador import gerar_semana
from ..models import AlocacaoGrade, Professor, Sala, Turma, Unidade
from ..replicacao import criar_previa, confirmar_replica
from ..restricoes import MotorRestricoes


class SalasParalelasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)
        cls.sala1 = Sala.objects.create(nome='Sala 1', unidade=cls.unidade)
        cls.sala2 = Sala.objects.create(nome='Sala 2', unidade=cls.unidade)
        AlocacaoGrade.objects.filter(pk=cls.fixa.pk).update(sala=cls.sala1)
        cls.fixa.refresh_from_db()
        cls.turma2 = Turma.objects.create(nome='Preparatório B', unidade=cls.unidade, curso=cls.curso,
                                         turno_principal='manha', dia_contraturno=2)
        cls.prof2 = Professor.objects.create(nome='Docente B', unidade_oficial=cls.unidade, limite_aulas=8)
        cls.prof2.disciplinas.add(cls.disciplina)

    def setUp(self):
        self.client.force_login(self.gestor)
        self.url = reverse('grade:exibir_grade')

    def outra(self, **campos):
        dados = dict(data=self.segunda, horario=self.horarios[0], unidade=self.unidade,
                     sala=self.sala2, turma=self.turma2, disciplina=self.disciplina,
                     demanda=self.turma2.demandas.get(), professor=self.prof2)
        return AlocacaoGrade(**{**dados, **campos})

    def test_duas_turmas_salas_e_professores_distintos_podem_ser_simultaneos(self):
        self.assertEqual(MotorRestricoes().validar([self.fixa, self.outra()]), [])

    def test_professor_turma_e_sala_nao_podem_sobrepor(self):
        for campos in [{'professor':self.professor}, {'sala':self.sala1},
                       {'turma':self.turma, 'demanda':self.demanda}]:
            with self.subTest(campos=campos), self.assertRaises(ValidationError):
                MotorRestricoes().validar([self.fixa, self.outra(**campos)])

    def test_sem_professor_ainda_ocupa_sala_e_turma(self):
        a = self.outra(professor=None)
        MotorRestricoes().validar([self.fixa, a])
        with self.assertRaises(ValidationError):
            MotorRestricoes().validar([self.fixa, a, self.outra()])

    def test_legado_sem_sala_bloqueia_toda_unidade(self):
        self.fixa.sala = None
        with self.assertRaisesMessage(ValidationError, 'escola'):
            MotorRestricoes().validar([self.fixa, self.outra()])

    def test_sala_errada_inativa_e_transferencia_de_unidade_sao_recusadas(self):
        u = Unidade.objects.create(nome='Outra unidade', responsavel='Gestor')
        sala = Sala.objects.create(nome='Outra sala', unidade=u)
        with self.assertRaises(ValidationError):
            MotorRestricoes().validar([self.outra(sala=sala)])
        self.sala2.ativa=False; self.sala2.save()
        with self.assertRaises(ValidationError):
            MotorRestricoes().validar([self.outra()])
        self.sala1.unidade=u
        with self.assertRaises(ValidationError):
            self.sala1.save()

    def test_gerador_entrega_48_aulas_com_paralelismo_validado(self):
        r = gerar_semana(self.segunda)
        self.assertEqual(r['status'], 'optimal', r)
        self.assertEqual(len(r['propostas']), 47)
        self.assertEqual(r['resumo']['pendentes'], 0)
        previa={'token':'salas','inicio':self.segunda.isoformat(),'criada_em':time.time(),
                'assinatura':assinatura_dados(self.segunda),'resultado':r,'proximidade':15}
        salvar_previa(previa, 'salas')
        aulas=list(AlocacaoGrade.objects.all())
        MotorRestricoes().validar(aulas)
        grupos=defaultdict(list)
        for a in aulas:
            grupos[a.data, a.horario_id].append(a)
        self.assertEqual(len(grupos), 24)
        for lote in grupos.values():
            self.assertEqual(len(lote), 2)
            self.assertEqual(len({a.sala_id for a in lote}), 2)
            self.assertEqual(len({a.professor_id for a in lote}), 2)
            self.assertEqual(len({a.turma_id for a in lote}), 2)

    def test_sem_docentes_duas_salas_distribuem_48_materias(self):
        AlocacaoGrade.objects.all().delete()
        self.professor.disciplinas.clear(); self.prof2.disciplinas.clear()
        r=gerar_semana(self.segunda)
        self.assertEqual(len(r['propostas']), 48, r)
        self.assertEqual(r['resumo']['sem_professor'], 48)
        self.assertEqual(r['resumo']['nao_distribuidas'], 0)
        self.assertTrue(all(p['sala_id'] for p in r['propostas']))

    def test_visualizacao_diaria_tem_colunas_de_turma_e_preserva_semana(self):
        self.outra().save()
        r=self.client.get(self.url, {'data':self.segunda.isoformat(), 'por':'unidade'})
        self.assertEqual(r.context['visao'], 'dia')
        g=r.context['distribuicao_diaria'][0]
        self.assertEqual(len(g['colunas']), 2)
        self.assertEqual(g['quantidade'], 2)
        self.assertTrue(all(len(c['aulas'])==1 for c in g['linhas'][0]['celulas']))
        self.assertContains(r, 'Sala 1'); self.assertContains(r, 'Sala 2')
        for modo in ['professor','turma','curso']:
            r=self.client.get(self.url, {'data':self.segunda.isoformat(),'por':modo})
            self.assertEqual(r.context['visao'],'semana')
            self.assertEqual(r.context['total_visivel'], 2)

    def test_previa_mantida_ao_alternar_dia_semana_e_editar_sala(self):
        self.client.post(self.url, {'acao':'gerar','semana':self.segunda,'proximidade':15})
        token=self.client.session[CHAVE_PREVIA]['token']
        for visao in ['dia','semana']:
            r=self.client.get(self.url, {'data':self.segunda.isoformat(),'visao':visao})
            self.assertEqual(r.context['total_propostas'],47)
            self.assertEqual(self.client.session[CHAVE_PREVIA]['token'],token)
        self.sala2.ativa=False; self.sala2.save()
        r=self.client.get(self.url, {'data':self.segunda.isoformat()})
        self.assertTrue(r.context['previa_desatualizada'])

    def test_replicacao_preserva_salas_e_confirma_sem_sobreposicao(self):
        self.outra().save()
        p=criar_previa(self.segunda,date(2027,3,1),date(2027,3,1))
        confirmar_replica(p,p['token'],revisado=True,aceitar_parcial=True)
        aulas=AlocacaoGrade.objects.filter(data=date(2027,3,1))
        self.assertEqual(set(aulas.values_list('sala_id',flat=True)),{self.sala1.pk,self.sala2.pk})

    def test_pdf_dia_e_semana_e_permissoes_de_cadastro(self):
        self.outra().save()
        for visao in ['dia','semana']:
            r=self.client.get(reverse('grade:grade_pdf'),{'data':self.segunda.isoformat(),'visao':visao})
            self.assertEqual(r.status_code,200)
            self.assertTrue(b''.join(r.streaming_content).startswith(b'%PDF'))
        self.assertEqual(self.client.get(reverse('grade:salas')).status_code,200)
        r=self.client.get(reverse('grade:sala_editar',args=[self.sala1.pk]))
        self.assertEqual(r.context['form'].initial['unidade'],self.unidade.pk)
        self.client.force_login(get_user_model().objects.create_user('comum-salas'))
        self.assertEqual(self.client.post(reverse('grade:salas'),{'nome':'Nao criar'}).status_code,302)

    def test_api_recusa_sala_de_outra_unidade_e_preserva_grade(self):
        api=APIClient();api.force_authenticate(self.gestor)
        u=Unidade.objects.create(nome='Outra',responsavel='Gestor')
        s=Sala.objects.create(nome='Outra',unidade=u)
        r=api.patch(f'/api/alocacoes/{self.fixa.pk}/',{'sala':s.pk},format='json')
        self.assertEqual(r.status_code,400)
        self.fixa.refresh_from_db();self.assertEqual(self.fixa.sala_id,self.sala1.pk)
        self.assertEqual(api.delete(f'/api/salas/{self.sala1.pk}/').status_code,400)
        self.assertEqual(api.post('/api/salas/', {'nome':' Sala 1 ', 'unidade':self.unidade.pk},format='json').status_code,400)
