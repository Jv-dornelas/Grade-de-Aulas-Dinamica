from django.core.management.base import BaseCommand
from grade.notificacoes import enviar_avisos


class Command(BaseCommand):
    help = 'Tenta enviar avisos pendentes/com erro de versões ainda vigentes; não repete enviados.'

    def handle(self, *args, **options):
        enviar_avisos()
        self.stdout.write('Processamento concluído. Confira os estados na revisão da aprovação.')
