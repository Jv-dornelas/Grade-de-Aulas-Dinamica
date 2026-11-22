from urllib.parse import urlsplit, parse_qs
from django.test import TestCase
from django.urls import reverse
from .factories import criar_cenario_grade
from ..models import AlocacaoGrade, Unidade


class CorrecaoFluxosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def setUp(self):
        self.client.force_login(self.gestor)

    def test_listar_criar_e_editar_curso_tem_funcoes_distintas(self):
        lista=self.client.get(reverse('grade:cursos'))
        self.assertContains(lista,'Cursos cadastrados')
        self.assertNotContains(lista,'name="nome"')
        novo=self.client.get(reverse('grade:curso_novo'))
        self.assertContains(novo,'Cadastrar curso')
        self.assertContains(novo,'name="nome"')
        self.assertNotContains(novo,'id="lista-cursos"')
        editar=self.client.get(reverse('grade:curso_editar',args=[self.curso.pk]))
        self.assertContains(editar,'Editar curso')

    def test_mudar_para_unidade_preserva_data_e_mostra_aula_no_dia(self):
        url=reverse('grade:exibir_grade')
        r=self.client.get(url,{'data':self.segunda.isoformat(),'por':'professor'})
        unidade=next(m['url'] for m in r.context['modos_distribuicao'] if m['valor']=='unidade')
        self.assertEqual(parse_qs(urlsplit(unidade).query)['data'],[self.segunda.isoformat()])
        atual=self.client.get(unidade)
        self.assertEqual(atual.context['visao'],'dia')
        self.assertContains(atual,'data-origem="salva"')
        self.assertEqual(AlocacaoGrade.objects.count(),1)

    def test_excecao_de_unidade_nao_esconde_turma_na_vista_diaria(self):
        outra=Unidade.objects.create(nome='Local de reposição',responsavel='Gestor')
        # Simula uma alocação manual autorizada para testar somente a projeção.
        AlocacaoGrade.objects.filter(pk=self.fixa.pk).update(unidade=outra)
        r=self.client.get(reverse('grade:exibir_grade'),{'data':self.segunda.isoformat(),'por':'unidade','visao':'dia'})
        grupos=r.context['distribuicao_diaria']
        aulas=[a for g in grupos for l in g['linhas'] for c in l['celulas'] for a in c['aulas']]
        self.assertEqual([a['id'] for a in aulas],[self.fixa.pk])
