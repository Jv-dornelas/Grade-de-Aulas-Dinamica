from collections import Counter
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from grade.horarios_curriculares import importar_semana, salvar_materias
from grade.models import Turma


class Command(BaseCommand):
    help = 'Aproveita somente a distribuição de matérias de uma semana, sem alterar professores ou aulas.'

    def add_arguments(self, parser):
        parser.add_argument('--semana', required=True)
        parser.add_argument('--turmas', nargs='+', type=int, required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        if Path(settings.DATABASES['default']['NAME']).name != 'db.automacao.sqlite3':
            raise CommandError('Permitido apenas na cópia local db.automacao.sqlite3.')
        try:
            semana = date.fromisoformat(options['semana'])
        except ValueError:
            raise CommandError('Informe uma data válida.')
        ids = set(options['turmas'])
        turmas = list(Turma.objects.filter(pk__in=ids))
        if len(turmas) != len(ids):
            raise CommandError('Turma inexistente na seleção.')
        for turma in turmas:
            if turma.distribuicao_curricular.exists():
                self.stdout.write(f'{turma}: distribuição existente preservada.')
                continue
            itens = importar_semana(turma, semana)
            contagem = Counter(i['demanda_id'] for i in itens)
            esperada = dict(turma.demandas.filter(ativa=True).values_list('pk', 'quantidade_semana'))
            if dict(contagem) != esperada:
                raise CommandError(f'{turma}: semana incompleta; nenhuma distribuição foi substituída.')
            salvar_materias(turma, itens)
            self.stdout.write(f'{turma}: {len(itens)} horários fixos; aulas e professores anteriores preservados.')
