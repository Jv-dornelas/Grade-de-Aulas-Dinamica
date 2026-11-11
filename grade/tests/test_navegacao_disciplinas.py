from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .factories import criar_cenario_grade
from ..disciplinas import consolidar_duplicadas
from ..models import Disciplina, AlocacaoGrade, DemandaAula


class NavegacaoCadastrosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        criar_cenario_grade(cls)

    def setUp(self):
        self.client.force_login(self.gestor)

    def test_header_compartilhado_em_listas_cadastros_selecoes_e_edicoes(self):
        rotas = ['cadastrar_professor', 'lista_professores', 'atualizar_professor', 'excluir_professor',
                 'cadastrar_unidade', 'lista_unidades', 'atualizar_unidade', 'excluir_unidade',
                 'cadastrar_disciplina', 'lista_disciplinas', 'atualizar_disciplina', 'excluir_disciplina']
        destinos = [(r, []) for r in rotas] + [
            ('editar_professor', [self.professor.pk]), ('confirmar_exclusao_professor', [self.professor.pk]),
            ('editar_unidade', [self.unidade.pk]), ('confirmar_exclusao_unidade', [self.unidade.pk]),
            ('editar_disciplina', [self.disciplina.pk]), ('confirmar_exclusao_disciplina', [self.disciplina.pk])]
        for rota, args in destinos:
            with self.subTest(rota=rota):
                r = self.client.get(reverse('grade:' + rota, args=args))
                self.assertEqual(r.status_code, 200)
                self.assertTemplateUsed(r, 'grade/navegacao_principal.html')
                self.assertContains(r, 'grade/navegacao.css')
                self.assertContains(r, '<header class="topbar">', count=1)
                self.assertContains(r, reverse('grade:inicio'))
                self.assertContains(r, reverse('grade:turmas'))

    def test_seta_disciplina_abre_edicao_real(self):
        r = self.client.get(reverse('grade:lista_disciplinas'))
        self.assertContains(r, reverse('grade:editar_disciplina', args=[self.disciplina.pk]))
        self.assertNotContains(r, 'href="#"')

    def test_novas_duplicatas_sao_recusadas(self):
        d = Disciplina(nome='  ' + self.disciplina.nome + '  ', area=self.disciplina.area)
        with self.assertRaises(ValidationError):
            d.save()
        r = self.client.post(reverse('grade:cadastrar_disciplina'), {'nome': self.disciplina.nome, 'area': self.disciplina.area})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Disciplina.objects.count(), 1)

    def test_consolidacao_preserva_carga_aulas_e_habilitacoes(self):
        duplicada = Disciplina(nome=' ' + self.disciplina.nome + ' ', area=self.disciplina.area)
        Disciplina.objects.bulk_create([duplicada])  # Simula cadastro legado anterior à validação.
        self.professor.disciplinas.clear()
        self.professor.disciplinas.add(duplicada)
        AlocacaoGrade.objects.filter(pk=self.fixa.pk).update(disciplina=duplicada)
        DemandaAula.objects.filter(pk=self.demanda.pk).update(disciplina=duplicada)
        antes = AlocacaoGrade.objects.values().get(pk=self.fixa.pk)
        plano = consolidar_duplicadas()
        self.assertEqual(len(plano), 1)
        self.assertEqual(Disciplina.objects.count(), 2)
        consolidar_duplicadas(aplicar=True)
        self.assertEqual(Disciplina.objects.count(), 1)
        depois = AlocacaoGrade.objects.values().get(pk=self.fixa.pk)
        self.assertEqual({k:v for k,v in antes.items() if k != 'disciplina_id'},
                         {k:v for k,v in depois.items() if k != 'disciplina_id'})
        self.assertEqual(depois['disciplina_id'], self.disciplina.pk)
        self.assertEqual(self.demanda.__class__.objects.get(pk=self.demanda.pk).quantidade_semana, 24)
        self.assertTrue(self.professor.disciplinas.filter(pk=self.disciplina.pk).exists())
        self.assertEqual(consolidar_duplicadas(aplicar=True), [])
