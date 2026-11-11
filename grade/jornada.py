"""Horários oficiais: aulas consecutivas de 50 minutos e uma hora de almoço."""
from datetime import datetime, timedelta

from django.conf import settings


def jornada():
    quantidade = getattr(settings, 'GRADE_AULAS_POR_TURNO', 4)
    inicio = datetime(2000, 1, 1, 8)
    fim_manha = inicio + timedelta(minutes=50 * quantidade)
    inicio_tarde = fim_manha + timedelta(hours=1)
    return {
        'quantidade': quantidade,
        'inicio_manha': inicio.time(),
        'fim_manha': fim_manha.time(),
        'inicio_tarde': inicio_tarde.time(),
        'fim_tarde': (inicio_tarde + timedelta(minutes=50 * quantidade)).time(),
    }


def horarios_padrao():
    dados = jornada()
    resultado = []
    for turno, inicio in (('Manhã', dados['inicio_manha']), ('Tarde', dados['inicio_tarde'])):
        cursor = datetime.combine(datetime(2000, 1, 1).date(), inicio)
        for indice in range(dados['quantidade']):
            fim = cursor + timedelta(minutes=50)
            resultado.append((f'{turno} — {indice + 1}ª aula', cursor.time(), fim.time()))
            cursor = fim
    return resultado


def durante_almoco(inicio, fim):
    dados = jornada()
    return inicio < dados['inicio_tarde'] and fim > dados['fim_manha']


def obter_horarios_padrao():
    """Reutiliza os intervalos existentes; não cria horários próprios para a demo."""
    from .models import HorarioAula
    horarios = []
    for nome, inicio, fim in horarios_padrao():
        horario = HorarioAula.objects.filter(hora_inicio=inicio, hora_fim=fim).order_by('pk').first()
        if horario is None:
            horario = HorarioAula.objects.create(nome=nome, hora_inicio=inicio, hora_fim=fim)
        horarios.append(horario)
    return horarios
