import re

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class RecuperacaoCsrfTests(TestCase):
    def test_token_antigo_apos_login_em_outra_aba_e_recuperacao(self):
        senha = 'credencial-so-do-teste'
        get_user_model().objects.create_user('gestor-csrf', password=senha, is_staff=True)
        get_user_model().objects.create_user('professor-csrf', password=senha)
        c = Client(enforce_csrf_checks=True)
        mobile = reverse('grade:mobile_login')
        home = reverse('grade:inicio')
        tela = c.get(mobile)
        antigo = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', tela.content.decode()).group(1)
        self.assertEqual(c.post(home, {'username': 'gestor-csrf', 'password': senha,
                                    'csrfmiddlewaretoken': antigo}).status_code, 302)
        r = c.post(mobile, {'username': 'professor-csrf', 'password': senha,
                           'csrfmiddlewaretoken': antigo})
        self.assertEqual(r.status_code, 403)
        self.assertTemplateUsed(r, 'grade/mobile/sessao_expirada.html')
        self.assertContains(r, 'Abrir login atualizado', status_code=403)
        self.assertNotContains(r, senha, status_code=403)
        self.assertNotContains(r, 'Reason given', status_code=403)
        gestor_id = c.session['_auth_user_id']
        novo = c.get(mobile)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', novo.content.decode()).group(1)
        r = c.post(mobile, {'username': 'professor-csrf', 'password': senha,
                           'csrfmiddlewaretoken': token})
        self.assertEqual(r.status_code, 302)
        self.assertNotEqual(c.session['_auth_user_id'], gestor_id)

    def test_ausencia_de_token_continua_bloqueada(self):
        c = Client(enforce_csrf_checks=True)
        for rota in ['grade:inicio', 'grade:mobile_login']:
            r = c.post(reverse(rota), {'username': 'nao-usado', 'password': 'nao-expor'})
            self.assertEqual(r.status_code, 403)
            self.assertNotContains(r, 'nao-expor', status_code=403)
            self.assertIn('no-store', r.headers['Cache-Control'])
