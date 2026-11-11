from datetime import timedelta
from pathlib import Path
import os

from django.test import TestCase
from django.urls import reverse

from .factories import criar_cenario_grade
from ..models import AlocacaoGrade, Professor
from ..automacao import CHAVE_PREVIA


class EdicaoPdfTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def setUp(self):
        self.url = reverse('grade:exibir_grade')
        self.client.force_login(self.gestor)

    def post_aula(self, r, **alteracoes):
        aula = r.context['aula_editor']
        dados = {'acao': 'salvar_aula', 'data': aula.data.isoformat() if aula.data else self.segunda.isoformat(),
            'horario': aula.horario_id or self.horarios[1].pk, 'unidade': self.unidade.pk,
            'demanda': aula.demanda_id or '', 'professor': self.professor.pk,
            'estado': r.context['estado_editor']}
        if r.context['editor_proposta']:
            dados.update(proposta=r.context['indice_editor'], token=self.client.session[CHAVE_PREVIA]['token'])
        elif aula.pk:
            dados['editar'] = aula.pk
        else:
            dados['nova'] = '1'
        return self.client.post(self.url, {**dados, **alteracoes})

    def gerar(self):
        self.client.post(self.url, {'acao':'gerar', 'semana':self.segunda.isoformat(), 'proximidade':15})

    def test_editar_salva_na_mesma_grade_preservando_vinculos(self):
        r = self.client.get(self.url, {'data':self.segunda.isoformat(), 'editar':self.fixa.pk})
        self.assertContains(r, 'Editar aula salva')
        self.assertNotContains(r, 'id="gradeForm"')
        self.assertEqual(self.post_aula(r, horario=self.horarios[1].pk).status_code,302)
        self.fixa.refresh_from_db()
        self.assertEqual(self.fixa.horario_id,self.horarios[1].pk)
        self.assertEqual(self.fixa.demanda_id,self.demanda.pk)
        self.assertEqual(self.fixa.turma_id,self.turma.pk)
        self.assertEqual(AlocacaoGrade.objects.count(),1)

    def test_editor_desatualizado_nao_sobregrava(self):
        r = self.client.get(self.url, {'editar':self.fixa.pk})
        self.fixa.horario=self.horarios[2]
        self.fixa.save()
        resposta=self.post_aula(r, horario=self.horarios[1].pk)
        self.assertIn('mudou',resposta.context['erro_editor'])
        self.fixa.refresh_from_db()
        self.assertEqual(self.fixa.horario_id,self.horarios[2].pk)

    def test_nova_aula_exige_matriz_e_recusa_sobreposicao(self):
        r = self.client.get(self.url, {'nova':1, 'data':self.segunda.isoformat()})
        resposta = self.post_aula(r, horario=self.horarios[1].pk)
        self.assertIn('demanda', resposta.context['aula_form'].errors)
        self.assertEqual(self.post_aula(r, horario=self.horarios[1].pk, demanda=self.demanda.pk).status_code,302)
        r=self.client.get(self.url, {'nova':1,'data':self.segunda.isoformat()})
        resposta=self.post_aula(r, horario=self.horarios[1].pk, demanda=self.demanda.pk)
        self.assertTrue(resposta.context['aula_form'].errors)
        self.assertEqual(AlocacaoGrade.objects.count(),2)

    def test_ajustar_previa_valida_lote_e_nao_grava(self):
        self.gerar()
        r=self.client.get(self.url, {'proposta':0})
        anterior=self.client.session[CHAVE_PREVIA]['token']
        # Mantém o mesmo horário/professor; passa pelo validador de todo o lote.
        self.assertEqual(self.post_aula(r).status_code,302)
        self.assertEqual(AlocacaoGrade.objects.count(),1)
        self.assertNotEqual(self.client.session[CHAVE_PREVIA]['token'],anterior)
        self.assertTrue(self.client.session[CHAVE_PREVIA]['resultado']['ajustada_manualmente'])
        r=self.client.get(self.url, {'proposta':0})
        resposta=self.post_aula(r, horario=self.horarios[0].pk, data=self.segunda.isoformat())
        self.assertTrue(resposta.context['aula_form'].errors or resposta.context['erro_editor'])
        self.assertEqual(AlocacaoGrade.objects.count(),1)

    def test_correcoes_nao_podem_inventar_disponibilidade_ou_habilitacao(self):
        professor=Professor.objects.create(nome='Sem habilitação',unidade_oficial=self.unidade)
        r=self.client.get(self.url, {'editar':self.fixa.pk})
        resposta=self.post_aula(r,professor=professor.pk)
        self.assertTrue(resposta.context['aula_form'].errors)
        self.fixa.refresh_from_db()
        self.assertEqual(self.fixa.professor_id,self.professor.pk)

    def test_pdf_salvas_previa_filtro_e_sem_persistencia(self):
        pdf_url=reverse('grade:grade_pdf')
        for por in ('curso','turma','professor','unidade'):
            r=self.client.get(pdf_url,{'data':self.segunda.isoformat(),'por':por})
            self.assertEqual(r.status_code,200)
            self.assertEqual(r['Content-Type'],'application/pdf')
            self.assertTrue(b''.join(r.streaming_content).startswith(b'%PDF-'))
        self.gerar()
        r=self.client.get(pdf_url,{'data':self.segunda.isoformat(),'por':'curso','entidade':self.curso.pk})
        pdf=b''.join(r.streaming_content)
        self.assertEqual(AlocacaoGrade.objects.count(),1)
        if os.environ.get('GRADE_QA_DIR'):
            pasta=Path(os.environ['GRADE_QA_DIR']);pasta.mkdir(parents=True,exist_ok=True)
            (pasta/'grade-editavel-previa.pdf').write_bytes(pdf)
        self.curso.observacoes='Alteração após prévia'
        self.curso.save()
        self.assertEqual(self.client.get(pdf_url,{'data':self.segunda.isoformat()}).status_code,400)

    def test_pdf_e_editor_exigem_coordenacao(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('grade:grade_pdf')).status_code,302)
        self.assertEqual(self.client.post(self.url,{'acao':'salvar_aula','editar':self.fixa.pk}).status_code,302)

    def test_disponibilidade_na_mesma_pagina_preserva_aulas(self):
        r=self.client.get(self.url,{'data':self.segunda.isoformat()})
        dados={'acao':'salvar_disponibilidade','data_grade':self.segunda.isoformat(),
               'assinatura':r.context['assinatura_disponibilidade'], f'disp_manha_{self.professor.pk}':'on'}
        self.assertEqual(self.client.post(self.url,dados).status_code,302)
        self.assertEqual(AlocacaoGrade.objects.count(),1)
        r=self.client.get(self.url,{'data':self.segunda.isoformat()})
        dados['assinatura']=r.context['assinatura_disponibilidade']
        dados.pop(f'disp_manha_{self.professor.pk}')
        resposta=self.client.post(self.url,dados)
        self.assertIn('disponibilidade',resposta.context['erro_negocio'])
        self.assertEqual(AlocacaoGrade.objects.count(),1)

    def test_previa_nao_autoriza_trocar_aula_fixa(self):
        self.gerar()
        r=self.client.get(self.url,{'editar':self.fixa.pk})
        resposta=self.post_aula(r,horario=self.horarios[1].pk)
        self.assertIn('descarte',resposta.context['erro_editor'])
        self.fixa.refresh_from_db()
        self.assertEqual(self.fixa.horario_id,self.horarios[0].pk)

    def test_assinatura_do_editor_adulterada_nao_grava(self):
        r=self.client.get(self.url,{'editar':self.fixa.pk})
        resposta=self.post_aula(r,estado='adulterado',horario=self.horarios[1].pk)
        self.assertIn('inválido',resposta.context['erro_editor'])
        self.assertEqual(AlocacaoGrade.objects.count(),1)
