"""Cenário compartilhado dos testes de integração da grade."""
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from ..models import (AlocacaoGrade, Curso, Disciplina, Disponibilidade, MatrizCurricular, Professor, Turma, Unidade)
from ..jornada import obter_horarios_padrao


def criar_cenario_grade(cls):
    cls.segunda = date(2026, 11, 9)
    cls.unidade = Unidade.objects.create(nome='Unidade Horizonte · QA', responsavel='Coordenação')
    cls.curso = Curso.objects.create(nome='Preparatório · QA')
    cls.disciplina = Disciplina.objects.create(nome='Matemática', area='EXATAS')
    cls.item = MatrizCurricular.objects.create(curso=cls.curso, disciplina=cls.disciplina, quantidade_semana=24)
    cls.turma = Turma.objects.create(materias_fixas=False, nome='Preparatório A', unidade=cls.unidade, curso=cls.curso,
                                     turno_principal='manha', dia_contraturno=2)
    cls.horarios = obter_horarios_padrao()
    cls.professor = Professor.objects.create(nome='Ana Ribeiro · QA', unidade_oficial=cls.unidade, limite_aulas=8)
    cls.professor.disciplinas.add(cls.disciplina)
    for d in range(5):
        Disponibilidade.objects.create(professor=cls.professor, data=cls.segunda + timedelta(days=d),
                                        disponivel_manha=True, disponivel_tarde=True)
    cls.demanda = cls.turma.demandas.get()
    cls.fixa = AlocacaoGrade.objects.create(data=cls.segunda, horario=cls.horarios[0],
        unidade=cls.unidade, professor=cls.professor, turma=cls.turma,
        disciplina=cls.disciplina, demanda=cls.demanda)
    cls.gestor = get_user_model().objects.create_user('qa-grade-integrada', is_staff=True)
