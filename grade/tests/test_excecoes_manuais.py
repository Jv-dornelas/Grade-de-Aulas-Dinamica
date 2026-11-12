from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.admin.models import LogEntry
from .factories import criar_cenario_grade
from ..models import AlocacaoGrade
from ..restricoes import MotorRestricoes
from ..gerador import gerar_semana


class ExcecoesManuaisTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def setUp(self):
        self.professor.limite_aulas = 1
        self.professor.save()
        self.client.force_login(self.gestor)
        self.url=reverse('grade:exibir_grade')

    def criar(self, **extra):
        r=self.client.get(self.url,{'nova':'1','data':self.segunda.isoformat()})
        return self.client.post(self.url,{'nova':'1','acao':'salvar_aula','estado':r.context['estado_editor'],
            'data':self.segunda.isoformat(),'horario':self.horarios[1].pk,'unidade':self.unidade.pk,
            'demanda':self.demanda.pk,'professor':self.professor.pk,**extra})

    def test_confirma_justifica_audita_e_marca_no_card(self):
        self.assertEqual(self.criar(confirmar_excecao='on',justificativa_excecao='Reposição autorizada').status_code,302)
        aula=AlocacaoGrade.objects.exclude(pk=self.fixa.pk).get()
        self.assertTrue(aula.eh_excecao_limite_aulas)
        self.assertEqual(aula.autorizado_por,self.gestor)
        self.assertTrue(LogEntry.objects.filter(object_id=str(aula.pk),user=self.gestor).exists())
        r=self.client.get(self.url,{'data':self.segunda.isoformat()})
        self.assertContains(r,'Exceção manual de limite')
        MotorRestricoes().validar(list(AlocacaoGrade.objects.all()))

    def test_sem_confirmacao_ou_justificativa_nao_grava(self):
        self.assertEqual(self.criar().status_code,200)
        self.assertEqual(self.criar(confirmar_excecao='on').status_code,200)
        self.assertEqual(AlocacaoGrade.objects.count(),1)

    def test_excecao_nao_libera_sobreposicao(self):
        r=self.criar(confirmar_excecao='on',justificativa_excecao='Teste',horario=self.horarios[0].pk)
        self.assertEqual(r.status_code,200)
        self.assertEqual(AlocacaoGrade.objects.count(),1)

    def test_excecao_forjada_fora_editor_rejeitada(self):
        a=AlocacaoGrade(data=self.segunda,horario=self.horarios[1],unidade=self.unidade,
            professor=self.professor,turma=self.turma,disciplina=self.disciplina,demanda=self.demanda,
            eh_excecao_limite_aulas=True,motivo_excecao_limite='Forjada',autorizado_por=self.gestor)
        with self.assertRaises(ValidationError):
            a.full_clean()

    def test_gerador_preserva_fixa_manual_mas_nao_cria_excecoes(self):
        self.criar(confirmar_excecao='on',justificativa_excecao='Reposição')
        resultado=gerar_semana(self.segunda)
        self.assertIn(resultado['status'],['optimal','feasible'])
        self.assertFalse(any(p.get('eh_excecao_limite_aulas') for p in resultado['propostas']))
        self.assertFalse(any(p['data']==self.segunda.isoformat() and p.get('professor_id')==self.professor.pk
                             for p in resultado['propostas']))
