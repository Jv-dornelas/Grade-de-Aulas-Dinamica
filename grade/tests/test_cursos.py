from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from ..models import Curso, MatrizCurricular, Turma, Unidade, Disciplina, DemandaAula, Professor, Disponibilidade, AlocacaoGrade
from ..jornada import obter_horarios_padrao
from ..automacao import assinatura_dados
from ..gerador import gerar_semana
from ..restricoes import MotorRestricoes


class CursosTests(TestCase):
    def setUp(self):
        self.unidade=Unidade.objects.create(nome='Unidade',responsavel='Gestor')
        self.curso=Curso.objects.create(nome='Curso real')
        self.disciplina=Disciplina.objects.create(nome='Matemática',area='EXATAS')
        self.item=MatrizCurricular.objects.create(curso=self.curso,disciplina=self.disciplina,quantidade_semana=4)
        self.turma=Turma.objects.create(materias_fixas=False, nome='A',unidade=self.unidade,curso=self.curso,turno_principal='manha',dia_contraturno=2)
        self.horarios=obter_horarios_padrao()
        self.gestor=get_user_model().objects.create_user('gestor',is_staff=True)
        self.client.force_login(self.gestor)
        self.segunda=date(2026,11,2)

    def test_calendario_contraturno_nao_libera_outras_tardes(self):
        slots=[(dia,h) for dia in range(7) for h in self.horarios if self.turma.permite_horario(dia,h)]
        self.assertEqual(len(slots),24)
        self.assertFalse(self.turma.permite_horario(0,self.horarios[4]))
        self.assertTrue(self.turma.permite_horario(2,self.horarios[4]))
        self.turma.turno_principal='tarde'
        self.assertTrue(self.turma.permite_horario(0,self.horarios[4]))
        self.assertFalse(self.turma.permite_horario(0,self.horarios[0]))
        self.assertTrue(self.turma.permite_horario(2,self.horarios[0]))

    def test_sincronizacao_idempotente_e_remocao(self):
        demanda=self.turma.demandas.get()
        self.turma.save()
        self.item.quantidade_semana=3
        self.item.save()
        self.assertEqual(self.turma.demandas.count(),1)
        demanda.refresh_from_db()
        self.assertEqual(demanda.quantidade_semana,3)
        self.item.delete()
        demanda.refresh_from_db()
        self.assertFalse(demanda.ativa)
        MatrizCurricular.objects.create(curso=self.curso,disciplina=self.disciplina,quantidade_semana=4)
        self.assertEqual(self.turma.demandas.get().pk,demanda.pk)
        self.assertTrue(self.turma.demandas.get().ativa)

    def test_gerador_respeita_calendario_e_confirmacao(self):
        professor=Professor.objects.create(nome='Professor real',unidade_oficial=self.unidade,limite_aulas=8)
        professor.disciplinas.add(self.disciplina)
        self.item.quantidade_semana=24
        self.item.save()
        for dia in range(5):
            Disponibilidade.objects.create(professor=professor,data=self.segunda+timedelta(days=dia),disponivel_manha=True,disponivel_tarde=True)
        resultado=gerar_semana(self.segunda)
        self.assertEqual(len(resultado['propostas']),24,resultado)
        self.assertEqual(AlocacaoGrade.objects.count(),0)
        for p in resultado['propostas']:
            self.assertTrue(self.turma.permite_horario(date.fromisoformat(p['data']).weekday(),next(h for h in self.horarios if h.pk==p['horario_id'])))
        from ..automacao import salvar_previa
        import time
        previa={'token':'teste','inicio':self.segunda.isoformat(),'assinatura':assinatura_dados(self.segunda),'criada_em':time.time(),'resultado':resultado,'proximidade':15}
        self.assertEqual(salvar_previa(previa,'teste')[0],24)
        self.assertEqual(len(gerar_semana(self.segunda)['propostas']),0)
        self.item.quantidade_semana=1
        with self.assertRaises(ValidationError):
            self.item.save()
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantidade_semana,24)
        self.assertEqual(AlocacaoGrade.objects.count(),24)
        for campo,modelo in [('professor',professor),('unidade',self.unidade),('curso',self.curso),('turma',self.turma)]:
            r=self.client.get(reverse('grade:consultar'),{'semana':self.segunda.isoformat(),'por':campo,campo:modelo.pk})
            self.assertEqual(r.status_code,200)
            self.assertEqual(sum(len(a) for a in r.context['grupos'].values()),24)

    def test_sem_disponibilidade_nao_inventa_professor(self):
        resultado=gerar_semana(self.segunda)
        self.assertEqual(len(resultado['propostas']),4)
        self.assertTrue(all(p['professor_id'] is None for p in resultado['propostas']))
        self.assertEqual(resultado['resumo']['pendentes'],4)

    def test_permissoes_e_telas(self):
        urls=[reverse('grade:cursos'),reverse('grade:curso_editar',args=[self.curso.pk]),reverse('grade:turmas'),reverse('grade:consultar'),reverse('grade:automacao')]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code,200)
        self.client.force_login(get_user_model().objects.create_user('comum'))
        for url in urls:
            self.assertEqual(self.client.get(url).status_code,302)
            self.assertEqual(self.client.post(url,{'acao':'exemplo'}).status_code,302)

    def test_exemplo_opt_in_sem_sobrescrever(self):
        url=reverse('grade:cursos')
        self.client.get(url)
        self.assertEqual(Curso.objects.count(),1)
        self.assertEqual(self.client.post(url,{'acao':'exemplo'}).status_code,302)
        curso=Curso.objects.get(nome='Preparatório 1')
        self.assertEqual(curso.aulas_semanais,24)
        self.assertEqual(curso.minutos_semanais,1200)
        self.client.post(url,{'acao':'exemplo'})
        self.assertEqual(Curso.objects.count(),2)
        self.assertEqual(Professor.objects.count(),0)
        self.assertEqual(Turma.objects.count(),1)

    def test_previa_desatualiza_com_matriz(self):
        antes=assinatura_dados(self.segunda)
        self.item.quantidade_semana=5
        self.item.save()
        self.assertNotEqual(antes,assinatura_dados(self.segunda))

    def test_demanda_manual_nao_e_sobrescrita(self):
        turma=Turma.objects.create(materias_fixas=False, nome='Legada',unidade=self.unidade)
        demanda=DemandaAula.objects.create(turma=turma,disciplina=self.disciplina,quantidade_semana=2)
        turma.curso=self.curso
        with self.assertRaises(ValidationError):
            turma.save()
        turma.refresh_from_db()
        demanda.refresh_from_db()
        self.assertIsNone(turma.curso)
        self.assertEqual(demanda.quantidade_semana,2)

    def dados_matriz(self, **alteracoes):
        dados = {'nome': self.curso.nome, 'observacoes': 'Editado localmente',
                 'matriz-TOTAL_FORMS': '2', 'matriz-INITIAL_FORMS': '1',
                 'matriz-MIN_NUM_FORMS': '0', 'matriz-MAX_NUM_FORMS': '1000',
                 'matriz-0-id': str(self.item.pk), 'matriz-0-disciplina': str(self.disciplina.pk),
                 'matriz-0-quantidade_semana': '6', 'matriz-1-disciplina': '',
                 'matriz-1-quantidade_semana': ''}
        return {**dados, **alteracoes}

    def test_crud_curso_pela_interface(self):
        url = reverse('grade:curso_editar', args=[self.curso.pk])
        self.assertEqual(self.client.post(url, self.dados_matriz()).status_code, 302)
        self.assertEqual(self.turma.demandas.get().quantidade_semana, 6)
        self.assertEqual(self.client.post(url, {'acao': 'excluir'}).status_code, 200)
        self.assertTrue(Curso.objects.filter(pk=self.curso.pk).exists())
        r = self.client.post(url, self.dados_matriz(**{'matriz-0-DELETE': 'on'}))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(self.turma.demandas.get().ativa)
        vazio = Curso.objects.create(nome='Curso descartável sem turma')
        self.client.post(reverse('grade:curso_editar', args=[vazio.pk]), {'acao': 'excluir'})
        self.assertFalse(Curso.objects.filter(pk=vazio.pk).exists())

    def test_turma_pela_interface_sem_redigitar_demandas(self):
        r = self.client.post(reverse('grade:turmas'), {
            'nome': 'Nova turma real', 'unidade': self.unidade.pk, 'curso': self.curso.pk,
            'dias_semana': ['0','1','2','3','4'], 'turno_principal': 'tarde',
            'dia_contraturno': '4',
        })
        self.assertEqual(r.status_code, 302)
        turma = Turma.objects.get(nome='Nova turma real')
        self.assertEqual(turma.demandas.get().quantidade_semana, 4)
        self.assertTrue(turma.permite_horario(4, self.horarios[0]))
        self.assertFalse(turma.permite_horario(3, self.horarios[0]))

    def test_matriz_invalida_nao_salva_parcialmente(self):
        url = reverse('grade:curso_editar', args=[self.curso.pk])
        dados = self.dados_matriz(**{'nome': 'Não persistir', 'matriz-0-quantidade_semana': '0'})
        self.assertEqual(self.client.post(url, dados).status_code, 200)
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.nome, 'Curso real')
        self.assertEqual(self.turma.demandas.get().quantidade_semana, 4)

    def test_sem_salas_nao_libera_paralelo_por_turma(self):
        outro = Professor.objects.create(nome='Outro', unidade_oficial=self.unidade)
        primeiro = Professor.objects.create(nome='Primeiro', unidade_oficial=self.unidade)
        a = AlocacaoGrade(data=self.segunda, horario=self.horarios[0], professor=primeiro, unidade=self.unidade, turma=self.turma)
        turma = Turma.objects.create(materias_fixas=False, nome='B', unidade=self.unidade)
        b = AlocacaoGrade(data=self.segunda, horario=self.horarios[0], professor=outro, unidade=self.unidade, turma=turma)
        self.assertTrue(MotorRestricoes().conflitam(a,b))
