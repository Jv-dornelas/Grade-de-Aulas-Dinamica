from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ..models import AlocacaoGrade, Curso, Disponibilidade, Professor, Turma


class DemoVisualTests(TestCase):
    def executar(self):
        with patch('grade.management.commands.preparar_demo_visual.settings', SimpleNamespace(DATABASES={'default': {
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': '/app/db.automacao.sqlite3'}})):
            call_command('preparar_demo_visual', semana='2026-11-09', dia_contraturno=2, stdout=StringIO())

    def test_seed_real_preserva_apenas_duas_fixas_e_nao_duplica(self):
        self.executar()
        self.assertEqual(Curso.objects.count(), 1)
        self.assertEqual(Curso.objects.get().aulas_semanais, 24)
        self.assertEqual(Turma.objects.count(), 2)
        self.assertEqual(Professor.objects.count(), 8)
        self.assertEqual(AlocacaoGrade.objects.count(), 2)
        self.assertEqual(Disponibilidade.objects.count(), 40)
        self.assertEqual({t.dia_contraturno for t in Turma.objects.all()}, {2})
        self.executar()
        self.assertEqual(AlocacaoGrade.objects.count(), 2)
        self.assertEqual(Professor.objects.count(), 8)

    def test_banco_original_e_recusado(self):
        with patch('grade.management.commands.preparar_demo_visual.settings', SimpleNamespace(DATABASES={'default': {
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': '/app/db.sqlite3'}})):
            with self.assertRaises(CommandError):
                call_command('preparar_demo_visual', semana='2026-11-09', dia_contraturno=2, stdout=StringIO())
        self.assertEqual(Curso.objects.count(), 0)

    def test_falha_de_viabilidade_reverte_todos_os_cadastros(self):
        with patch('grade.management.commands.preparar_demo_visual.gerar_semana', return_value={
            'status': 'invalid', 'pendencias': ['Cenário incompatível']}):
            with self.assertRaises(CommandError):
                self.executar()
        self.assertEqual(Curso.objects.count(), 0)
        self.assertEqual(Professor.objects.count(), 0)
        self.assertEqual(AlocacaoGrade.objects.count(), 0)
