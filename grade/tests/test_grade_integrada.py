"""Fluxo real pela página principal, sem escrever no banco de trabalho."""
from copy import deepcopy
from datetime import date, timedelta
from html.parser import HTMLParser
import os
from pathlib import Path
import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..automacao import CHAVE_PREVIA
from ..jornada import obter_horarios_padrao
from ..models import (AlocacaoGrade, Curso, Disciplina, Disponibilidade,
                     MatrizCurricular, Professor, Turma, Unidade)


class CamposGrade(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.campo = None
        self.selecionados = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        dados = dict(attrs)
        if tag == 'select':
            self.campo = dados.get('name')
        if tag == 'option' and self.campo and 'selected' in dados:
            self.selecionados[self.campo] = dados.get('value')

    def handle_endtag(self, tag):
        if tag == 'select':
            self.campo = None


from .factories import criar_cenario_grade


class GradeIntegradaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def setUp(self):
        self.url = reverse('grade:exibir_grade')
        self.client.force_login(self.gestor)

    def gerar(self):
        response = self.client.post(self.url, {'acao': 'gerar', 'semana': self.segunda.isoformat(),
            'data_grade': self.segunda.isoformat(), 'por': 'unidade', 'visao': 'semana', 'proximidade': '0'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'grade/grade_tabela.html')
        self.assertFalse(response.context['erro'])
        self.assertEqual(response.context['total_propostas'], 23)
        self.assertEqual(response.context['total_visivel'], 24)
        return response

    def confirmar(self, **extra):
        return self.client.post(self.url, {'acao': 'salvar',
            'token': self.client.session[CHAVE_PREVIA]['token'], **extra})

    @staticmethod
    def aulas(response):
        return [a for g in response.context['distribuicao'] for l in g['linhas'] for c in l['celulas'] for a in c]

    def test_get_principal_nao_gera_nem_navega_para_areas_externas(self):
        with patch('grade.automacao.gerar_semana') as motor:
            response = self.client.get(self.url, {'data': self.segunda.isoformat()})
        motor.assert_not_called()
        self.assertContains(response, 'form="gerar-integrado"')
        self.assertNotContains(response, 'href="/automacao/')
        self.assertNotContains(response, 'href="/consultar/')
        self.assertEqual(AlocacaoGrade.objects.count(), 1)
        self.assertNotIn(CHAVE_PREVIA, self.client.session)
        self.assertNotContains(response, 'class="home-operacao"')
        self.assertNotContains(response, 'Consultar trajetos das unidades')
        self.assertNotContains(response, 'Distâncias pelos endereços')
        self.assertNotContains(response, 'proximidade-integrada')
        self.assertContains(response, 'Grade gravada, aguardando aprovação.')
        self.assertContains(response, 'id="aprovar-grade-btn"')

    def test_limite_de_proximidade_vem_da_administracao(self):
        with self.settings(GRADE_PROXIMIDADE_PARENTESCO_MINUTOS=25):
            self.gerar()
        self.assertEqual(self.client.session[CHAVE_PREVIA]['proximidade'],25)

    def test_gerar_preenche_campos_e_mostra_toda_semana_sem_gravar(self):
        response = self.gerar()
        self.assertEqual(AlocacaoGrade.objects.count(), 1)
        self.assertEqual(len(response.context['dias_distribuicao']), 7)
        self.assertEqual([d.weekday() for d in response.context['dias_distribuicao']], [6, 0, 1, 2, 3, 4, 5])
        self.assertEqual(response.context['fim_distribuicao'], self.segunda + timedelta(days=6))
        self.assertEqual(sum(a['proposta'] for a in self.aulas(response)), 23)
        self.assertEqual({a['data'] for a in self.aulas(response)}, {self.segunda + timedelta(days=d) for d in range(5)})
        self.assertEqual(len(self.aulas(response)), 24)
        self.assertContains(response, 'Ajustar</a>', count=23)
        self.assertNotContains(response, 'id="gradeForm"')
        self.assertContains(response, 'Aprovar e gravar prévia · 23 aulas')
        self.assertContains(response, 'form="aprovar-integrado"')
        self.assertContains(response, 'type="hidden" name="proximidade"')

    def test_quatro_modos_preservam_mesmos_ids_e_proposta(self):
        self.gerar()
        previa = deepcopy(self.client.session[CHAVE_PREVIA])
        for por in ('curso', 'turma', 'professor', 'unidade'):
            with self.subTest(por=por):
                response = self.client.get(self.url, {'data': self.segunda.isoformat(), 'por': por})
                aulas = self.aulas(response)
                self.assertEqual(response.context['por'], por)
                self.assertEqual(len(aulas), 24)
                self.assertEqual({a['id'] for a in aulas if not a['proposta']}, {self.fixa.pk})
                self.assertEqual(sum(a['proposta'] for a in aulas), 23)
                self.assertContains(response, self.curso.nome)
                self.assertContains(response, self.turma.nome)
                self.assertContains(response, self.professor.nome)
                self.assertContains(response, self.unidade.nome)
                self.assertEqual(self.client.session[CHAVE_PREVIA], previa)
                self.assertEqual(AlocacaoGrade.objects.count(), 1)
                if os.environ.get('GRADE_QA_DIR'):
                    self.snapshot(response, por)

    def snapshot(self, response, por):
        """Artefatos opcionais só com dados fictícios do banco temporário dos testes."""
        pasta = Path(os.environ['GRADE_QA_DIR'])
        pasta.mkdir(parents=True, exist_ok=True)
        html = response.content.decode()
        # Autossuficiente para a inspeção visual offline, sem sessão/cookie ou serviço auxiliar.
        html = re.sub(r'<link rel="stylesheet" href="/static/grade/distribuicao.css[^\"]*">',
                      lambda _: '<style>' + Path('grade/static/grade/distribuicao.css').read_text() + '</style>', html)
        html = re.sub(r'<script src="/static/grade/distribuicao.js[^\"]*"></script>',
                      lambda _: '<script>' + Path('grade/static/grade/distribuicao.js').read_text() + '</script>', html)
        (pasta / f'grade-{por}.html').write_text(html, encoding='utf-8')

    def test_navegar_dias_e_semanas_nao_perde_previa(self):
        self.gerar()
        previa = deepcopy(self.client.session[CHAVE_PREVIA])
        quarta = self.segunda + timedelta(days=2)
        r = self.client.get(self.url, {'data': quarta.isoformat(), 'por': 'turma'})
        self.assertEqual(sum(a['data'] == quarta for a in self.aulas(r)), 8)
        self.assertNotContains(r, 'id="gradeForm"')
        r = self.client.get(self.url, {'data': (quarta + timedelta(days=7)).isoformat(), 'por': 'curso'})
        self.assertFalse(r.context['previa_visivel'])
        self.assertEqual(r.context['total_propostas'], 0)
        self.assertContains(r, 'Voltar à semana da proposta')
        self.assertEqual(self.client.session[CHAVE_PREVIA], previa)
        self.assertEqual(self.client.get(r.context['url_semana_previa']).context['total_propostas'], 23)

    def test_filtrar_nao_descarta_aulas_nem_limita_confirmacao(self):
        self.gerar()
        curso = Curso.objects.create(nome='Outro curso sem aulas')
        # Cadastro novo torna a prévia antiga desatualizada; gerar outra antes de filtrar.
        self.gerar()
        r = self.client.get(self.url, {'data': self.segunda.isoformat(), 'por': 'curso', 'entidade': curso.pk})
        self.assertEqual(r.context['total_visivel'], 0)
        self.assertEqual(r.context['total_sem_filtro'], 24)
        self.assertContains(r, 'inclusive fora do filtro atual')
        self.assertIn(CHAVE_PREVIA, self.client.session)
        r = self.confirmar(por='curso', entidade=str(curso.pk))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(self.url + '?'))
        self.assertEqual(AlocacaoGrade.objects.count(), 24)

    def test_confirmar_principal_preserva_fixas_e_impede_duplicacao(self):
        estado = AlocacaoGrade.objects.values().get(pk=self.fixa.pk)
        self.gerar()
        token = self.client.session[CHAVE_PREVIA]['token']
        r = self.confirmar(por='professor')
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('/automacao/', r.url)
        r = self.client.get(r.url)
        self.assertEqual(r.context['total_salvas'], 24)
        self.assertEqual(r.context['total_propostas'], 0)
        self.assertNotIn(CHAVE_PREVIA, self.client.session)
        self.assertEqual(AlocacaoGrade.objects.values().get(pk=self.fixa.pk), estado)
        r = self.client.post(self.url, {'acao': 'salvar', 'token': token})
        self.assertTrue(r.context['erro'])
        self.assertEqual(AlocacaoGrade.objects.count(), 24)

    def test_manual_durante_previa_recusado_no_servidor(self):
        self.gerar()
        r = self.client.post(self.url, {'data_grade': self.segunda.isoformat(),
            f'alocacao_{self.horarios[1].pk}_{self.unidade.pk}': self.professor.pk})
        self.assertIn('prévia pendente', r.context['erro_negocio'])
        self.assertEqual(AlocacaoGrade.objects.count(), 1)
        self.assertEqual(r.context['total_propostas'], 23)

    def test_descartar_restaura_campos_sem_apagar_fixa(self):
        self.gerar()
        r = self.client.post(self.url, {'acao': 'descartar', 'data_grade': self.segunda.isoformat()}, follow=True)
        self.assertNotIn(CHAVE_PREVIA, self.client.session)
        self.assertEqual(r.context['total_propostas'], 0)
        campos = CamposGrade(r.content.decode()).selecionados
        self.assertNotIn(f'alocacao_{self.horarios[1].pk}_{self.unidade.pk}', campos)
        self.assertNotContains(r, '<fieldset disabled>')
        self.assertEqual(AlocacaoGrade.objects.count(), 1)

    def test_edicao_manual_continua_funcional_sem_previa(self):
        dados = {'data_grade': self.segunda.isoformat(), f'disp_manha_{self.professor.pk}': 'on',
                 f'disp_tarde_{self.professor.pk}': 'on',
                 f'alocacao_{self.horarios[0].pk}_{self.unidade.pk}': self.professor.pk,
                 f'alocacao_{self.horarios[1].pk}_{self.unidade.pk}': self.professor.pk}
        r = self.client.post(self.url, dados)
        self.assertFalse(r.context['erro_negocio'])
        self.assertTrue(r.context['sucesso'])
        self.assertEqual(AlocacaoGrade.objects.count(), 2)
        self.assertEqual(r.context['total_salvas'], 2)

    def test_stale_detection_na_mesma_pagina(self):
        self.gerar()
        self.curso.observacoes = 'Matriz revisada pela coordenação'
        self.curso.save()
        r = self.client.get(self.url)
        self.assertTrue(r.context['previa_desatualizada'])
        self.assertFalse(r.context['pode_salvar'])
        r = self.confirmar()
        self.assertIn('alterados', r.context['erro'])
        self.assertEqual(AlocacaoGrade.objects.count(), 1)

    def test_inviavel_exibe_pendencias_e_exige_aceite_parcial(self):
        Disponibilidade.objects.filter(data=self.segunda + timedelta(days=2)).update(disponivel_tarde=False)
        r = self.client.post(self.url, {'acao': 'gerar', 'semana': self.segunda.isoformat(), 'proximidade': '15'})
        self.assertEqual(r.context['resultado']['resumo']['pendentes'], 4)
        self.assertContains(r, 'Pendências da distribuição')
        self.assertContains(r, 'aceito salvar a proposta parcial')
        self.assertTrue(self.confirmar().context['erro'])
        self.assertEqual(AlocacaoGrade.objects.count(), 1)
        self.assertEqual(self.confirmar(aceitar_parcial='on').status_code, 302)
        self.assertEqual(AlocacaoGrade.objects.count(), 24)
        self.assertEqual(AlocacaoGrade.objects.filter(professor=None).count(), 4)

    def test_legado_nao_fica_invisivel_em_curso_ou_turma(self):
        legado = AlocacaoGrade.objects.create(data=self.segunda, horario=self.horarios[1],
            unidade=self.unidade, professor=self.professor)
        for por in ('curso', 'turma'):
            r = self.client.get(self.url, {'data': self.segunda.isoformat(), 'por': por})
            self.assertEqual({a['id'] for a in self.aulas(r)}, {self.fixa.pk, legado.pk})
            self.assertContains(r, 'Sem vínculo / legado')

    def test_curso_separa_turmas_das_unidades_sem_ocultar_aulas(self):
        unidade = Unidade.objects.create(nome='Segunda unidade QA', responsavel='Gestor')
        turma = Turma.objects.create(materias_fixas=False, nome='Turma B', curso=self.curso, unidade=unidade)
        professor = Professor.objects.create(nome='Outro professor', unidade_oficial=unidade)
        outra = AlocacaoGrade.objects.create(data=self.segunda, horario=self.horarios[0],
            unidade=unidade, professor=professor, turma=turma, disciplina=self.disciplina, demanda=turma.demandas.get())
        r = self.client.get(self.url, {'data': self.segunda.isoformat(), 'por': 'curso'})
        self.assertEqual({a['id'] for a in self.aulas(r)}, {self.fixa.pk, outra.pk})
        self.assertEqual(len(r.context['distribuicao']), 2)
        self.assertTrue(all(len(g['linhas'][0]['celulas'][1]) == 1 for g in r.context['distribuicao']))

    def test_permissoes_e_csrf_principal(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.gestor)
        self.assertEqual(cliente.post(self.url, {'acao': 'gerar'}).status_code, 403)
        for usuario in (None, get_user_model().objects.create_user('professor-sem-gestao')):
            self.client.logout()
            if usuario:
                self.client.force_login(usuario)
            for dados in ({'acao': 'gerar'}, {'acao': 'salvar'}, {'acao': 'descartar'}, {'data_grade': self.segunda.isoformat()}):
                self.assertEqual(self.client.post(self.url, dados).status_code, 302)
            self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(AlocacaoGrade.objects.count(), 1)

    def test_token_e_dados_adulterados_nao_substituem_proposta(self):
        self.gerar()
        r = self.client.post(self.url, {'acao': 'salvar', 'token': 'errado'})
        self.assertTrue(r.context['erro'])
        self.assertEqual(AlocacaoGrade.objects.count(), 1)
        r = self.confirmar(professor_id=999999, propostas='[]', semana='2027-01-04')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(AlocacaoGrade.objects.count(), 24)
        self.assertFalse(AlocacaoGrade.objects.exclude(professor=self.professor).exists())
