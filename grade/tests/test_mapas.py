from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from ..mapas import consultar_trajeto, aplicar_trajeto
from ..models import CacheConsultaMapas, MatrizDistancia, Unidade
from ..restricoes import MotorRestricoes


class ConsultaMapasTests(TestCase):
    def setUp(self):
        self.a=Unidade.objects.create(nome='Centro',responsavel='Coordenação',endereco='Rua Central, 10',cidade='Cidade SP')
        self.b=Unidade.objects.create(nome='Norte',responsavel='Coordenação',endereco='Rua Norte, 20',cidade='Cidade SP')
        self.gestor=get_user_model().objects.create_user('gestor-mapas',is_staff=True)
        self.client.force_login(self.gestor)
        self.url=reverse('grade:editar_unidade',args=[self.a.pk])
        self.respostas=[
            [{'lat':'-23.5','lon':'-46.5','display_name':'Rua Central, 10, Cidade, SP','address':{'city':'Cidade SP'}}],
            [{'lat':'-23.6','lon':'-46.6','display_name':'Rua Norte, 20, Cidade, SP','address':{'city':'Cidade SP'}}],
            {'code':'Ok','routes':[{'distance':12340,'duration':601}]},
            {'code':'Ok','routes':[{'distance':14000,'duration':900}]},
        ]

    def consultar(self):
        with patch('grade.mapas.requisitar_json',side_effect=deepcopy(self.respostas)):
            return consultar_trajeto(self.a,self.b)

    def test_consulta_bidirecional_tem_cache_e_nao_aplica_sem_revisao(self):
        with patch('grade.mapas.requisitar_json',side_effect=deepcopy(self.respostas)) as http:
            resultado=consultar_trajeto(self.a,self.b)
            self.assertEqual(http.call_count,4)
            repetido=consultar_trajeto(self.a,self.b)
            self.assertEqual(http.call_count,4)
        self.assertEqual(resultado['ida'],{'km':'12.34','minutos':11})
        self.assertEqual(resultado['volta'],{'km':'14.00','minutos':15})
        self.assertEqual(repetido['ida'],resultado['ida'])
        self.assertEqual(MatrizDistancia.objects.count(),0)
        self.assertEqual(CacheConsultaMapas.objects.count(),4)

    def test_aplicar_usando_sessao_ignora_valores_adulterados(self):
        with patch('grade.mapas.requisitar_json',side_effect=deepcopy(self.respostas)):
            r=self.client.post(self.url,{'acao':'consultar_trajeto','destino':self.b.pk})
        self.assertContains(r,'Confira a localização retornada')
        self.assertEqual(MatrizDistancia.objects.count(),0)
        token=self.client.session['trajeto_previa']['token']
        r=self.client.post(self.url,{'acao':'aplicar_trajeto','token':token,'conferido':'on','minutos':0,'km':0})
        self.assertEqual(r.status_code,200)
        self.assertEqual(MatrizDistancia.objects.get(origem=self.a,destino=self.b).tempo_minutos,11)
        self.assertEqual(MatrizDistancia.objects.get(origem=self.b,destino=self.a).tempo_minutos,15)
        self.assertEqual(MatrizDistancia.objects.get(origem=self.a,destino=self.b).distancia_km,Decimal('12.34'))
        self.assertNotIn('trajeto_previa',self.client.session)

    def test_nao_aplica_token_invalido_ou_sem_conferencia(self):
        previa=self.consultar();previa['token']='segredo'
        session=self.client.session;session['trajeto_previa']=previa;session.save()
        for dados in ({'token':'errado','conferido':'on'},{'token':'segredo'}):
            r=self.client.post(self.url,{'acao':'aplicar_trajeto',**dados})
            self.assertTrue(r.context['erro'])
        self.assertEqual(MatrizDistancia.objects.count(),0)

    def test_endereco_alterado_invalida_consulta_e_rota_aplicada(self):
        previa=self.consultar()
        aplicar_trajeto(previa)
        self.assertEqual(MotorRestricoes().tempo(self.a.pk,self.b.pk),11)
        self.a.endereco='Outro endereço, 100';self.a.save()
        self.assertIsNone(MotorRestricoes().tempo(self.a.pk,self.b.pk))
        with self.assertRaisesMessage(ValidationError,'endereços mudaram'):
            aplicar_trajeto(previa)

    def test_edicao_manual_posterior_nao_e_sobrescrita_por_consulta_antiga(self):
        previa=self.consultar()
        MatrizDistancia.objects.create(origem=self.a,destino=self.b,tempo_minutos=40)
        with self.assertRaisesMessage(ValidationError,'editados após'):
            aplicar_trajeto(previa)
        self.assertEqual(MatrizDistancia.objects.get().tempo_minutos,40)

    def test_endereco_ausente_ou_ambiguo_nao_inventa_distancia(self):
        self.a.endereco=''
        with patch('grade.mapas.requisitar_json') as http:
            with self.assertRaises(ValidationError): consultar_trajeto(self.a,self.b)
        http.assert_not_called()
        self.a.refresh_from_db()
        with patch('grade.mapas.requisitar_json',return_value=self.respostas[0]+self.respostas[1]):
            with self.assertRaisesMessage(ValidationError,'ambíguo'): consultar_trajeto(self.a,self.b)
        self.assertEqual(MatrizDistancia.objects.count(),0)

    def test_falha_externa_preserva_trajeto_existente(self):
        MatrizDistancia.objects.create(origem=self.a,destino=self.b,tempo_minutos=30)
        with patch('grade.mapas.requisitar_json',side_effect=ValidationError('Serviço indisponível')):
            r=self.client.post(self.url,{'acao':'consultar_trajeto','destino':self.b.pk})
        self.assertIn('indisponível',r.context['erro'])
        self.assertEqual(MatrizDistancia.objects.get().tempo_minutos,30)

    def test_recusa_rota_sem_caminho_e_resposta_invalida(self):
        for resposta in ({'code':'NoRoute'}, {'code':'Ok','routes':[{'distance':-1,'duration':50}]}):
            CacheConsultaMapas.objects.all().delete()
            with patch('grade.mapas.requisitar_json',side_effect=deepcopy(self.respostas[:2])+[resposta]):
                with self.assertRaises(ValidationError): consultar_trajeto(self.a,self.b)
        self.assertEqual(MatrizDistancia.objects.count(),0)

    def test_apenas_coordenacao_pode_consultar(self):
        self.client.logout()
        with patch('grade.mapas.requisitar_json') as http:
            self.assertEqual(self.client.post(self.url,{'acao':'consultar_trajeto','destino':self.b.pk}).status_code,302)
        http.assert_not_called()

    def test_resultado_em_outro_municipio_nao_vira_trajeto(self):
        resposta=deepcopy(self.respostas[0])
        resposta[0]['address']['city']='Outra cidade'
        with patch('grade.mapas.requisitar_json',return_value=resposta) as http:
            with self.assertRaisesMessage(ValidationError,'município cadastrado'):
                consultar_trajeto(self.a,self.b)
        self.assertEqual(http.call_count,1)
        self.assertEqual(MatrizDistancia.objects.count(),0)

    def test_pois_do_mesmo_predio_nao_sao_confundidos_com_enderecos_distintos(self):
        a={'city':'Cidade SP','road':'Rua Central','house_number':'10','postcode':'01000-000'}
        respostas=[{'lat':'-23.5000','lon':'-46.5000','display_name':'Edifício','address':a},
                   {'lat':'-23.5001','lon':'-46.5001','display_name':'Biblioteca','address':{**a,'amenity':'Biblioteca'}}]
        self.a.cep='01000-000'
        from ..mapas import localizar
        with patch('grade.mapas.requisitar_json',return_value=respostas):
            self.assertEqual(localizar(self.a)['rotulo'],'Biblioteca')
