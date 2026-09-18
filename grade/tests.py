from datetime import date, time
import base64
import re
import zlib

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Professor, Unidade, HorarioAula, AlocacaoGrade


class MobileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('ana', password='senha-teste-42')
        cls.other = get_user_model().objects.create_user('bia', password='outra-senha-42')
        cls.prof = Professor.objects.create(nome='Ana', usuario=cls.user)
        cls.prof_other = Professor.objects.create(nome='Bia', usuario=cls.other)
        cls.unit = Unidade.objects.create(nome='Unidade da Ana', responsavel='Coordenação')
        cls.unit_other = Unidade.objects.create(nome='Unidade privada da Bia', responsavel='Coordenação')
        cls.slot = HorarioAula.objects.create(nome='Primeira aula', hora_inicio=time(8), hora_fim=time(9))
        AlocacaoGrade.objects.create(data=date(2026, 9, 14), horario=cls.slot, unidade=cls.unit, professor=cls.prof)
        AlocacaoGrade.objects.create(data=date(2026, 9, 14), horario=cls.slot, unidade=cls.unit_other, professor=cls.prof_other)
        AlocacaoGrade.objects.create(data=date(2026, 9, 20), horario=cls.slot, unidade=cls.unit, professor=cls.prof)
        AlocacaoGrade.objects.create(data=date(2026, 9, 21), horario=cls.slot, unidade=cls.unit, professor=cls.prof)

    def setUp(self):
        self.client.force_login(self.user)

    def test_anonymous_cannot_access_schedule_or_pdf(self):
        self.client.logout()
        for name in ('mobile', 'mobile_pdf'):
            response = self.client.get(reverse('grade:' + name))
            self.assertEqual(response.status_code, 302)
            self.assertIn('/mobile/entrar/', response.url)

    def test_week_and_identity_are_enforced(self):
        response = self.client.get(reverse('grade:mobile'), {'semana': '2026-09-17', 'professor': self.prof_other.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['inicio'], date(2026, 9, 14))
        self.assertEqual(len(response.context['aulas']), 2)
        self.assertContains(response, 'Unidade da Ana')
        self.assertNotContains(response, 'Unidade privada da Bia')
        self.assertIn('no-store', response['Cache-Control'])

    def test_unlinked_account_is_denied(self):
        self.client.force_login(get_user_model().objects.create_user('sem-vinculo'))
        for name in ('mobile', 'mobile_pdf'):
            self.assertEqual(self.client.get(reverse('grade:' + name)).status_code, 403)

    def test_invalid_dates_and_extremes_do_not_crash(self):
        for value in ('invalida', '2026-02-30', '0001-01-01', '9999-12-31'):
            for name in ('mobile', 'mobile_pdf'):
                self.assertEqual(self.client.get(reverse('grade:' + name), {'semana': value}).status_code, 400)

    def test_empty_week_and_no_write(self):
        before = AlocacaoGrade.objects.count()
        self.assertContains(self.client.get(reverse('grade:mobile'), {'semana': '2027-01-01'}), 'Uma semana sem aulas cadastradas')
        self.assertEqual(self.client.post(reverse('grade:mobile'), {}).status_code, 405)
        self.assertEqual(AlocacaoGrade.objects.count(), before)

    def test_pdf_is_downloadable_and_private(self):
        response = self.client.get(reverse('grade:mobile_pdf'), {'semana': '2026-09-14', 'professor': self.prof_other.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])
        content = b''.join(response.streaming_content)
        self.assertTrue(content.startswith(b'%PDF-'))
        streams = re.findall(rb'stream\r?\n(.*?)endstream', content, re.S)
        decoded = b''.join(zlib.decompress(base64.a85decode(stream.strip(), adobe=True)) for stream in streams)
        self.assertIn(b'Unidade da Ana', decoded)
        self.assertNotIn(b'Unidade privada da Bia', decoded)

    def test_login_logout_and_safe_redirect(self):
        self.client.logout()
        response = self.client.post(reverse('grade:mobile_login'), {'username': 'ana', 'password': 'senha-teste-42', 'next': 'https://example.org/'})
        self.assertRedirects(response, reverse('grade:mobile'))
        self.assertEqual(self.client.get(reverse('grade:mobile_logout')).status_code, 405)
        self.client.post(reverse('grade:mobile_logout'))
        self.assertEqual(self.client.get(reverse('grade:mobile')).status_code, 302)

    def test_management_routes_block_teacher_and_shared_password(self):
        self.assertEqual(self.client.get('/').status_code, 302)
        for path in ('professores', 'alocacoes', 'unidades', 'disciplinas', 'horarios', 'disponibilidades', 'distancias'):
            self.assertEqual(self.client.get('/api/' + path + '/').status_code, 403)
            self.assertEqual(self.client.post('/api/' + path + '/', {}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.post('/', {'senha_acesso': 'grade2026'}).status_code, 302)
        self.assertFalse(self.client.session.get('grade_autorizada', False))

    def test_admin_keeps_management_access(self):
        admin = get_user_model().objects.create_user('gestor', is_staff=True)
        self.client.force_login(admin)
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/api/alocacoes/').status_code, 200)

    def test_manifest_and_worker_are_public(self):
        self.client.logout()
        response = self.client.get(reverse('grade:mobile_manifest'))
        self.assertEqual(response.json()['start_url'], '/mobile/')
        self.assertEqual(len(response.json()['icons']), 2)
        self.assertEqual(self.client.get(reverse('grade:mobile_sw')).status_code, 200)
