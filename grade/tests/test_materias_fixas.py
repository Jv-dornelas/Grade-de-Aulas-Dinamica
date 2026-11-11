from datetime import date, time
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from ..automacao import assinatura_dados
from ..gerador import gerar_semana
from ..horarios_curriculares import assinatura_curriculo, salvar_materias
from ..models import (AlocacaoGrade, DemandaAula, Disciplina, Disponibilidade, DisponibilidadeHorario,
                     HorarioAula, HorarioCurricular, MatrizDistancia, Professor, Turma, Unidade)
from ..restricoes import MotorRestricoes


class MateriasFixasTests(TestCase):
    def setUp(self):
        self.segunda = date(2026,11,9)
        self.unidade = Unidade.objects.create(nome='Centro', responsavel='Gestor')
        self.outra = Unidade.objects.create(nome='Norte', responsavel='Gestor')
        self.matematica = Disciplina.objects.create(nome='Matemática',area='EXATAS')
        self.portugues = Disciplina.objects.create(nome='Português',area='HUMANAS')
        self.h1 = HorarioAula.objects.create(nome='Primeira',hora_inicio=time(8),hora_fim=time(8,50))
        self.h2 = HorarioAula.objects.create(nome='Segunda',hora_inicio=time(8,50),hora_fim=time(9,40))
        self.turma = Turma.objects.create(nome='Preparatório',unidade=self.unidade,dias_semana=[0],materias_fixas=True)
        self.turma.horarios.set([self.h1,self.h2])
        self.dm = DemandaAula.objects.create(turma=self.turma,disciplina=self.matematica,quantidade_semana=1)
        self.dp = DemandaAula.objects.create(turma=self.turma,disciplina=self.portugues,quantidade_semana=1)
        self.fm = HorarioCurricular.objects.create(turma=self.turma,demanda=self.dm,dia_semana=0,horario=self.h1)
        self.fp = HorarioCurricular.objects.create(turma=self.turma,demanda=self.dp,dia_semana=0,horario=self.h2)
        self.professor = Professor.objects.create(nome='Docente',unidade_oficial=self.unidade,limite_aulas=4)
        self.professor.disciplinas.set([self.matematica,self.portugues])
        self.disp = Disponibilidade.objects.create(professor=self.professor,data=self.segunda,disponivel_manha=True)
        self.gestor = get_user_model().objects.create_user('coordenacao-fixa',is_staff=True)
        self.client.force_login(self.gestor)

    def test_padrao_escolhe_so_professores_e_nao_troca_materias(self):
        self.assertTrue(self.turma.materias_fixas)
        resultado=gerar_semana(self.segunda)
        self.assertEqual(resultado['status'],'optimal')
        self.assertEqual({(p['disciplina_id'],p['horario_id']) for p in resultado['propostas']},
                         {(self.matematica.pk,self.h1.pk),(self.portugues.pk,self.h2.pk)})
        self.assertEqual({p['professor_id'] for p in resultado['propostas']},{self.professor.pk})
        self.assertEqual(AlocacaoGrade.objects.count(),0)

    def test_sem_horario_fixo_nao_inventa_distribuicao(self):
        self.fp.delete()
        resultado=gerar_semana(self.segunda)
        self.assertEqual(resultado['status'],'invalid')
        self.assertEqual(resultado['propostas'],[])
        self.assertTrue(any('horários fixos' in p for p in resultado['pendencias']))

    def test_indisponibilidade_nao_move_materia_para_outro_horario(self):
        DisponibilidadeHorario.objects.create(professor=self.professor,data=self.segunda,horario=self.h1,disponivel=False)
        resultado=gerar_semana(self.segunda)
        self.assertEqual(resultado['resumo']['pendentes'],1)
        self.assertEqual([(p['disciplina_id'],p['horario_id']) for p in resultado['propostas']],
                         [(self.portugues.pk,self.h2.pk)])

    def test_nova_alocacao_fora_da_distribuicao_e_recusada(self):
        aula=AlocacaoGrade(data=self.segunda,horario=self.h2,unidade=self.unidade,professor=self.professor,
                           turma=self.turma,disciplina=self.matematica,demanda=self.dm)
        with self.assertRaisesMessage(ValidationError,'horário fixo'):
            aula.full_clean()

    def test_alocacao_historica_fora_do_plano_e_preservada(self):
        historica=AlocacaoGrade.objects.create(data=self.segunda,horario=self.h2,unidade=self.unidade,
            professor=self.professor,turma=self.turma,disciplina=self.matematica,demanda=self.dm)
        MotorRestricoes().validar([historica])
        self.assertTrue(AlocacaoGrade.objects.filter(pk=historica.pk).exists())

    def test_sem_professor_aparece_no_quadro_quatro_modos_e_pdf(self):
        for por in ('curso','turma','professor','unidade'):
            r=self.client.get(reverse('grade:exibir_grade'),{'data':self.segunda.isoformat(),'por':por})
            self.assertEqual(r.context['total_sem_professor'],2)
            self.assertEqual(r.context['total_salvas'],0)
            self.assertContains(r,'Definir professor')
            self.assertContains(r,'Sem professor')
        r=self.client.get(reverse('grade:grade_pdf'),{'data':self.segunda.isoformat()})
        self.assertEqual(r.status_code,200)
        self.assertTrue(b''.join(r.streaming_content).startswith(b'%PDF-'))

    def test_plano_desatualiza_previa(self):
        antes=assinatura_dados(self.segunda)
        self.fp.delete()
        self.assertNotEqual(antes,assinatura_dados(self.segunda))

    def test_plano_invalido_reverte_a_distribuicao_anterior(self):
        with self.assertRaises(ValidationError):
            salvar_materias(self.turma,[{'demanda':self.dm,'dia_semana':0,'horario':self.h1},
                                       {'demanda':self.dp,'dia_semana':0,'horario':self.h1}])
        self.assertEqual(self.turma.distribuicao_curricular.count(),2)

    def test_editor_de_proposta_so_permite_mudar_professor(self):
        self.client.post(reverse('grade:exibir_grade'),{'acao':'gerar','semana':self.segunda.isoformat(),'proximidade':15})
        r=self.client.get(reverse('grade:exibir_grade'),{'proposta':0})
        for campo in ('data','horario','unidade','demanda'):
            self.assertTrue(r.context['aula_form'].fields[campo].disabled)
        self.assertFalse(r.context['aula_form'].fields['professor'].disabled)

    def test_ficha_da_unidade_salva_ida_volta_e_motor_consulta(self):
        antes=assinatura_dados(self.segunda)
        r=self.client.post(reverse('grade:editar_unidade',args=[self.unidade.pk]),{
            'nome':self.unidade.nome,'responsavel':'Gestor','trajetos-TOTAL_FORMS':1,
            'trajetos-INITIAL_FORMS':1,'trajetos-0-destino':self.outra.pk,
            'trajetos-0-ida':20,'trajetos-0-volta':35,'trajetos-0-km_ida':'12.50','trajetos-0-km_volta':'13.00'})
        self.assertEqual(r.status_code,200)
        self.assertTrue(r.context['sucesso'])
        motor=MotorRestricoes()
        self.assertEqual(motor.tempo(self.unidade.pk,self.outra.pk),20)
        self.assertEqual(motor.tempo(self.outra.pk,self.unidade.pk),35)
        self.assertNotEqual(antes,assinatura_dados(self.segunda))
        a=AlocacaoGrade(data=self.segunda,horario=self.h1,professor=self.professor,unidade=self.unidade)
        b=AlocacaoGrade(data=self.segunda,horario=self.h2,professor=self.professor,unidade=self.outra)
        self.assertTrue(motor.conflitam(a,b))

    def test_km_sem_tempo_nao_gera_tempo_estimado(self):
        r=self.client.post(reverse('grade:editar_unidade',args=[self.unidade.pk]),{
            'nome':self.unidade.nome,'responsavel':'Gestor','trajetos-TOTAL_FORMS':1,
            'trajetos-INITIAL_FORMS':1,'trajetos-0-destino':self.outra.pk,'trajetos-0-km_ida':'10.00'})
        self.assertFalse(r.context['sucesso'])
        self.assertEqual(MatrizDistancia.objects.count(),0)

    def test_acesso_a_fichas_e_plano_exige_coordenacao(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('grade:materias_turma',args=[self.turma.pk])).status_code,302)
        self.assertEqual(self.client.get(reverse('grade:editar_unidade',args=[self.unidade.pk])).status_code,302)

    def test_editar_distribuicao_pelo_formulario_inclusive_trocar_horarios(self):
        url=reverse('grade:materias_turma',args=[self.turma.pk])
        r=self.client.get(url)
        dados={'assinatura':r.context['assinatura'],'materias-TOTAL_FORMS':3,'materias-INITIAL_FORMS':2,
            'materias-0-dia_semana':0,'materias-0-horario':self.h2.pk,'materias-0-demanda':self.dm.pk,
            'materias-1-dia_semana':0,'materias-1-horario':self.h1.pk,'materias-1-demanda':self.dp.pk,
            'materias-2-dia_semana':'','materias-2-horario':'','materias-2-demanda':''}
        self.assertEqual(self.client.post(url,dados).status_code,302)
        self.assertEqual(self.turma.distribuicao_curricular.get(demanda=self.dm).horario_id,self.h2.pk)
        resposta=self.client.post(url,dados)
        self.assertIn('mudou',resposta.context['erro'])

    def test_trajeto_para_propria_unidade_reverte_edicao(self):
        r=self.client.post(reverse('grade:editar_unidade',args=[self.unidade.pk]),{
            'nome':'Não salvar','responsavel':'Gestor','trajetos-TOTAL_FORMS':1,
            'trajetos-INITIAL_FORMS':0,'trajetos-0-destino':self.unidade.pk,'trajetos-0-ida':20})
        self.assertFalse(r.context['sucesso'])
        self.unidade.refresh_from_db()
        self.assertEqual(self.unidade.nome,'Centro')
        self.assertEqual(MatrizDistancia.objects.count(),0)

    def test_modo_flexivel_pode_reorganizar_materia_sem_apagar_plano_opcional(self):
        self.turma.materias_fixas=False;self.turma.save()
        self.dp.ativa=False;self.dp.save()
        DisponibilidadeHorario.objects.create(professor=self.professor,data=self.segunda,horario=self.h1,disponivel=False)
        resultado=gerar_semana(self.segunda)
        self.assertEqual([(p['disciplina_id'],p['horario_id']) for p in resultado['propostas']],
                         [(self.matematica.pk,self.h2.pk)])
        self.assertEqual(self.turma.distribuicao_curricular.count(),2)
