from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .factories import criar_cenario_grade
from ..models import AlocacaoGrade, Disponibilidade


class PeriodoLocalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def executar(self, banco='db.automacao.sqlite3'):
        with patch('grade.management.commands.preencher_periodo_local.settings', SimpleNamespace(DATABASES={
                'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': '/app/' + banco}})):
            call_command('preencher_periodo_local', de='2026-11-16', ate='2026-11-29',
                         semana_modelo='2026-11-09', professores=[self.professor.pk], stdout=StringIO())

    def test_periodo_real_completo_e_idempotente(self):
        self.executar()
        self.assertEqual(AlocacaoGrade.objects.count(), 49)
        self.assertTrue(AlocacaoGrade.objects.filter(pk=self.fixa.pk).exists())
        self.executar()
        self.assertEqual(AlocacaoGrade.objects.count(), 49)

    def test_recusa_banco_original(self):
        with self.assertRaises(CommandError):
            self.executar('db.sqlite3')
        self.assertEqual(AlocacaoGrade.objects.count(), 1)

    def test_recusa_existente_e_preservada_e_lote_revertido(self):
        Disponibilidade.objects.create(professor=self.professor, data='2026-11-18',
                                        disponivel_manha=True, disponivel_tarde=False)
        with self.assertRaises(CommandError):
            self.executar()
        self.assertEqual(AlocacaoGrade.objects.count(), 1)
        self.assertFalse(Disponibilidade.objects.get(professor=self.professor, data='2026-11-18').disponivel_tarde)
