from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .factories import criar_cenario_grade
from ..aprovacao import registrar_aprovacao
from ..automacao import CHAVE_PREVIA, assinatura_dados
from ..indicadores import resumir_planejamento
from ..models import AlocacaoGrade, AprovacaoGrade


class IndicadoresTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def setUp(self):
        self.client.force_login(self.gestor)
        self.url = reverse('grade:exibir_grade')

    def completar_sem_professores(self):
        for i in range(5):
            dia = self.segunda+timedelta(days=i)
            for h in self.horarios:
                if self.turma.permite_horario(i, h) and (dia, h.pk) != (self.fixa.data, self.fixa.horario_id):
                    AlocacaoGrade.objects.create(data=dia, horario=h, unidade=self.unidade,
                        turma=self.turma, disciplina=self.disciplina, demanda=self.demanda)

    def test_grade_cheia_nao_significa_atendimento_completo(self):
        self.completar_sem_professores()
        resumo = resumir_planejamento(AlocacaoGrade.objects.all())
        self.assertEqual(resumo['distribuidas'], 24)
        self.assertEqual(resumo['com_docente'], 1)
        self.assertEqual(resumo['sem_docente'], 23)
        self.assertEqual(resumo['sem_horario'], 0)
        with self.assertRaises(ValidationError):
            registrar_aprovacao(self.segunda, self.gestor, assinatura_dados(self.segunda))
        registrar_aprovacao(self.segunda, self.gestor, assinatura_dados(self.segunda), True)
        r = self.client.get(self.url, {'data':self.segunda.isoformat()})
        self.assertEqual(r.context['indicadores_grade']['aceitas'], 23)
        self.assertEqual(r.context['indicadores_grade']['sem_docente'], 23)
        self.assertContains(r, 'Grade aprovada com pendências')
        self.assertContains(r, 'aceite não significa resolução')
        a = AlocacaoGrade.objects.filter(professor=None).first()
        AlocacaoGrade.objects.filter(pk=a.pk).update(professor=self.professor)
        r = self.client.get(self.url, {'data':self.segunda.isoformat()})
        self.assertEqual(r.context['indicadores_grade']['aceitas'], 0)
        self.assertEqual(r.context['indicadores_grade']['com_docente'], 2)
        self.assertEqual(r.context['estado_grade'], 'Alterada após a aprovação')

    def test_previa_separada_de_dados_salvos_e_botao_de_rascunho(self):
        r = self.client.post(self.url, {'acao':'gerar','semana':self.segunda,'proximidade':15})
        self.assertTrue(r.context['indicadores_grade']['inclui_previa'])
        self.assertEqual(r.context['indicadores_grade']['distribuidas'], 24)
        self.assertContains(r, 'Salvar sem aprovar')
        self.assertEqual(AlocacaoGrade.objects.count(), 1)
        token=self.client.session[CHAVE_PREVIA]['token']
        r=self.client.post(self.url, {'acao':'salvar','token':token})
        self.assertEqual(r.status_code,302)
        self.assertEqual(AlocacaoGrade.objects.count(),24)
        self.assertFalse(AprovacaoGrade.objects.exists())

    def test_falta_de_horario_nao_e_rotulada_como_falta_de_professor(self):
        resumo=resumir_planejamento(AlocacaoGrade.objects.all())
        self.assertEqual(resumo['sem_horario'],23)
        self.assertEqual(resumo['sem_docente'],0)

    def test_dashboard_mostra_planejamento_e_pendencias_aceitas_separados(self):
        self.completar_sem_professores()
        r=self.client.get(reverse('grade:inicio'), {'semana':self.segunda.isoformat()})
        self.assertEqual(r.context['planejamento']['distribuidas'],24)
        self.assertEqual(r.context['planejamento']['com_docente'],1)
        self.assertEqual(r.context['pendencias_aceitas'],0)

    def test_estilo_compartilhado_e_confirmacoes_destrutivas(self):
        for rota,args in [('cadastrar_professor',[]),('cadastrar_unidade',[]),('cadastrar_disciplina',[]),
                          ('cursos',[]),('turmas',[]),('salas',[]),('confirmar_exclusao_disciplina',[self.disciplina.pk])]:
            r=self.client.get(reverse('grade:'+rota,args=args))
            self.assertContains(r,'grade/formularios.css')
            self.assertContains(r,'pagina-cadastro')
        self.assertContains(r, 'data-acao="excluir"')
        self.assertContains(r, 'Confirmar exclusão')

    def test_previa_expirada_orienta_preparar_novamente(self):
        import time
        self.client.post(self.url, {'acao':'gerar','semana':self.segunda,'proximidade':15})
        session=self.client.session
        previa=session[CHAVE_PREVIA];previa['criada_em']=time.time()-1900
        session[CHAVE_PREVIA]=previa;session.save()
        r=self.client.get(self.url, {'data':self.segunda.isoformat()})
        self.assertEqual(r.context['estado_grade'],'Prévia expirada')
        self.assertFalse(r.context['pode_salvar'])
