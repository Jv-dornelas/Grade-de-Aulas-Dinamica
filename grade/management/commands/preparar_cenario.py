"""Cria/valida cenários exclusivamente em arquivos SQLite isolados."""
from datetime import date, timedelta
import json
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from grade.cenarios import ESPERADOS, preparar_cenario, validar_cenario
from grade.models import Curso, Unidade


class Command(BaseCommand):
    help = 'Prepara cenário isolado em tmp/cenarios/db.cenario.<cenario>.sqlite3; nunca limpa a base atual.'

    def add_arguments(self, parser):
        parser.add_argument('--cenario', required=True, choices=sorted(ESPERADOS))
        parser.add_argument('--semana', default='2027-03-01')

    def handle(self, *args, **opcoes):
        nome = opcoes['cenario']
        banco = settings.DATABASES['default']
        pasta = Path(settings.BASE_DIR).resolve()/'tmp'/'cenarios'
        arquivo = f'db.cenario.{nome}.sqlite3'
        esperado = (pasta/arquivo).resolve()
        if esperado.parent != pasta or esperado.name != arquivo:
            raise CommandError('O destino não pode ser um link para outro arquivo ou diretório.')
        if banco['ENGINE'] != 'django.db.backends.sqlite3' or Path(banco['NAME']).resolve() != esperado:
            raise CommandError(f'Use SQLITE_NAME=tmp/cenarios/db.cenario.{nome}.sqlite3. O banco atual não foi alterado.')
        if not esperado.is_relative_to(Path(settings.BASE_DIR).resolve()):
            raise CommandError('O arquivo precisa ficar dentro do workspace.')
        try:
            inicio = date.fromisoformat(opcoes['semana'])
            if not date(1900,1,8) <= inicio <= date(2100,12,24):
                raise ValueError
            inicio -= timedelta(days=inicio.weekday())
        except ValueError as exc:
            raise CommandError('Informe uma data entre 1900 e 2100.') from exc
        esperado.parent.mkdir(parents=True, exist_ok=True)
        call_command('migrate', interactive=False, verbosity=0)
        marcador = f'cenario:{nome}:{inicio.isoformat()}'
        if Unidade.objects.exists():
            if not Curso.objects.filter(observacoes=marcador).exists():
                raise CommandError('O banco já contém outros dados. Nada foi apagado ou sobrescrito.')
            relatorio = validar_cenario(nome, inicio)
        else:
            relatorio = preparar_cenario(nome, inicio)
        saida = esperado.with_suffix('.json')
        saida.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(json.dumps(relatorio, ensure_ascii=False))
        if not relatorio['confere']:
            raise CommandError('O resultado diverge do cenário esperado. Consulte o relatório; nenhum cadastro foi limpo.')
