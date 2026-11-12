from types import SimpleNamespace as NS
from datetime import date
from django.test import SimpleTestCase
from ..diagnosticos import diagnostico


class DiagnosticosTests(SimpleTestCase):
    def setUp(self):
        self.d = NS(disciplina_id=1, professor_id=None, turma=NS(unidade_id=1))
        self.a = NS(pk=None, professor_id=None, data=date(2026,11,9), horario_id=1)
        self.m = NS(professores={1:NS(limite_aulas=4)}, _disciplinas={1:{1}},
                    permitido=lambda *args: True, disponivel=lambda *args: True,
                    motivo_conflito=lambda *args: None)

    def test_habilitacao_e_unidade_tem_acoes_distintas(self):
        self.m._disciplinas[1] = set()
        self.assertIn('cadastrar a habilitação', diagnostico(self.d,self.m))
        self.m._disciplinas[1] = {1}
        self.m.permitido = lambda *args: False
        self.assertIn('unidade oficial/permitidas', diagnostico(self.d,self.m))

    def test_disponibilidade_e_limite_comprovados(self):
        self.m.disponivel = lambda *args: False
        self.assertIn('restrições por data/horário', diagnostico(self.d,self.m,self.a))
        self.m.disponivel = lambda *args: True
        self.m.professores[1].limite_aulas = 0
        self.assertIn('limite diário atingido', diagnostico(self.d,self.m,self.a))

    def test_trajeto_sobreposicao_e_candidato_livre(self):
        outra=NS(pk=2,professor_id=1,data=self.a.data)
        for motivo,trecho in [('Falta cadastrar o tempo de deslocamento','trajeto ausente'),
                              ('Tempo insuficiente de deslocamento','trajeto insuficiente'),
                              ('Professor possui aulas sobrepostas','sobreposição')]:
            self.m.motivo_conflito=lambda *args,m=motivo:m
            self.assertIn(trecho,diagnostico(self.d,self.m,self.a,[outra]))
        self.m.motivo_conflito=lambda *args:None
        self.assertIn('não foi comprovada falta',diagnostico(self.d,self.m,self.a,[outra]))

    def test_outro_candidato_livre_impede_diagnostico_global_falso(self):
        self.m.professores[2]=NS(limite_aulas=4)
        self.m._disciplinas[2]={1}
        self.m.professores[1].limite_aulas=0
        self.assertIn('não foi comprovada falta',diagnostico(self.d,self.m,self.a))
