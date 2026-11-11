"""Preenchimento opt-in de um período na cópia, usando a semana-modelo cadastrada."""
from datetime import date, timedelta
from pathlib import Path
import secrets
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from grade.automacao import assinatura_dados, salvar_previa
from grade.gerador import gerar_semana
from grade.models import AlocacaoGrade, Disponibilidade, DisponibilidadeHorario, Professor


class Command(BaseCommand):
    help = 'Copia disponibilidades explicitamente selecionadas e preenche semanas pelo gerador, sem substituir aulas.'

    def add_arguments(self, parser):
        parser.add_argument('--de', required=True)
        parser.add_argument('--ate', required=True)
        parser.add_argument('--semana-modelo', required=True)
        parser.add_argument('--professores', type=int, nargs='+', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        banco = settings.DATABASES['default']
        if banco['ENGINE'] != 'django.db.backends.sqlite3' or Path(banco['NAME']).name != 'db.automacao.sqlite3':
            raise CommandError('Permitido somente na cópia db.automacao.sqlite3.')
        try:
            inicio, fim, modelo = (date.fromisoformat(options[c]) for c in ('de', 'ate', 'semana_modelo'))
            modelo -= timedelta(days=modelo.weekday())
            if inicio.weekday() != 0 or fim.weekday() != 6 or not 0 <= (fim - inicio).days <= 182:
                raise ValueError
            if not date(1900, 1, 8) <= inicio <= fim <= date(2100, 12, 24):
                raise ValueError
        except (ValueError, TypeError):
            raise CommandError('Use início na segunda e fim no domingo, intervalo de até 26 semanas e anos entre 1900 e 2100.')
        ids = set(options['professores'])
        if Professor.objects.filter(pk__in=ids).count() != len(ids):
            raise CommandError('Há professores inexistentes na seleção.')
        base = {}
        for disp in Disponibilidade.objects.filter(professor_id__in=ids, data__range=(modelo, modelo + timedelta(days=6))):
            chave = (disp.professor_id, disp.data.weekday())
            anterior = base.get(chave, (True, True))
            base[chave] = (anterior[0] and disp.disponivel_manha, anterior[1] and disp.disponivel_tarde)
        especificas = list(DisponibilidadeHorario.objects.filter(
            professor_id__in=ids, data__range=(modelo, modelo + timedelta(days=6))))
        if ids - {p for p, _ in base}:
            raise CommandError('Todos os professores selecionados precisam de disponibilidade na semana-modelo.')
        adicionadas = 0
        semana = inicio
        while semana <= fim:
            for (prof_id, dia), (manha, tarde) in base.items():
                Disponibilidade.objects.get_or_create(professor_id=prof_id, data=semana + timedelta(days=dia),
                    defaults={'disponivel_manha': manha, 'disponivel_tarde': tarde})
            for disp in especificas:
                DisponibilidadeHorario.objects.get_or_create(professor_id=disp.professor_id,
                    data=semana + timedelta(days=disp.data.weekday()), horario_id=disp.horario_id,
                    defaults={'disponivel': disp.disponivel})
            assinatura = assinatura_dados(semana)
            resultado = gerar_semana(semana)
            if resultado['status'] not in ('optimal', 'feasible') or resultado.get('resumo', {}).get('pendentes', 1):
                raise CommandError(f'Semana de {semana}: inviável/inconclusiva; todo o lote será revertido. ' +
                                   ' '.join(resultado.get('pendencias', [])))
            novas = 0
            if resultado['propostas']:
                token = secrets.token_urlsafe(24)
                previa = {'token': token, 'inicio': semana.isoformat(), 'criada_em': time.time(),
                          'assinatura': assinatura, 'proximidade': 15, 'resultado': resultado}
                novas, _ = salvar_previa(previa, token)
            adicionadas += novas
            total = AlocacaoGrade.objects.filter(data__range=(semana, semana + timedelta(days=6))).count()
            self.stdout.write(f'{semana:%d/%m/%Y}: {novas} novas aulas; {total} no total; sem pendências (lote em transação).')
            semana += timedelta(days=7)
        self.stdout.write(self.style.SUCCESS(f'Período concluído: {adicionadas} aulas adicionadas; anteriores preservadas.'))
