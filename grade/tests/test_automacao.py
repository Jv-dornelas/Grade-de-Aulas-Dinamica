"""Fluxo de prévia e confirmação, sempre no banco isolado do Django TestCase."""

from copy import deepcopy
from datetime import date, time
from unittest.mock import patch

from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import (
    AlocacaoGrade, DemandaAula, Disciplina, Disponibilidade,
    DisponibilidadeHorario, HorarioAula, MatrizDistancia, Professor,
    Turma, Unidade,
)


class AutomacaoSemanalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-automacao', is_staff=True)
        cls.visitante = get_user_model().objects.create_user('professor-automacao')
        cls.segunda = date(2026, 9, 21)
        cls.escola = Unidade.objects.create(nome='Escola para testes', responsavel='Coordenação')
        cls.disciplina = Disciplina.objects.create(nome='Matemática', area='EXATAS')
        cls.professor = Professor.objects.create(
            nome='Ana', unidade_oficial=cls.escola, limite_aulas=5,
        )
        cls.professor.disciplinas.add(cls.disciplina)
        cls.horario = HorarioAula.objects.create(
            nome='Primeira aula', hora_inicio=time(8), hora_fim=time(9),
        )
        cls.segundo_horario = HorarioAula.objects.create(
            nome='Segunda aula', hora_inicio=time(9), hora_fim=time(10),
        )
        cls.turma = Turma.objects.create(materias_fixas=False, nome='6º A', unidade=cls.escola, dias_semana=[0])
        cls.turma.horarios.add(cls.horario, cls.segundo_horario)
        cls.demanda = DemandaAula.objects.create(
            turma=cls.turma, disciplina=cls.disciplina,
            quantidade_semana=1, professor=cls.professor,
        )
        cls.disponibilidade = Disponibilidade.objects.create(
            professor=cls.professor, data=cls.segunda, disponivel_manha=True,
        )

    def setUp(self):
        self.url = reverse('grade:automacao')
        self.client.force_login(self.gestor)

    def proposta(self, **alteracoes):
        proposta = {
            'data': self.segunda.isoformat(), 'horario_id': self.horario.pk,
            'unidade_id': self.escola.pk, 'professor_id': self.professor.pk,
            'turma_id': self.turma.pk, 'disciplina_id': self.disciplina.pk,
            'demanda_id': self.demanda.pk,
        }
        proposta.update(alteracoes)
        return proposta

    def resultado(self, pendentes=0):
        return {
            'status': 'optimal', 'propostas': [self.proposta()], 'avisos': [],
            'pendencias': ['Uma aula ainda não foi atendida.'] if pendentes else [],
            'resumo': {'fixas': 0, 'solicitadas': 1 + pendentes,
                       'geradas': 1, 'pendentes': pendentes},
        }

    def gerar_previa(self, resultado=None, semana='2026-09-21'):
        resultado = deepcopy(resultado if resultado is not None else self.resultado())
        with patch('grade.automacao.gerar_semana', return_value=resultado) as gerador:
            resposta = self.client.post(self.url, {
                'acao': 'gerar', 'semana': semana, 'proximidade': '15',
            })
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(resposta.context['erro'])
        self.assertIn('automacao_previa', self.client.session)
        return self.client.session['automacao_previa'], gerador

    def salvar(self, previa, **dados):
        dados = {'acao': 'salvar', 'token': previa['token'], **dados}
        return self.client.post(self.url, dados)

    def assert_rejeitado_sem_gravar(self, resposta, quantidade=0):
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.context['erro'])
        self.assertEqual(AlocacaoGrade.objects.count(), quantidade)

    def test_acesso_restrito_a_gestores_em_get_e_post(self):
        for usuario in (None, self.visitante):
            with self.subTest(usuario=usuario):
                self.client.logout()
                if usuario:
                    self.client.force_login(usuario)
                for metodo in (self.client.get, self.client.post):
                    resposta = metodo(self.url, {'acao': 'gerar', 'semana': '2026-09-21'})
                    self.assertIn(resposta.status_code, (302, 403))
                self.assertNotIn('automacao_previa', self.client.session)
        self.assertEqual(AlocacaoGrade.objects.count(), 0)

    def test_confirmacao_exige_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.gestor)
        self.assertEqual(cliente.post(self.url, {'acao': 'gerar'}).status_code, 403)
        self.assertEqual(AlocacaoGrade.objects.count(), 0)

    def test_geracao_real_e_confirmacao_preservam_aula_existente(self):
        self.demanda.quantidade_semana = 2
        self.demanda.save(update_fields=['quantidade_semana'])
        fixa = AlocacaoGrade.objects.create(
            data=self.segunda, horario=self.horario, unidade=self.escola,
            professor=self.professor, turma=self.turma,
            disciplina=self.disciplina, demanda=self.demanda,
        )
        estado_fixa = AlocacaoGrade.objects.values().get(pk=fixa.pk)
        resposta = self.client.post(self.url, {
            'acao': 'gerar', 'semana': '2026-09-21', 'proximidade': '15',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(resposta.context['erro'])
        previa = self.client.session['automacao_previa']
        self.assertIn(previa['resultado']['status'], ('optimal', 'feasible'))
        self.assertEqual(len(previa['resultado']['propostas']), 1)
        self.assertEqual(AlocacaoGrade.objects.count(), 1, 'A prévia não pode gravar aulas.')

        resposta = self.salvar(previa)
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(AlocacaoGrade.objects.count(), 2)
        self.assertEqual(AlocacaoGrade.objects.values().get(pk=fixa.pk), estado_fixa)
        nova = AlocacaoGrade.objects.exclude(pk=fixa.pk).get()
        self.assertEqual(nova.horario_id, self.segundo_horario.pk)
        self.assertEqual(nova.demanda_id, self.demanda.pk)
        self.assertNotIn('automacao_previa', self.client.session)

    def test_semana_e_normalizada_para_segunda(self):
        previa, gerador = self.gerar_previa(semana='2026-09-24')
        self.assertEqual(previa['inicio'], '2026-09-21')
        argumentos = gerador.call_args
        inicio = argumentos.args[0] if argumentos.args else argumentos.kwargs['inicio']
        self.assertEqual(inicio, self.segunda)

    def test_aula_confirmada_aparece_no_mobile_e_permite_baixar_pdf(self):
        self.professor.usuario = self.visitante
        self.professor.save(update_fields=['usuario'])
        previa, _ = self.gerar_previa()
        self.assertEqual(self.salvar(previa).status_code, 302)
        self.client.force_login(self.visitante)

        resposta = self.client.get(reverse('grade:mobile'), {'semana': '2026-09-21'})
        self.assertContains(resposta, self.escola.nome)
        self.assertContains(resposta, self.disciplina.nome)
        self.assertContains(resposta, self.turma.nome)
        self.assertEqual(len(resposta.context['aulas']), 1)
        self.assertEqual(resposta.context['aulas'][0].demanda_id, self.demanda.pk)

        pdf = self.client.get(reverse('grade:mobile_pdf'), {'semana': '2026-09-21'})
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertIn('attachment', pdf['Content-Disposition'])
        self.assertTrue(b''.join(pdf.streaming_content).startswith(b'%PDF-'))

    def test_admin_da_turma_exibe_e_salva_multiplos_dias(self):
        administrador = get_user_model().objects.create_user(
            'admin-calendario', is_staff=True, is_superuser=True,
        )
        self.client.force_login(administrador)
        url = reverse('admin:grade_turma_change', args=[self.turma.pk])
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 200)
        campo = resposta.context['adminform'].form.fields['dias_semana']
        self.assertIsInstance(campo.widget, forms.CheckboxSelectMultiple)
        for nome in ('Segunda', 'Quarta', 'Sexta', 'Domingo'):
            self.assertContains(resposta, nome)

        resposta = self.client.post(url, {
            'nome': self.turma.nome, 'unidade': self.escola.pk,
            'dias_semana': ['0', '2', '4'],
            'horarios': [self.horario.pk, self.segundo_horario.pk],
            '_save': 'Salvar',
        })
        self.assertEqual(resposta.status_code, 302)
        self.turma.refresh_from_db()
        self.assertEqual(self.turma.dias_semana, [0, 2, 4])

    def test_get_nao_gera_nem_grava(self):
        with patch('grade.automacao.gerar_semana') as gerador:
            resposta = self.client.get(self.url, {'semana': '2026-09-21'})
        self.assertEqual(resposta.status_code, 200)
        gerador.assert_not_called()
        self.assertEqual(AlocacaoGrade.objects.count(), 0)

    def test_confirmacao_usa_propostas_da_sessao(self):
        previa, _ = self.gerar_previa()
        resposta = self.salvar(
            previa, professor_id='99999', unidade_id='99999',
            propostas='[{"professor_id":99999}]', semana='2027-01-04',
        )
        self.assertEqual(resposta.status_code, 302)
        aula = AlocacaoGrade.objects.get()
        self.assertEqual(aula.professor_id, self.professor.pk)
        self.assertEqual(aula.unidade_id, self.escola.pk)
        self.assertEqual(aula.data, self.segunda)

    def test_token_incorreto_e_sessao_diferente_nao_confirmam(self):
        previa, _ = self.gerar_previa()
        resposta = self.salvar(previa, token='token-adulterado')
        self.assert_rejeitado_sem_gravar(resposta)
        outro_cliente = Client()
        outro_cliente.force_login(self.gestor)
        resposta = outro_cliente.post(self.url, {'acao': 'salvar', 'token': previa['token']})
        self.assert_rejeitado_sem_gravar(resposta)

    def test_confirmacao_repetida_nao_duplica(self):
        previa, _ = self.gerar_previa()
        self.assertEqual(self.salvar(previa).status_code, 302)
        self.assert_rejeitado_sem_gravar(self.salvar(previa), quantidade=1)

    def test_previa_expirada_nao_pode_ser_confirmada(self):
        previa, _ = self.gerar_previa()
        sessao = self.client.session
        previa['criada_em'] -= 30 * 60 + 1
        sessao['automacao_previa'] = previa
        sessao.save()
        self.assert_rejeitado_sem_gravar(self.salvar(previa))

    def test_parcial_exige_aceite_e_respeita_demanda(self):
        self.demanda.quantidade_semana = 2
        self.demanda.save(update_fields=['quantidade_semana'])
        previa, _ = self.gerar_previa(self.resultado(pendentes=1))
        self.assert_rejeitado_sem_gravar(self.salvar(previa))
        resposta = self.salvar(previa, aceitar_parcial='on')
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(AlocacaoGrade.objects.count(), 1)

    def test_descartar_remove_apenas_previa(self):
        fixa = AlocacaoGrade.objects.create(
            data=date(2026, 9, 14), horario=self.horario,
            unidade=self.escola, professor=self.professor,
        )
        self.gerar_previa()
        resposta = self.client.post(self.url, {'acao': 'descartar'})
        self.assertEqual(resposta.status_code, 302)
        self.assertNotIn('automacao_previa', self.client.session)
        self.assertEqual(list(AlocacaoGrade.objects.values_list('pk', flat=True)), [fixa.pk])

    def test_alteracao_de_disponibilidade_invalida_previa(self):
        previa, _ = self.gerar_previa()
        self.disponibilidade.disponivel_manha = False
        self.disponibilidade.save(update_fields=['disponivel_manha'])
        self.assert_rejeitado_sem_gravar(self.salvar(previa))

    def test_disponibilidade_especifica_posterior_invalida_previa(self):
        previa, _ = self.gerar_previa()
        DisponibilidadeHorario.objects.create(
            professor=self.professor, data=self.segunda,
            horario=self.horario, disponivel=False,
        )
        self.assert_rejeitado_sem_gravar(self.salvar(previa))

    def test_alteracao_de_demanda_invalida_previa(self):
        previa, _ = self.gerar_previa()
        self.demanda.quantidade_semana = 2
        self.demanda.save(update_fields=['quantidade_semana'])
        self.assert_rejeitado_sem_gravar(self.salvar(previa))

    def test_alteracao_de_calendario_m2m_invalida_previa(self):
        previa, _ = self.gerar_previa()
        self.turma.horarios.remove(self.horario)
        self.assert_rejeitado_sem_gravar(self.salvar(previa))

    def test_alteracao_de_habilitacao_m2m_invalida_previa(self):
        previa, _ = self.gerar_previa()
        self.professor.disciplinas.remove(self.disciplina)
        self.assert_rejeitado_sem_gravar(self.salvar(previa))

    def test_alteracao_de_parentesco_invalida_previa(self):
        parente = Professor.objects.create(nome='Bruno', unidade_oficial=self.escola)
        previa, _ = self.gerar_previa()
        parente.parente_vinculado = self.professor
        parente.save(update_fields=['parente_vinculado'])
        self.assert_rejeitado_sem_gravar(self.salvar(previa))

    def test_alteracao_de_matriz_invalida_previa(self):
        outra_escola = Unidade.objects.create(nome='Outra escola', responsavel='Coordenação')
        trajeto = MatrizDistancia.objects.create(
            origem=self.escola, destino=outra_escola, tempo_minutos=5,
        )
        previa, _ = self.gerar_previa()
        trajeto.tempo_minutos = 60
        trajeto.save(update_fields=['tempo_minutos'])
        self.assert_rejeitado_sem_gravar(self.salvar(previa))

    def test_nova_aula_gravada_depois_da_previa_nao_e_sobrescrita(self):
        previa, _ = self.gerar_previa()
        existente = AlocacaoGrade.objects.create(
            data=self.segunda, horario=self.horario, unidade=self.escola,
            professor=self.professor, turma=self.turma,
            disciplina=self.disciplina, demanda=self.demanda,
        )
        self.assert_rejeitado_sem_gravar(self.salvar(previa), quantidade=1)
        self.assertTrue(AlocacaoGrade.objects.filter(pk=existente.pk).exists())

    def test_confirmacao_revalida_restricoes_da_proposta(self):
        resultado = self.resultado()
        resultado['propostas'][0]['data'] = '2026-09-22'
        previa, _ = self.gerar_previa(resultado)
        self.assert_rejeitado_sem_gravar(self.salvar(previa))

    def test_lote_com_uma_proposta_invalida_nao_grava_nenhuma(self):
        self.demanda.quantidade_semana = 2
        self.demanda.save(update_fields=['quantidade_semana'])
        resultado = self.resultado()
        resultado['propostas'].append(self.proposta(data='2026-09-22'))
        previa, _ = self.gerar_previa(resultado)
        self.assert_rejeitado_sem_gravar(self.salvar(previa))

    def test_edicao_durante_geracao_descarta_previa(self):
        self.gerar_previa()

        def gerar_e_alterar(*args, **kwargs):
            self.demanda.quantidade_semana = 2
            self.demanda.save(update_fields=['quantidade_semana'])
            return self.resultado()

        with patch('grade.automacao.gerar_semana', side_effect=gerar_e_alterar):
            resposta = self.client.post(self.url, {
                'acao': 'gerar', 'semana': '2026-09-21', 'proximidade': '15',
            })
        self.assert_rejeitado_sem_gravar(resposta)
        self.assertNotIn('automacao_previa', self.client.session)

    def test_sem_demanda_nao_cria_aulas(self):
        self.demanda.delete()
        resposta = self.client.post(self.url, {
            'acao': 'gerar', 'semana': '2026-09-21', 'proximidade': '15',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(AlocacaoGrade.objects.count(), 0)
        previa = self.client.session.get('automacao_previa')
        if previa:
            self.assertEqual(previa['resultado']['propostas'], [])
            self.assert_rejeitado_sem_gravar(self.salvar(previa))

    def test_formulario_invalido_nao_aciona_gerador(self):
        for campos in (
            {'semana': '2026-02-30', 'proximidade': '15'},
            {'semana': '2026-09-21', 'proximidade': '-1'},
            {'semana': '2026-09-21', 'proximidade': 'nao-e-numero'},
            {'semana': '9999-12-31', 'proximidade': '15'},
        ):
            with self.subTest(campos=campos), patch('grade.automacao.gerar_semana') as gerador:
                resposta = self.client.post(self.url, {'acao': 'gerar', **campos})
                self.assertEqual(resposta.status_code, 200)
                gerador.assert_not_called()
                self.assertTrue(resposta.context['form'].errors or resposta.context['erro'])
        self.assertEqual(AlocacaoGrade.objects.count(), 0)
