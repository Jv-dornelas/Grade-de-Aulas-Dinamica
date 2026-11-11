from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ..automacao import CHAVE_PREVIA
from ..models import AlocacaoGrade, AprovacaoGrade
from .factories import criar_cenario_grade


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def setUp(self):
        self.client.force_login(self.gestor)
        self.url = reverse('grade:inicio')

    def test_indicadores_e_links_da_semana(self):
        response = self.client.get(self.url, {'semana': self.segunda.isoformat()})
        self.assertEqual(response.status_code, 200)
        for key, value in {'total_aulas': 1, 'carga': 24, 'atendidas': 1,
                           'pendentes': 23, 'cobertura': 4, 'total_turmas': 1,
                           'professores_alocados': 1, 'professores_disponiveis': 1}.items():
            self.assertEqual(response.context[key], value, key)
        self.assertContains(response, 'grade/dashboard.css')
        self.assertContains(response, reverse('grade:exibir_grade'))
        self.assertEqual([d['total'] for d in response.context['dias']], [1, 0, 0, 0, 0, 0, 0])
        self.assertEqual(list(response.context['unidades'])[0]['atendidas'], 1)

    def test_semana_vazia_e_data_invalida(self):
        response = self.client.get(self.url, {'semana': (self.segunda + timedelta(days=7)).isoformat()})
        self.assertEqual(response.context['total_aulas'], 0)
        self.assertEqual(response.context['pendentes'], 24)
        self.assertEqual(response.context['cobertura'], 0)
        self.assertContains(response, 'Sem aulas')
        self.assertEqual(self.client.get(self.url, {'semana': '9999-12-31'}).status_code, 200)
        self.assertEqual(self.client.get(self.url, {'semana': 'invalida'}).status_code, 200)

    def test_previa_nao_conta_nem_e_perdida(self):
        session = self.client.session
        session[CHAVE_PREVIA] = {'marcador': 'preservar'}
        session.save()
        antes = list(AlocacaoGrade.objects.values())
        response = self.client.get(self.url, {'semana': self.segunda.isoformat()})
        self.assertEqual(response.context['total_aulas'], 1)
        self.assertEqual(self.client.session[CHAVE_PREVIA], {'marcador': 'preservar'})
        self.assertEqual(list(AlocacaoGrade.objects.values()), antes)
        self.assertFalse(AprovacaoGrade.objects.exists())

    def test_legado_nao_aumenta_cobertura_e_outra_semana_nao_conta(self):
        AlocacaoGrade.objects.filter(pk=self.fixa.pk).update(demanda=None)
        response = self.client.get(self.url, {'semana': self.segunda.isoformat()})
        self.assertEqual(response.context['total_aulas'], 1)
        self.assertEqual(response.context['atendidas'], 0)
        self.assertEqual(response.context['aulas_sem_demanda'], 1)
        AlocacaoGrade.objects.filter(pk=self.fixa.pk).update(data=self.segunda + timedelta(days=7))
        self.assertEqual(self.client.get(self.url, {'semana': self.segunda.isoformat()}).context['total_aulas'], 0)

    def test_permissoes_e_get_apenas(self):
        self.assertEqual(self.client.post(self.url, {}).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 200)
        comum = get_user_model().objects.create_user('sem-permissao-dashboard')
        self.client.force_login(comum)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_sem_cadastros_nao_divide_por_zero(self):
        AlocacaoGrade.objects.all().delete()
        self.demanda.delete()
        response = self.client.get(self.url, {'semana': self.segunda.isoformat()})
        self.assertEqual(response.context['carga'], 0)
        self.assertEqual(response.context['cobertura'], 0)
        self.assertEqual(response.context['total_aulas'], 0)
