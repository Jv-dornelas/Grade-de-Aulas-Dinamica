"""Pequenos conjuntos fictícios para reproduzir comportamentos conhecidos."""
from django.core.exceptions import ValidationError
from django.db import transaction

from .gerador import gerar_semana
from .indicadores import resumir_planejamento
from .jornada import obter_horarios_padrao
from .models import (AlocacaoGrade, Curso, Disciplina, MatrizCurricular,
                     MatrizDistancia, Professor, Sala, Turma, Unidade)


ESPERADOS = {
    'completo': (24, 24, 0, 0),
    'falta_professor': (24, 12, 12, 0),
    'deslocamento': (2, 1, 1, 0),
    'disputa_sala': (24, 24, 0, 24),
    'paralelo': (48, 48, 0, 0),
}


@transaction.atomic
def preparar_cenario(nome, inicio):
    if nome not in ESPERADOS:
        raise ValidationError('Cenário desconhecido.')
    if Unidade.objects.exists() or Curso.objects.exists() or Professor.objects.exists() or AlocacaoGrade.objects.exists():
        raise ValidationError('O cenário exige banco sem cadastros. Nenhum dado existente será apagado.')
    horarios = obter_horarios_padrao()
    u = Unidade.objects.create(nome='Unidade Alfa', responsavel='Coordenação fictícia')
    sala = Sala.objects.create(unidade=u, nome='Sala 1')
    curso = Curso.objects.create(nome='Curso de validação', observacoes=f'cenario:{nome}:{inicio.isoformat()}')
    mat = Disciplina.objects.create(nome='Matemática', area='EXATAS')
    MatrizCurricular.objects.create(curso=curso, disciplina=mat, quantidade_semana=1 if nome == 'deslocamento' else 12)
    ana = Professor.objects.create(nome='Ana', unidade_oficial=u, limite_aulas=8)
    ana.disciplinas.add(mat)
    if nome == 'deslocamento':
        v = Unidade.objects.create(nome='Unidade Beta', responsavel='Coordenação fictícia')
        Sala.objects.create(unidade=v, nome='Sala 1')
        ana.unidades_permitidas.add(v)
        MatrizDistancia.objects.create(origem=u, destino=v, tempo_minutos=30)
        MatrizDistancia.objects.create(origem=v, destino=u, tempo_minutos=30)
        for unidade, horario in [(u, horarios[0]), (v, horarios[1])]:
            t = Turma.objects.create(nome='Turma A', unidade=unidade, curso=curso, dias_semana=[0])
            t.horarios.set([horario])
    else:
        port = Disciplina.objects.create(nome='Português', area='HUMANAS')
        MatrizCurricular.objects.create(curso=curso, disciplina=port, quantidade_semana=12)
        if nome != 'falta_professor':
            bruna = Professor.objects.create(nome='Bruna', unidade_oficial=u, limite_aulas=8)
            bruna.disciplinas.add(port)
        Turma.objects.create(nome='Turma A', unidade=u, curso=curso, turno_principal='manha', dia_contraturno=0)
        if nome in ('disputa_sala', 'paralelo'):
            Turma.objects.create(nome='Turma B', unidade=u, curso=curso, turno_principal='manha', dia_contraturno=0)
        if nome == 'paralelo':
            Sala.objects.create(nome='Sala 2', unidade=u)
    return validar_cenario(nome, inicio)


def validar_cenario(nome, inicio):
    from datetime import date, timedelta
    resultado = gerar_semana(inicio)
    aulas = list(AlocacaoGrade.objects.filter(data__range=(inicio, inicio+timedelta(days=6))))
    aulas += [AlocacaoGrade(**{**p, 'data': date.fromisoformat(p['data'])}) for p in resultado['propostas']]
    resumo = resumir_planejamento(aulas)
    esperado = dict(zip(('distribuidas', 'com_docente', 'sem_docente', 'sem_horario'), ESPERADOS[nome]))
    confere = resultado['status'] in ('optimal', 'feasible') and all(resumo[k] == v for k, v in esperado.items())
    return {'cenario': nome, 'semana': inicio.isoformat(), 'confere': confere, 'esperado': esperado,
            'obtido': resumo, 'status': resultado['status'], 'pendencias': resultado['pendencias']}
