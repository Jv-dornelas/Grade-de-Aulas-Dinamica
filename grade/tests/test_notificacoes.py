from unittest.mock import patch
from django.core import mail
from django.test import TestCase, override_settings
from django.db import transaction
from .factories import criar_cenario_grade
from ..aprovacao import registrar_aprovacao
from ..automacao import assinatura_dados
from ..models import AvisoGradeEmail
from ..notificacoes import enviar_avisos


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NotificacoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def setUp(self):
        self.professor.email = 'professor@example.test'
        self.professor.save()

    def aprovar(self):
        return registrar_aprovacao(self.segunda, self.gestor, assinatura_dados(self.segunda), True)

    def test_envio_so_depois_commit_sem_duplicar(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.aprovar()
            self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.professor.email])
        self.assertIn('/mobile/', mail.outbox[0].body)
        with self.captureOnCommitCallbacks(execute=True):
            self.aprovar()
        enviar_avisos()
        self.assertEqual(len(mail.outbox), 1)

    def test_rollback_nao_cria_aviso(self):
        with self.assertRaises(ValueError):
            with transaction.atomic():
                self.aprovar()
                raise ValueError()
        self.assertFalse(AvisoGradeEmail.objects.exists())

    def test_falha_preserva_aprovacao_e_permite_tentar_novamente(self):
        with patch('grade.notificacoes.send_mail', side_effect=OSError()):
            with self.captureOnCommitCallbacks(execute=True):
                aprovacao, _ = self.aprovar()
        self.assertEqual(aprovacao.avisos_email.get().estado, 'erro')
        enviar_avisos()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(aprovacao.avisos_email.get().tentativas, 2)

    def test_sem_email_e_recuperacao(self):
        self.professor.email = ''
        self.professor.save()
        with self.captureOnCommitCallbacks(execute=True):
            self.aprovar()
        self.assertEqual(AvisoGradeEmail.objects.get().estado, 'sem_email')
        self.professor.email = 'corrigido@example.test'
        self.professor.save()
        # Cadastro também invalida aprovação: exige revisão antes de avisar.
        enviar_avisos()
        self.assertEqual(AvisoGradeEmail.objects.get().estado, 'desatualizado')

    def test_cadastro_alterado_sem_mudar_aulas_nao_repete_aviso(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.aprovar()
        self.unidade.responsavel = 'Outra pessoa'
        self.unidade.save()
        with self.captureOnCommitCallbacks(execute=True):
            self.aprovar()
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(AvisoGradeEmail.objects.filter(estado='sem_alteracao').exists())

    def test_professor_removido_recebe_aviso(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.aprovar()
        self.fixa.professor = None
        self.fixa.save()
        with self.captureOnCommitCallbacks(execute=True):
            self.aprovar()
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('não possui aulas', mail.outbox[-1].body)
