from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class AcessoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.senha = 'senha-apenas-para-teste-local'
        cls.gestor = get_user_model().objects.create_user('gestor-entrada', password=cls.senha, is_staff=True)
        cls.professor = get_user_model().objects.create_user('docente-entrada', password=cls.senha)
        cls.inativo = get_user_model().objects.create_user('inativo-entrada', password=cls.senha, is_staff=True, is_active=False)

    def test_home_anonima_tem_login_e_nao_expoe_painel(self):
        r = self.client.get(reverse('grade:inicio'))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'grade/login_grade.html')
        self.assertContains(r, 'name="username"')
        self.assertContains(r, 'name="password"')
        self.assertContains(r, 'csrfmiddlewaretoken')
        self.assertContains(r, 'grade/login.css')
        self.assertNotContains(r, 'dashboard-kpis')

    def test_login_valido_abre_home_e_grade(self):
        r = self.client.post(reverse('grade:inicio'), {'username': self.gestor.username, 'password': self.senha})
        self.assertRedirects(r, reverse('grade:inicio'))
        self.assertTemplateUsed(self.client.get(reverse('grade:inicio')), 'grade/inicio.html')
        self.assertEqual(self.client.get(reverse('grade:exibir_grade')).status_code, 200)

    def test_destino_original_e_filtros_preservados(self):
        destino = reverse('grade:exibir_grade') + '?data=2026-11-09&por=turma'
        r = self.client.get(destino)
        self.assertEqual(urlparse(r.url).path, reverse('grade:inicio'))
        self.assertEqual(parse_qs(urlparse(r.url).query)['next'], [destino])
        r = self.client.post(reverse('grade:inicio'), {'username': self.gestor.username, 'password': self.senha, 'next': destino})
        self.assertRedirects(r, destino)

    def test_redirecionamento_externo_recusado(self):
        r = self.client.post(reverse('grade:inicio'), {'username': self.gestor.username, 'password': self.senha, 'next': 'https://externo.invalid/'})
        self.assertRedirects(r, reverse('grade:inicio'))

    def test_senha_errada_inativo_e_sem_permissao_nao_entram(self):
        for username, senha in [(self.gestor.username, 'errada'), (self.inativo.username, self.senha), (self.professor.username, self.senha)]:
            r = self.client.post(reverse('grade:inicio'), {'username': username, 'password': senha})
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.context['form'].errors)
            self.assertNotIn('_auth_user_id', self.client.session)
            self.assertNotContains(r, f'value="{senha}"')

    def test_csrf_e_logout_post(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post(reverse('grade:inicio'), {'username': self.gestor.username, 'password': self.senha}).status_code, 403)
        c.get(reverse('grade:inicio'))
        r = c.post(reverse('grade:inicio'), {'username': self.gestor.username, 'password': self.senha, 'csrfmiddlewaretoken': c.cookies['csrftoken'].value})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(c.get(reverse('grade:sair')).status_code, 405)
        self.assertEqual(c.post(reverse('grade:sair')).status_code, 403)
        r = c.post(reverse('grade:sair'), {'csrfmiddlewaretoken': c.cookies['csrftoken'].value})
        self.assertRedirects(r, reverse('grade:inicio'))
        self.assertNotIn('_auth_user_id', c.session)

    def test_cadastros_usam_entrada_do_sistema(self):
        for rota in ['cursos', 'turmas', 'lista_professores', 'automacao']:
            r = self.client.get(reverse('grade:' + rota))
            self.assertEqual(r.status_code, 302)
            self.assertEqual(urlparse(r.url).path, reverse('grade:inicio'))
