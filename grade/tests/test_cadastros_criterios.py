from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .factories import criar_cenario_grade
from ..automacao import GeracaoForm, assinatura_dados
from ..models import (Professor, Unidade, ConfiguracaoAutomacao,
                      DisponibilidadeHorario)
from ..parametros import obter_proximidade
from ..restricoes import MotorRestricoes


class CadastrosCriteriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def setUp(self):
        self.client.force_login(self.gestor)

    def dados_professor(self, **extras):
        return {'nome':'Carla QA','telefone':'11999999999','email':'carla@example.com',
                'disciplinas':[self.disciplina.pk],'meio_de_transporte':'PUBLICO','limite_aulas':6,
                'unidade_oficial':self.unidade.pk,'parente_vinculado':self.professor.pk,
                'observacao':'Informação de consulta', **extras}

    def test_todos_os_campos_editaveis_de_professor_têm_input(self):
        campos={f.name for f in Professor._meta.fields if f.name != 'id'} | {f.name for f in Professor._meta.many_to_many}
        for rota,args in [('cadastrar_professor',[]),('editar_professor',[self.professor.pk])]:
            r=self.client.get(reverse('grade:'+rota,args=args))
            for campo in campos:
                self.assertContains(r, f'name="{campo}"')

    def test_cadastro_persiste_campos_vinculos_e_conta_mobile(self):
        outra=Unidade.objects.create(nome='Outra',responsavel='Gestor')
        usuario=get_user_model().objects.create_user('mobile-novo')
        r=self.client.post(reverse('grade:cadastrar_professor'),self.dados_professor(
            unidades_permitidas=[outra.pk],usuario=usuario.pk))
        self.assertEqual(r.status_code,302)
        p=Professor.objects.get(nome='Carla QA')
        self.assertEqual(p.usuario_id,usuario.pk)
        self.assertEqual(p.parente_vinculado_id,self.professor.pk)
        self.assertEqual(p.limite_aulas,6)
        self.assertEqual(p.meio_de_transporte,'PUBLICO')
        self.assertEqual(list(p.disciplinas.values_list('pk',flat=True)),[self.disciplina.pk])
        self.assertTrue(MotorRestricoes().permitido(p.pk,outra.pk))

    def test_vinculo_usuario_nao_pode_apontar_para_gestor(self):
        r=self.client.post(reverse('grade:cadastrar_professor'),self.dados_professor(usuario=self.gestor.pk))
        self.assertEqual(r.status_code,200)
        self.assertIn('usuario',r.context['form_professor'].errors)
        self.assertFalse(Professor.objects.filter(nome='Carla QA').exists())

    def test_edicao_incompativel_com_aula_salva_faz_rollback(self):
        url=reverse('grade:editar_professor',args=[self.professor.pk])
        r=self.client.get(url);estado=r.context['form_professor']['estado'].value()
        dados=self.dados_professor(nome=self.professor.nome,parente_vinculado='',estado=estado,limite_aulas=0)
        r=self.client.post(url,dados)
        self.assertEqual(r.status_code,200)
        self.assertTrue(r.context['form_professor'].non_field_errors())
        self.professor.refresh_from_db();self.assertEqual(self.professor.limite_aulas,8)

    def test_estado_concorrente_da_ficha_e_rejeitado(self):
        url=reverse('grade:editar_professor',args=[self.professor.pk])
        r=self.client.get(url);estado=r.context['form_professor']['estado'].value()
        Professor.objects.filter(pk=self.professor.pk).update(observacao='Outra edição')
        r=self.client.post(url,self.dados_professor(parente_vinculado='',estado=estado))
        self.assertEqual(r.status_code,200)
        self.professor.refresh_from_db();self.assertEqual(self.professor.observacao,'Outra edição')

    def test_parametro_tem_input_persiste_e_e_consumido_no_servidor(self):
        antes=assinatura_dados(self.segunda)
        r=self.client.get(reverse('grade:configuracoes'))
        self.assertContains(r,'name="proximidade_parentesco_minutos"')
        self.client.post(reverse('grade:configuracoes'),{'proximidade_parentesco_minutos':30})
        self.assertEqual(obter_proximidade(),30)
        self.assertNotEqual(assinatura_dados(self.segunda),antes)
        form=GeracaoForm({'semana':self.segunda,'proximidade':200})
        self.assertTrue(form.is_valid());self.assertEqual(form.cleaned_data['proximidade'],30)
        self.client.post(reverse('grade:configuracoes'),{'proximidade_parentesco_minutos':241})
        self.assertEqual(obter_proximidade(),30)

    def test_motor_usa_proximidade_cadastrada_para_o_vinculo_familiar(self):
        from ..models import MatrizDistancia, AlocacaoGrade
        outra=Unidade.objects.create(nome='Perto',responsavel='Gestor')
        p=Professor.objects.create(nome='Familiar',unidade_oficial=outra,parente_vinculado=self.professor)
        for origem,destino in [(self.unidade,outra),(outra,self.unidade)]:
            MatrizDistancia.objects.create(origem=origem,destino=destino,tempo_minutos=20)
        aulas=[self.fixa,AlocacaoGrade(data=self.segunda,horario=self.horarios[1],unidade=outra,professor=p)]
        self.assertTrue(MotorRestricoes().avisos_parentesco(aulas))
        self.client.post(reverse('grade:configuracoes'),{'proximidade_parentesco_minutos':30})
        self.assertEqual(MotorRestricoes().avisos_parentesco(aulas),[])

    def test_restricao_por_horario_persiste_e_retorna_ao_padrao(self):
        data=self.segunda+timedelta(days=7)
        r=self.client.post(reverse('grade:restricoes_horario'),{'professor':self.professor.pk,
            'data':data,'horario':self.horarios[0].pk})
        self.assertEqual(r.status_code,302)
        registro=DisponibilidadeHorario.objects.get()
        self.assertFalse(MotorRestricoes().disponivel(self.professor.pk,data,self.horarios[0].pk))
        self.client.post(reverse('grade:restricao_horario_editar',args=[registro.pk]),{'acao':'remover'})
        self.assertTrue(MotorRestricoes().disponivel(self.professor.pk,data,self.horarios[0].pk))

    def test_restricao_nao_pode_invalidar_aula_existente(self):
        r=self.client.post(reverse('grade:restricoes_horario'),{'professor':self.professor.pk,
            'data':self.segunda,'horario':self.horarios[0].pk})
        self.assertEqual(r.status_code,200)
        self.assertIsNotNone(r.context['erro'])
        self.assertFalse(DisponibilidadeHorario.objects.exists())

    def test_novas_telas_exigem_permissao_e_csrf(self):
        rotas=['configuracoes','restricoes_horario']
        c=Client(enforce_csrf_checks=True);c.force_login(self.gestor)
        for rota in rotas:
            self.assertEqual(c.post(reverse('grade:'+rota),{}).status_code,403)
        self.client.force_login(get_user_model().objects.create_user('sem-gestao'))
        for rota in rotas:
            self.assertEqual(self.client.get(reverse('grade:'+rota)).status_code,302)
