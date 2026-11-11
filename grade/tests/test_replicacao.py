from datetime import date, timedelta
import time

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .factories import criar_cenario_grade
from ..automacao import CHAVE_PREVIA, assinatura_dados, salvar_previa
from ..gerador import gerar_semana
from ..models import AlocacaoGrade, AprovacaoGrade, Disponibilidade, DisponibilidadeHorario
from ..replicacao import (CHAVE_REPLICA, ReplicacaoForm, criar_previa,
                          confirmar_replica)


class ReplicacaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)
        resultado = gerar_semana(cls.segunda)
        salvar_previa({'token':'completar-modelo', 'inicio': cls.segunda.isoformat(),
            'assinatura':assinatura_dados(cls.segunda), 'criada_em':time.time(),
            'resultado':resultado, 'proximidade':15}, 'completar-modelo')

    def setUp(self):
        self.client.force_login(self.gestor)
        self.url = reverse('grade:exibir_grade')
        self.destino = date(2027, 3, 1)

    def preparar(self, ultima=None):
        return criar_previa(self.segunda, self.destino, ultima or self.destino)

    def test_mes_completo_preserva_origem_horarios_e_nao_exige_disponibilidade_datada(self):
        antes = list(AlocacaoGrade.objects.order_by('pk').values())
        p = self.preparar(date(2027, 3, 29))
        self.assertEqual(p['fim'], '2027-04-04')
        self.assertEqual(len(p['resultado']['propostas']), 120)
        self.assertEqual(list(AlocacaoGrade.objects.order_by('pk').values()), antes)
        self.assertEqual(p['resultado']['resumo']['pendentes'], 0)
        total = confirmar_replica(p, p['token'], revisado=True)
        self.assertEqual(total, 120)
        self.assertEqual(AlocacaoGrade.objects.count(), 144)
        self.assertFalse(Disponibilidade.objects.filter(data__gte=self.destino).exists())
        self.assertEqual(list(AlocacaoGrade.objects.filter(data__lt=self.destino).order_by('pk').values()), antes)

    def test_repeticao_nao_duplica_e_nao_copia_aprovacao(self):
        from ..aprovacao import registrar_aprovacao
        registrar_aprovacao(self.segunda, self.gestor, assinatura_dados(self.segunda))
        p = self.preparar()
        confirmar_replica(p, p['token'], revisado=True)
        q = self.preparar()
        self.assertEqual(q['repetidas'], 24)
        self.assertEqual(q['resultado']['propostas'], [])
        self.assertEqual(confirmar_replica(q, q['token'], revisado=True), 0)
        self.assertEqual(AlocacaoGrade.objects.count(), 48)
        self.assertEqual(AprovacaoGrade.objects.count(), 1)
        self.assertFalse(AprovacaoGrade.objects.filter(semana=self.destino).exists())

    def test_bloqueio_explicito_no_destino_rejeita_periodo_inteiro(self):
        DisponibilidadeHorario.objects.create(professor=self.professor, data=self.destino+timedelta(days=7),
                                              horario=self.horarios[0], disponivel=False)
        with self.assertRaises(ValidationError):
            self.preparar(self.destino+timedelta(days=7))
        self.assertEqual(AlocacaoGrade.objects.count(), 24)

    def test_modificacao_em_qualquer_semana_invalida_previa(self):
        p = self.preparar(self.destino+timedelta(days=7))
        DisponibilidadeHorario.objects.create(professor=self.professor, data=self.destino+timedelta(days=7),
                                              horario=self.horarios[0], disponivel=False)
        with self.assertRaisesMessage(ValidationError, 'mudaram'):
            confirmar_replica(p, p['token'], revisado=True)
        self.assertEqual(AlocacaoGrade.objects.count(), 24)

    def test_mudanca_na_origem_invalida_e_token_revisao_expiracao_sao_exigidos(self):
        p = self.preparar()
        with self.assertRaises(ValidationError):
            confirmar_replica(p, 'errado', revisado=True)
        with self.assertRaises(ValidationError):
            confirmar_replica(p, p['token'])
        p['criada_em'] -= 1900
        with self.assertRaisesMessage(ValidationError, 'expirou'):
            confirmar_replica(p, p['token'], revisado=True)
        p = self.preparar()
        AlocacaoGrade.objects.filter(pk=self.fixa.pk).update(motivo_pendencia='Alterado')
        with self.assertRaisesMessage(ValidationError, 'mudaram'):
            confirmar_replica(p, p['token'], revisado=True)

    def test_sem_professor_exige_aceite_parcial_e_preserva_card(self):
        AlocacaoGrade.objects.filter(pk=self.fixa.pk).update(professor=None)
        p = self.preparar()
        self.assertEqual(p['resultado']['resumo']['pendentes'], 1)
        with self.assertRaises(ValidationError):
            confirmar_replica(p, p['token'], revisado=True)
        confirmar_replica(p, p['token'], revisado=True, aceitar_parcial=True)
        self.assertEqual(AlocacaoGrade.objects.filter(data__gte=self.destino, professor=None).count(), 1)

    def test_interface_previa_nas_duas_semanas_quatro_modos_pdf_e_confirmacao(self):
        r = self.client.post(self.url, {'acao':'replicar', 'semana_modelo':self.segunda,
            'primeira_semana':self.destino, 'ultima_semana':self.destino+timedelta(days=7)})
        self.assertEqual(r.status_code, 302)
        p = self.client.session[CHAVE_REPLICA]
        for dia in [self.destino, self.destino+timedelta(days=7)]:
            for modo in ['curso','turma','unidade','professor']:
                r = self.client.get(self.url, {'data':dia.isoformat(), 'por':modo})
                self.assertEqual(r.context['total_propostas'], 24)
                self.assertEqual(r.context['total_visivel'], 24)
                self.assertContains(r, 'Confirmar replicação do período')
                self.assertEqual(self.client.session[CHAVE_REPLICA]['token'], p['token'])
            pdf = self.client.get(reverse('grade:grade_pdf'), {'data':dia.isoformat()})
            self.assertEqual(pdf.status_code, 200)
            self.assertTrue(b''.join(pdf.streaming_content).startswith(b'%PDF'))
        self.assertEqual(AlocacaoGrade.objects.count(), 24)
        r = self.client.post(self.url, {'acao':'confirmar_replicacao','token':p['token'],
                                      'revisado_replicacao':'on'})
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(CHAVE_REPLICA, self.client.session)
        self.assertEqual(AlocacaoGrade.objects.count(), 72)

    def test_previa_nao_e_substituida_por_geracao_e_editor_nao_grava(self):
        session = self.client.session; p = self.preparar(); session[CHAVE_REPLICA] = p; session.save()
        r = self.client.post(self.url, {'acao':'gerar','semana':self.destino,'proximidade':15})
        self.assertContains(r, 'Confirme ou descarte')
        self.assertNotIn(CHAVE_PREVIA, self.client.session)
        r = self.client.get(self.url, {'data':self.destino.isoformat(),'proposta':0})
        self.assertIn('replicação', r.context['erro_editor'])
        self.assertEqual(AlocacaoGrade.objects.count(), 24)
        self.client.post(self.url, {'acao':'descartar_replicacao'})
        self.assertNotIn(CHAVE_REPLICA, self.client.session)

    def test_permissoes_e_csrf(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {'acao':'replicar'}).status_code, 302)
        self.client.force_login(get_user_model().objects.create_user('comum-replica'))
        self.assertEqual(self.client.post(self.url, {'acao':'replicar'}).status_code, 302)
        c = Client(enforce_csrf_checks=True); c.force_login(self.gestor)
        self.assertEqual(c.post(self.url, {'acao':'replicar'}).status_code, 403)

    def test_formulario_limita_periodo_e_semana_modelo_vazia(self):
        with self.assertRaises(ValidationError):
            criar_previa(date(2027,2,1), self.destino, self.destino)
        f = ReplicacaoForm({'semana_modelo':self.segunda,'primeira_semana':self.segunda,'ultima_semana':self.destino})
        self.assertFalse(f.is_valid())
        f = ReplicacaoForm({'semana_modelo':self.segunda,'primeira_semana':self.destino,
                           'ultima_semana':self.destino+timedelta(weeks=26)})
        self.assertFalse(f.is_valid())
