from django.test import SimpleTestCase, override_settings


@override_settings(ROOT_URLCONF='configuracao_site.urls_mobile_publico', DEBUG=False)
class MobilePublicoTests(SimpleTestCase):
    def test_gestao_e_arquivos_nao_publicados(self):
        for url in ['/', '/admin/', '/api/professores/', '/inicio/', '/automacao/',
                    '/cursos/', '/static/grade/mobile/MinhaGrade-demo.apk', '/.env']:
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_login_e_assets_disponiveis(self):
        self.assertEqual(self.client.get('/mobile/entrar/').status_code, 200)
        self.assertEqual(self.client.get('/static/grade/mobile/mobile.css').status_code, 200)

    def test_consulta_e_pdf_exigem_login(self):
        for url in ['/mobile/', '/mobile/grade.pdf']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/mobile/entrar/', response.url)
