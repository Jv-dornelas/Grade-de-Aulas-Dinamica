from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from unittest.mock import patch

from .factories import criar_cenario_grade
from ..models import AlocacaoGrade, AprovacaoGrade


class AprovacaoGradeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def setUp(self):
        self.url=reverse('grade:exibir_grade')
        self.client.force_login(self.gestor)

    def gerar_e_gravar(self, aprovar=False):
        self.client.post(self.url,{'acao':'gerar','semana':self.segunda.isoformat(),'proximidade':15})
        token=self.client.session['automacao_previa']['token']
        return self.client.post(self.url,{'acao':'salvar','token':token,
            'registrar_aprovacao':'on' if aprovar else ''})

    def revisar(self):
        return self.client.get(self.url,{'data':self.segunda.isoformat(),'aprovar':1})

    def aprovar(self, revisao, **dados):
        return self.client.post(self.url,{'acao':'aprovar_grade','data_grade':self.segunda.isoformat(),
            'assinatura':revisao.context['assinatura_aprovacao'],'revisado':'on',**dados})

    def test_botao_verde_disponivel_sem_previa_e_get_nao_aprova(self):
        r=self.client.get(self.url,{'data':self.segunda.isoformat()})
        self.assertContains(r,'class="btn btn-aprovar" id="aprovar-grade-btn"')
        self.assertContains(r,'Aprovar grade</a>')
        self.assertEqual(AprovacaoGrade.objects.count(),0)
        r=self.client.get(r.context['url_revisar_aprovacao'])
        self.assertContains(r,'Confirmar aprovação da grade')
        self.assertEqual(AprovacaoGrade.objects.count(),0)

    def test_aprovar_semana_ja_gravada_preserva_todas_as_aulas(self):
        self.gerar_e_gravar()
        self.assertEqual(AprovacaoGrade.objects.count(),0)
        antes=list(AlocacaoGrade.objects.order_by('pk').values())
        revisao=self.revisar()
        self.assertEqual(revisao.context['resumo_aprovacao']['pendentes'],0)
        self.assertEqual(self.aprovar(revisao).status_code,302)
        aprovacao=AprovacaoGrade.objects.get()
        self.assertEqual(aprovacao.aprovado_por,self.gestor)
        self.assertEqual(aprovacao.total_aulas,24)
        self.assertFalse(aprovacao.parcial)
        self.assertEqual(list(AlocacaoGrade.objects.order_by('pk').values()),antes)
        self.assertTrue(self.revisar().context['aprovacao_vigente'])

    def test_aprovar_previa_grava_e_aprova_na_mesma_transacao(self):
        self.assertEqual(self.gerar_e_gravar(aprovar=True).status_code,302)
        self.assertEqual(AlocacaoGrade.objects.count(),24)
        self.assertEqual(AprovacaoGrade.objects.get().total_aulas,24)

    def test_parcial_exige_aceite_explicito(self):
        revisao=self.revisar()
        self.assertEqual(revisao.context['resumo_aprovacao']['pendentes'],23)
        r=self.aprovar(revisao)
        self.assertIn('incompleta',r.context['erro_aprovacao'])
        self.assertEqual(AprovacaoGrade.objects.count(),0)
        self.assertEqual(self.aprovar(self.revisar(),aceitar_parcial_aprovacao='on').status_code,302)
        self.assertTrue(AprovacaoGrade.objects.get().parcial)
        self.assertEqual(AprovacaoGrade.objects.get().pendentes,23)

    def test_revisao_desatualizada_nao_aprova(self):
        self.gerar_e_gravar()
        revisao=self.revisar()
        self.unidade.responsavel='Nova coordenação';self.unidade.save()
        r=self.aprovar(revisao)
        self.assertIn('mudaram',r.context['erro_aprovacao'])
        self.assertEqual(AprovacaoGrade.objects.count(),0)

    def test_alteracao_exige_nova_aprovacao_e_preserva_historico(self):
        self.gerar_e_gravar(aprovar=True)
        self.professor.nome='Nome revisado';self.professor.save()
        revisao=self.revisar()
        self.assertTrue(revisao.context['aprovacao_alterada'])
        self.assertFalse(revisao.context['aprovacao_vigente'])
        self.assertEqual(self.aprovar(revisao).status_code,302)
        self.assertEqual(AprovacaoGrade.objects.count(),2)

    def test_repetir_aprovacao_nao_duplica_registro(self):
        self.gerar_e_gravar()
        revisao=self.revisar()
        self.assertEqual(self.aprovar(revisao).status_code,302)
        self.assertEqual(self.aprovar(revisao).status_code,302)
        self.assertEqual(AprovacaoGrade.objects.count(),1)

    def test_aprovacao_exige_revisao_autenticacao_e_csrf(self):
        r=self.aprovar(self.revisar(),revisado='')
        self.assertIn('revisou',r.context['erro_aprovacao'])
        cliente=Client(enforce_csrf_checks=True);cliente.force_login(self.gestor)
        self.assertEqual(cliente.post(self.url,{'acao':'aprovar_grade'}).status_code,403)
        self.client.force_login(get_user_model().objects.create_user('sem-permissao-aprovar'))
        self.assertEqual(self.client.post(self.url,{'acao':'aprovar_grade'}).status_code,302)
        self.assertEqual(AprovacaoGrade.objects.count(),0)

    def test_semana_vazia_nao_e_aprovada(self):
        AlocacaoGrade.objects.all().delete()
        r=self.aprovar(self.revisar(),aceitar_parcial_aprovacao='on')
        self.assertIn('Não há aulas',r.context['erro_aprovacao'])
        self.assertEqual(AprovacaoGrade.objects.count(),0)

    def test_falha_na_aprovacao_da_previa_reverte_a_gravacao(self):
        with patch('grade.aprovacao.registrar_aprovacao',side_effect=ValidationError('Falha ao registrar aprovação')):
            r=self.gerar_e_gravar(aprovar=True)
        self.assertEqual(r.status_code,200)
        self.assertIn('Falha',r.context['erro'])
        self.assertEqual(AlocacaoGrade.objects.count(),1)
        self.assertEqual(AprovacaoGrade.objects.count(),0)
        self.assertIn('automacao_previa',self.client.session)

    def test_geracao_sem_novas_aulas_nao_bloqueia_aprovacao(self):
        self.gerar_e_gravar()
        self.client.post(self.url,{'acao':'gerar','semana':self.segunda.isoformat(),'proximidade':15})
        self.assertEqual(self.client.session['automacao_previa']['resultado']['propostas'],[])
        r=self.aprovar(self.revisar())
        self.assertEqual(r.status_code,302)
        self.assertEqual(AprovacaoGrade.objects.count(),1)
        self.assertNotIn('automacao_previa',self.client.session)
