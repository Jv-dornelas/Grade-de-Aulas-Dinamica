"""Consolida horários da demonstração sem apagar aulas ou perder os vínculos."""
import re

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from grade.jornada import horarios_padrao, obter_horarios_padrao
from grade.models import AlocacaoGrade, DisponibilidadeHorario, HorarioAula, Turma
from grade.restricoes import MotorRestricoes


class Command(BaseCommand):
    help = 'Padroniza a grade em aulas de 50 minutos, consolida duplicados e corrige os horários antigos da demo.'

    @transaction.atomic
    def handle(self, *args, **options):
        anteriores = list(HorarioAula.objects.order_by('pk'))
        padrao = horarios_padrao()
        indices = {(inicio, fim): i for i, (_, inicio, fim) in enumerate(padrao)}
        destinos = {}
        for horario in anteriores:
            indice = indices.get((horario.hora_inicio, horario.hora_fim))
            demo = re.fullmatch(r'\[DEMO\] Aula (\d+)', horario.nome)
            if demo:
                indice = int(demo.group(1)) - 1
                if not 0 <= indice < len(padrao) // 2:
                    indice = None
            if indice is None:
                raise CommandError(f'Horário fora do padrão: {horario}. Revise seu destino antes de continuar. Nenhum dado foi alterado.')
            destinos[horario.pk] = indice
        oficiais = obter_horarios_padrao()
        for horario in anteriores:
            destino = oficiais[destinos[horario.pk]]
            if horario.pk == destino.pk:
                continue
            AlocacaoGrade.objects.filter(horario=horario).update(horario=destino)
            for turma in Turma.objects.filter(horarios=horario):
                turma.horarios.add(destino)
                turma.horarios.remove(horario)
            for disponibilidade in DisponibilidadeHorario.objects.filter(horario=horario):
                outra = DisponibilidadeHorario.objects.filter(
                    professor_id=disponibilidade.professor_id, data=disponibilidade.data,
                    horario=destino).first()
                if outra:
                    outra.disponivel = outra.disponivel and disponibilidade.disponivel
                    outra.save(update_fields=['disponivel'])
                    disponibilidade.delete()
                else:
                    disponibilidade.horario = destino
                    disponibilidade.save(update_fields=['horario'])
            horario.delete()  # Todos os vínculos já foram transferidos.
        for horario, (nome, _, _) in zip(oficiais, padrao):
            horario.nome = nome
            horario.save(update_fields=['nome'])
        try:
            MotorRestricoes().validar(AlocacaoGrade.objects.all())
        except ValidationError as exc:
            raise CommandError('A correção produziria uma grade inválida; nenhuma mudança foi salva. ' + ' '.join(exc.messages)) from exc
        self.stdout.write(self.style.SUCCESS(f'{len(oficiais)} horários oficiais, sem duplicações. Aulas e vínculos preservados.'))
