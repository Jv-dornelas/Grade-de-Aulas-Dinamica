"""Dados fictícios para experimentar o gerador, exclusivamente no banco de testes."""
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from grade.models import (DemandaAula, Disciplina, Disponibilidade,
                          MatrizDistancia, Professor, Turma, Unidade, HorarioCurricular)
from grade.jornada import obter_horarios_padrao


class Command(BaseCommand):
    help = 'Prepara um cenário fictício na cópia db.automacao.sqlite3, sem gravar aulas.'

    def add_arguments(self, parser):
        parser.add_argument('--semana', help='Uma data da semana no formato AAAA-MM-DD.')

    @transaction.atomic
    def handle(self, *args, **options):
        if Path(settings.DATABASES['default']['NAME']).name != 'db.automacao.sqlite3':
            raise CommandError('Este comando só pode usar db.automacao.sqlite3. O banco principal não foi alterado.')
        try:
            inicio = date.fromisoformat(options['semana']) if options['semana'] else timezone.localdate() + timedelta(days=1)
            inicio -= timedelta(days=inicio.weekday())
        except (ValueError, OverflowError):
            raise CommandError('Informe uma data válida no formato AAAA-MM-DD.')
        if Turma.objects.filter(nome='[DEMO] Turma 1').exists():
            self.stdout.write('O cenário de demonstração já existe. Nenhum cadastro foi sobrescrito.')
            return
        centro = Unidade.objects.create(nome='[DEMO] Escola Centro', responsavel='Coordenação de teste')
        norte = Unidade.objects.create(nome='[DEMO] Escola Norte', responsavel='Coordenação de teste')
        for origem, destino in ((centro, norte), (norte, centro)):
            MatrizDistancia.objects.create(origem=origem, destino=destino, tempo_minutos=20)
        horarios = obter_horarios_padrao()
        matematica = Disciplina.objects.create(nome='[DEMO] Matemática', area='EXATAS')
        portugues = Disciplina.objects.create(nome='[DEMO] Português', area='HUMANAS')
        ana = Professor.objects.create(nome='[DEMO] Ana', limite_aulas=2, unidade_oficial=centro)
        bruno = Professor.objects.create(nome='[DEMO] Bruno', limite_aulas=2, unidade_oficial=centro,
                                         parente_vinculado=ana)
        for professor, disciplina in ((ana, matematica), (bruno, portugues)):
            professor.disciplinas.add(disciplina)
            professor.unidades_permitidas.add(centro, norte)
            for dia in range(5):
                Disponibilidade.objects.create(professor=professor, data=inicio + timedelta(days=dia),
                                                disponivel_manha=True, disponivel_tarde=True)
        for indice, unidade in enumerate((centro, norte)):
            turma = Turma.objects.create(nome='[DEMO] Turma 1', unidade=unidade)
            turma.horarios.set(horarios)
            for professor, disciplina in ((ana, matematica), (bruno, portugues)):
                DemandaAula.objects.create(turma=turma, disciplina=disciplina, professor=professor,
                                          quantidade_semana=3)
            for i, demanda in enumerate(turma.demandas.order_by('pk')):
                for dia in range(3):
                    HorarioCurricular.objects.create(turma=turma, demanda=demanda, dia_semana=dia,
                                                     horario=horarios[indice * 4 + i])
        self.stdout.write(self.style.SUCCESS(
            f'Cenário pronto para {inicio:%d/%m/%Y}: 2 professores parentes, 2 escolas e demanda de 12 aulas. '
            'Nenhuma aula foi gravada. Abra /automacao/ e gere a prévia.'))
