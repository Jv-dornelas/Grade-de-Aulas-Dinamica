"""Retira marcadores visuais dos nomes, mantendo IDs e identificação fictícia nas notas."""
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from grade.models import Curso, Disciplina, Professor, Turma, Unidade


class Command(BaseCommand):
    help = 'Remove [DEMO] e [DEMO VISUAL] somente dos nomes na cópia local, preservando vínculos.'

    @transaction.atomic
    def handle(self, *args, **options):
        if Path(settings.DATABASES['default']['NAME']).name != 'db.automacao.sqlite3':
            raise CommandError('Permitido apenas na cópia db.automacao.sqlite3.')
        sobrenomes = dict(zip(('Ana','Bruno','Carla','Diego','Elisa','Fábio','Gabriela','Hugo'),
                             ('Ribeiro','Martins','Souza','Lima','Costa','Almeida','Rocha','Santos')))
        total = 0
        for modelo in (Curso, Disciplina, Professor, Unidade, Turma):
            for obj in modelo.objects.all():
                nome = obj.nome
                novo = nome.replace('[DEMO VISUAL]', '').replace('[DEMO]', '').strip()
                if novo == nome:
                    continue
                if modelo is Professor and nome.startswith('[DEMO VISUAL]') and novo in sobrenomes:
                    novo += ' ' + sobrenomes[novo]
                if modelo is Curso and modelo.objects.exclude(pk=obj.pk).filter(nome=novo).exists():
                    raise CommandError('Já existe um curso com o nome resultante; nenhuma alteração foi salva.')
                if modelo is Turma and modelo.objects.exclude(pk=obj.pk).filter(unidade_id=obj.unidade_id, nome=novo).exists():
                    raise CommandError('Já existe uma turma com o nome resultante nessa unidade.')
                # Apenas o rótulo muda: não ressincronizar ou alterar demandas/histórico.
                modelo.objects.filter(pk=obj.pk).update(nome=novo)
                total += 1
        self.stdout.write(self.style.SUCCESS(f'{total} nomes atualizados; IDs, vínculos, disponibilidades e aulas preservados.'))
