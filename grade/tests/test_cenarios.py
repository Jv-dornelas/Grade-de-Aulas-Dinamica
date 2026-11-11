from datetime import date
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from ..cenarios import preparar_cenario, validar_cenario
from ..gerador import gerar_semana
from ..models import AlocacaoGrade, MatrizDistancia, Unidade


class CenariosTests(TestCase):
    inicio = date(2027,3,1)

    def conferir(self,nome):
        r=preparar_cenario(nome,self.inicio)
        self.assertTrue(r['confere'],r)
        self.assertFalse(AlocacaoGrade.objects.exists())
        return r

    def test_completo(self):
        self.conferir('completo')

    def test_falta_professor(self):
        self.conferir('falta_professor')

    def test_disputa_sala(self):
        self.conferir('disputa_sala')

    def test_paralelo(self):
        self.conferir('paralelo')

    def test_deslocamento_e_causa_controlada(self):
        r=self.conferir('deslocamento')
        self.assertEqual(r['obtido']['com_docente'],1)
        MatrizDistancia.objects.update(tempo_minutos=0)
        self.assertEqual(sum(bool(p['professor_id']) for p in gerar_semana(self.inicio)['propostas']),2)

    def test_comando_recusa_banco_atual_e_builder_recusa_limpar_dados(self):
        Unidade.objects.create(nome='Preservar',responsavel='Gestor')
        with self.assertRaises(CommandError):
            call_command('preparar_cenario',cenario='completo',stdout=StringIO())
        with self.assertRaises(ValidationError):
            preparar_cenario('completo',self.inicio)
        self.assertEqual(Unidade.objects.get().nome,'Preservar')

    def test_validacao_repetida_nao_duplica_cadastros(self):
        self.conferir('completo')
        antes=Unidade.objects.count()
        self.assertTrue(validar_cenario('completo',self.inicio)['confere'])
        self.assertEqual(Unidade.objects.count(),antes)

    def test_comando_nao_segue_link_para_banco_original(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from types import SimpleNamespace
        from unittest.mock import patch
        with TemporaryDirectory() as temporario:
            raiz=Path(temporario); pasta=raiz/'tmp'/'cenarios';pasta.mkdir(parents=True)
            original=raiz/'db.sqlite3';original.write_bytes(b'preservar')
            destino=pasta/'db.cenario.completo.sqlite3';destino.symlink_to(original)
            config=SimpleNamespace(BASE_DIR=raiz,DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':destino}})
            with patch('grade.management.commands.preparar_cenario.settings',config), self.assertRaises(CommandError):
                call_command('preparar_cenario',cenario='completo',stdout=StringIO())
            self.assertEqual(original.read_bytes(),b'preservar')
