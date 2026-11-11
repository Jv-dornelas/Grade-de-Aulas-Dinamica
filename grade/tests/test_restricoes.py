"""Regressões de regras, atomicidade e entradas manual/API/admin.

Os registros são criados apenas no banco temporário do Django TestCase.
"""
from datetime import date, time, timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from ..models import (
    AlocacaoGrade, DemandaAula, Disciplina, Disponibilidade,
    DisponibilidadeHorario, HorarioAula, MatrizDistancia, Professor, Turma, Unidade,
)
from ..restricoes import MotorRestricoes, validar_alocacao_individual
from ..services import GradeService, GradeServiceError


class RestricoesGradeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.segunda = date(2026, 9, 21)
        cls.terca = cls.segunda + timedelta(days=1)
        cls.proxima = cls.segunda + timedelta(days=7)
        cls.admin = get_user_model().objects.create_superuser('gestor-regras', password='teste-regras-42')
        cls.escola = Unidade.objects.create(nome='Escola A', responsavel='Coordenação')
        cls.outra = Unidade.objects.create(nome='Escola B', responsavel='Coordenação')
        cls.distante = Unidade.objects.create(nome='Escola C', responsavel='Coordenação')
        cls.disciplina = Disciplina.objects.create(nome='Matemática', area='EXATAS')
        cls.outra_disciplina = Disciplina.objects.create(nome='Português', area='HUMANAS')
        cls.prof = Professor.objects.create(nome='Ana', unidade_oficial=cls.escola, limite_aulas=3)
        cls.parente = Professor.objects.create(nome='Bia', unidade_oficial=cls.outra, limite_aulas=3)
        for prof in (cls.prof, cls.parente):
            prof.unidades_permitidas.add(cls.escola, cls.outra, cls.distante)
            prof.disciplinas.add(cls.disciplina)
            for data in (cls.segunda, cls.terca, cls.proxima):
                Disponibilidade.objects.create(
                    professor=prof, data=data, disponivel_manha=True, disponivel_tarde=True,
                )
        cls.h1 = HorarioAula.objects.create(nome='08h', hora_inicio=time(8), hora_fim=time(9))
        cls.h2 = HorarioAula.objects.create(nome='09h10', hora_inicio=time(9, 10), hora_fim=time(10))
        cls.h3 = HorarioAula.objects.create(nome='10h', hora_inicio=time(10), hora_fim=time(11))
        cls.sobreposto = HorarioAula.objects.create(nome='08h30', hora_inicio=time(8, 30), hora_fim=time(9, 30))
        cls.tarde = HorarioAula.objects.create(nome='13h', hora_inicio=time(13), hora_fim=time(14))
        cls.cruzado = HorarioAula.objects.create(nome='12h30', hora_inicio=time(12, 30), hora_fim=time(13, 30))
        cls.turma = Turma.objects.create(materias_fixas=False, nome='6º A', unidade=cls.escola, dias_semana=[0, 1, 2, 3, 4])
        cls.turma.horarios.add(cls.h1, cls.h2, cls.h3)
        cls.demanda = DemandaAula.objects.create(
            turma=cls.turma, disciplina=cls.disciplina, quantidade_semana=2,
        )

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def aula(self, **mudancas):
        dados = dict(data=self.segunda, horario=self.h1, unidade=self.escola, professor=self.prof)
        dados.update(mudancas)
        return AlocacaoGrade(**dados)

    def aula_demanda(self, **mudancas):
        dados = dict(turma=self.turma, disciplina=self.disciplina, demanda=self.demanda)
        dados.update(mudancas)
        return self.aula(**dados)

    def salvar_manual(self, dados):
        return GradeService.salvar_grade_diaria(
            self.segunda, dados, Professor.objects.all(), HorarioAula.objects.all(), Unidade.objects.all(),
        )

    def dados_manuais(self, *aulas):
        dados = {f'disp_{turno}_{prof.pk}': 'on'
                 for prof in (self.prof, self.parente) for turno in ('manha', 'tarde')}
        for aula in aulas:
            dados[f'alocacao_{aula.horario_id}_{aula.unidade_id}'] = str(aula.professor_id)
        return dados

    def dados_api(self, **mudancas):
        dados = dict(data=self.segunda.isoformat(), horario=self.h1.pk,
                     unidade=self.escola.pk, professor=self.prof.pk)
        dados.update(mudancas)
        return dados

    def cadastrar_rota(self, origem=None, destino=None, minutos=15):
        return MatrizDistancia.objects.create(
            origem=origem or self.escola, destino=destino or self.outra, tempo_minutos=minutos,
        )

    def test_disponivel_por_padrao_e_janela_especifica_tem_prioridade(self):
        sem_cadastro = self.segunda + timedelta(days=2)
        self.assertEqual(MotorRestricoes().validar([self.aula(data=sem_cadastro)]), [])
        Disponibilidade.objects.create(professor=self.prof, data=sem_cadastro,
                                       disponivel_manha=False, disponivel_tarde=False)
        with self.assertRaisesMessage(ValidationError, 'sem disponibilidade'):
            MotorRestricoes().validar([self.aula(data=sem_cadastro)])
        regra = DisponibilidadeHorario.objects.create(
            professor=self.prof, data=sem_cadastro, horario=self.h1, disponivel=True,
        )
        self.assertEqual(MotorRestricoes().validar([self.aula(data=sem_cadastro)]), [])
        regra.data = self.segunda
        regra.disponivel = False
        regra.save()
        with self.assertRaisesMessage(ValidationError, 'sem disponibilidade'):
            MotorRestricoes().validar([self.aula()])

    def test_disponibilidade_da_tarde_nao_depende_da_manha(self):
        Disponibilidade.objects.filter(professor=self.prof).update(disponivel_tarde=False)
        motor = MotorRestricoes()
        self.assertTrue(motor.disponivel(self.prof.pk, self.segunda, self.h1.pk))
        self.assertFalse(motor.disponivel(self.prof.pk, self.segunda, self.tarde.pk))
        self.assertFalse(motor.disponivel(self.prof.pk, self.segunda, self.cruzado.pk))
        Disponibilidade.objects.filter(professor=self.prof).update(disponivel_tarde=True)
        self.assertTrue(MotorRestricoes().disponivel(self.prof.pk, self.segunda, self.cruzado.pk))

    def test_sobreposicao_real_independe_do_id_do_horario(self):
        with self.assertRaisesMessage(ValidationError, 'Professor com aulas sobrepostas'):
            MotorRestricoes().validar([self.aula(), self.aula(horario=self.sobreposto, unidade=self.outra)])

    def test_escola_so_recebe_uma_aula_por_intervalo_na_grade_atual(self):
        with self.assertRaisesMessage(ValidationError, 'escola já possui uma aula'):
            MotorRestricoes().validar([self.aula(), self.aula(professor=self.parente, horario=self.sobreposto)])

    def test_horarios_encostados_mesma_escola_e_dias_distintos_sao_validos(self):
        self.assertEqual(MotorRestricoes().validar([
            self.aula(horario=self.h2), self.aula(horario=self.h3), self.aula(data=self.terca),
        ]), [])

    def test_deslocamento_insuficiente_bloqueia_inclusive_carro(self):
        self.cadastrar_rota(minutos=40)
        for transporte in ('PARTICULAR', 'PUBLICO', 'OUTRO'):
            with self.subTest(transporte=transporte):
                self.prof.meio_de_transporte = transporte
                self.prof.save()
                with self.assertRaisesMessage(ValidationError, 'Tempo insuficiente de deslocamento'):
                    MotorRestricoes().validar([self.aula(), self.aula(horario=self.h2, unidade=self.outra)])

    def test_rota_ausente_nao_usa_valor_inventado_nem_trajeto_inverso(self):
        self.cadastrar_rota(origem=self.outra, destino=self.escola, minutos=5)
        with self.assertRaisesMessage(ValidationError, 'Falta cadastrar o tempo de deslocamento'):
            MotorRestricoes().validar([self.aula(), self.aula(horario=self.h2, unidade=self.outra)])

    def test_rota_duplicada_escolhe_tempo_mais_conservador(self):
        self.cadastrar_rota(minutos=5)
        self.cadastrar_rota(minutos=40)
        motor = MotorRestricoes()
        self.assertEqual(motor.tempo(self.escola.pk, self.outra.pk), 40)
        with self.assertRaisesMessage(ValidationError, 'Tempo insuficiente'):
            motor.validar([self.aula(), self.aula(horario=self.h2, unidade=self.outra)])

    def test_unidade_oficial_ou_permitida_e_obrigatoria(self):
        self.prof.unidades_permitidas.clear()
        self.assertEqual(MotorRestricoes().validar([self.aula()]), [])
        with self.assertRaisesMessage(ValidationError, 'fora das unidades permitidas'):
            MotorRestricoes().validar([self.aula(unidade=self.outra)])
        self.prof.unidade_oficial = None
        self.prof.save()
        with self.assertRaisesMessage(ValidationError, 'fora das unidades permitidas'):
            MotorRestricoes().validar([self.aula()])

    def test_limite_diario_considera_todas_as_aulas_do_lote(self):
        self.prof.limite_aulas = 1
        self.prof.save()
        with self.assertRaisesMessage(ValidationError, 'excedeu o limite de 1 aulas'):
            MotorRestricoes().validar([self.aula(), self.aula(horario=self.h2)])

    def test_horario_invertido_nao_passa_no_motor(self):
        self.h1.hora_fim = time(7)
        self.h1.save()
        with self.assertRaisesMessage(ValidationError, 'fim da aula deve ser posterior'):
            MotorRestricoes().validar([self.aula()])

    def test_disciplina_e_dados_da_demanda_precisam_ser_coerentes(self):
        with self.assertRaisesMessage(ValidationError, 'não habilitado'):
            MotorRestricoes().validar([self.aula(disciplina=self.outra_disciplina)])
        with self.assertRaisesMessage(ValidationError, 'incompatíveis com a demanda'):
            MotorRestricoes().validar([self.aula(demanda=self.demanda)])
        self.demanda.professor = self.parente
        self.demanda.save()
        with self.assertRaisesMessage(ValidationError, 'incompatíveis com a demanda'):
            MotorRestricoes().validar([self.aula_demanda()])

    def test_turma_respeita_escola_dias_e_horarios_cadastrados(self):
        self.turma.dias_semana = [1]
        self.turma.save()
        with self.assertRaisesMessage(ValidationError, 'dias ou horários cadastrados'):
            MotorRestricoes().validar([self.aula_demanda()])
        with self.assertRaisesMessage(ValidationError, 'dias ou horários cadastrados'):
            MotorRestricoes().validar([self.aula_demanda(data=self.terca, unidade=self.outra)])
        with self.assertRaisesMessage(ValidationError, 'dias ou horários cadastrados'):
            MotorRestricoes().validar([self.aula_demanda(data=self.terca, horario=self.tarde)])

    def test_demanda_tem_teto_por_semana_e_nao_soma_semanas_diferentes(self):
        self.demanda.quantidade_semana = 1
        self.demanda.save()
        with self.assertRaisesMessage(ValidationError, 'excede as 1 aulas cadastradas'):
            MotorRestricoes().validar([self.aula_demanda(), self.aula_demanda(data=self.terca)])
        self.assertEqual(MotorRestricoes().validar([self.aula_demanda(), self.aula_demanda(data=self.proxima)]), [])

    def test_parentesco_unilateral_avisa_ambos_mesmo_em_turnos_distintos(self):
        self.parente.parente_vinculado = self.prof
        self.parente.save()
        aulas = [self.aula(), self.aula(professor=self.parente, unidade=self.outra, horario=self.tarde)]
        avisos = MotorRestricoes().validar(aulas)
        self.assertEqual(len(avisos), 1)
        self.assertIn('Ana e Bia', avisos[0])
        self.assertIn('durante todo o dia', avisos[0])
        self.prof.parente_vinculado = self.parente
        self.prof.save()
        self.parente.parente_vinculado = None
        self.parente.save()
        self.assertEqual(MotorRestricoes().validar(aulas), avisos)
        self.assertEqual(MotorRestricoes().validar([aulas[0]]), [])

    def test_parentesco_proximidade_precisa_dos_dois_sentidos(self):
        self.prof.parente_vinculado = self.parente
        self.prof.save()
        aulas = [self.aula(), self.aula(professor=self.parente, unidade=self.outra)]
        self.cadastrar_rota(minutos=10)
        self.assertEqual(len(MotorRestricoes().validar(aulas, proximidade=15)), 1)
        retorno = self.cadastrar_rota(origem=self.outra, destino=self.escola, minutos=20)
        self.assertEqual(len(MotorRestricoes().validar(aulas, proximidade=15)), 1)
        retorno.tempo_minutos = 15
        retorno.save()
        self.assertEqual(MotorRestricoes().validar(aulas, proximidade=15), [])

    def test_distancia_nao_define_vinculo_familiar_ou_conjugal(self):
        aulas=[self.aula(),self.aula(professor=self.parente,unidade=self.outra)]
        self.assertEqual(MotorRestricoes().validar(aulas),[])
        self.prof.parente_vinculado=self.parente
        self.prof.save()
        avisos=MotorRestricoes().validar(aulas)
        self.assertEqual(len(avisos),1)
        self.assertIn('vínculo familiar ou conjugal',avisos[0])
        self.assertIn('Ana e Bia',avisos[0])

    def test_parentesco_mudanca_de_escola_no_dia_tambem_e_avaliada(self):
        self.prof.parente_vinculado = self.parente
        self.prof.save()
        self.cadastrar_rota(minutos=5)
        self.cadastrar_rota(origem=self.outra, destino=self.escola, minutos=5)
        self.cadastrar_rota(origem=self.escola, destino=self.distante, minutos=30)
        aulas = [self.aula(), self.aula(professor=self.parente, unidade=self.outra),
                 self.aula(unidade=self.distante, horario=self.tarde)]
        self.assertEqual(len(MotorRestricoes().validar(aulas)), 1)

    def test_save_manual_invalido_preserva_grade_disponibilidade_e_ids(self):
        antiga = self.aula()
        antiga.save()
        antes = list(AlocacaoGrade.objects.values())
        disponibilidade_antes = list(Disponibilidade.objects.order_by('pk').values())
        post = self.dados_manuais(antiga, self.aula(unidade=self.outra))
        post.pop(f'disp_tarde_{self.parente.pk}')
        with self.assertRaisesMessage(GradeServiceError, 'Professor com aulas sobrepostas'):
            self.salvar_manual(post)
        self.assertEqual(list(AlocacaoGrade.objects.values()), antes)
        self.assertEqual(list(Disponibilidade.objects.order_by('pk').values()), disponibilidade_antes)

    def test_save_manual_valida_professor_e_nao_limpa_grade_em_post_invalido(self):
        antiga = self.aula()
        antiga.save()
        for valor in ('nao-e-id', '999999'):
            with self.subTest(valor=valor):
                post = self.dados_manuais(antiga)
                post[f'alocacao_{self.h1.pk}_{self.escola.pk}'] = valor
                with self.assertRaises(GradeServiceError):
                    self.salvar_manual(post)
                self.assertTrue(AlocacaoGrade.objects.filter(pk=antiga.pk).exists())

    def test_save_manual_sem_alterar_preserva_metadados_e_auditoria_da_demanda(self):
        antiga = self.aula_demanda()
        antiga.save()
        antes = list(AlocacaoGrade.objects.values())
        self.assertEqual(self.salvar_manual(self.dados_manuais(antiga)), [])
        self.assertEqual(list(AlocacaoGrade.objects.values()), antes)

    def test_save_manual_nao_apaga_nem_troca_aula_gerada(self):
        antiga = self.aula_demanda()
        antiga.save()
        antes = list(AlocacaoGrade.objects.values())
        for aulas in ([], [self.aula(professor=self.parente)]):
            with self.subTest(aulas=len(aulas)):
                post = self.dados_manuais(*aulas)
                post.pop(f'disp_manha_{self.prof.pk}')
                with self.assertRaisesMessage(GradeServiceError, 'não pode ser alterada pela tabela manual'):
                    self.salvar_manual(post)
                self.assertEqual(list(AlocacaoGrade.objects.values()), antes)
                self.assertTrue(Disponibilidade.objects.get(professor=self.prof, data=self.segunda).disponivel_manha)

    def test_api_rejeita_conflito_e_excecao_nao_o_contorna(self):
        self.aula().save()
        response = self.api.post('/api/alocacoes/', self.dados_api(
            unidade=self.outra.pk, eh_excecao_horario=True,
        ), format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('exceções não podem contornar', str(response.data))
        self.assertIn('Professor com aulas sobrepostas', str(response.data))
        self.assertEqual(AlocacaoGrade.objects.count(), 1)

    def test_api_criar_e_patch_mesmo_registro_valido_nao_conflita_consigo(self):
        response = self.api.post('/api/alocacoes/', self.dados_api(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        response = self.api.patch(f"/api/alocacoes/{response.data['id']}/", {
            'horario': self.h2.pk,
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(AlocacaoGrade.objects.get().horario_id, self.h2.pk)

    def test_api_limite_considera_aulas_ja_gravadas(self):
        self.prof.limite_aulas = 1
        self.prof.save()
        self.aula().save()
        response = self.api.post('/api/alocacoes/', self.dados_api(horario=self.h2.pk), format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('excedeu o limite', str(response.data))
        self.assertEqual(AlocacaoGrade.objects.count(), 1)

    def test_api_troca_semana_revalida_teto_da_demanda_e_preserva_original(self):
        self.demanda.quantidade_semana = 1
        self.demanda.save()
        self.aula_demanda().save()
        futura = self.aula_demanda(data=self.proxima, horario=self.h2)
        futura.save()
        response = self.api.patch(f'/api/alocacoes/{futura.pk}/', {
            'data': self.terca.isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('excede as 1 aulas cadastradas', str(response.data))
        futura.refresh_from_db()
        self.assertEqual(futura.data, self.proxima)

    def test_api_bloqueio_faz_rollback_e_remocao_retorna_ao_padrao_disponivel(self):
        self.aula().save()
        disponibilidade = Disponibilidade.objects.get(professor=self.prof, data=self.segunda)
        url = f'/api/disponibilidades/{disponibilidade.pk}/'
        response = self.api.patch(url, {'disponivel_manha': False}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        disponibilidade.refresh_from_db()
        self.assertTrue(disponibilidade.disponivel_manha)
        response = self.api.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Disponibilidade.objects.filter(pk=disponibilidade.pk).exists())
        self.assertTrue(MotorRestricoes().disponivel(self.prof.pk, self.segunda, self.h1.pk))

    def test_api_horario_nao_pode_criar_sobreposicao_em_grade_salva(self):
        self.aula().save()
        self.aula(horario=self.h2).save()
        response = self.api.patch(f'/api/horarios/{self.h2.pk}/', {
            'hora_inicio': '08:30:00',
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.h2.refresh_from_db()
        self.assertEqual(self.h2.hora_inicio, time(9, 10))

    def test_modelo_admin_rejeita_conflitos_antes_de_salvar(self):
        self.aula().save()
        request = RequestFactory().get('/admin/grade/alocacaograde/add/')
        request.user = self.admin
        form_class = admin.site._registry[AlocacaoGrade].get_form(request)
        form = form_class(data=self.dados_api(unidade=self.outra.pk))
        self.assertFalse(form.is_valid())
        self.assertIn('Professor com aulas sobrepostas', str(form.errors))
        self.assertEqual(AlocacaoGrade.objects.count(), 1)

    def test_revalidacao_individual_detecta_cadastro_alterado_apos_salvar(self):
        antiga = self.aula()
        antiga.save()
        self.prof.unidade_oficial = None
        self.prof.save()
        self.prof.unidades_permitidas.clear()
        with self.assertRaisesMessage(ValidationError, 'fora das unidades permitidas'):
            validar_alocacao_individual(antiga)

    def test_turma_disciplina_sem_demanda_nao_contorna_teto_semanal(self):
        with self.assertRaisesMessage(ValidationError, 'turma, disciplina e demanda juntas'):
            MotorRestricoes().validar([self.aula(turma=self.turma, disciplina=self.disciplina)])
        response = self.api.post('/api/alocacoes/', self.dados_api(
            turma=self.turma.pk, disciplina=self.disciplina.pk,
        ), format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(AlocacaoGrade.objects.count(), 0)

    def test_api_e_admin_nao_podem_desvincular_aula_para_contornar_demanda(self):
        antiga = self.aula_demanda()
        antiga.save()
        response = self.api.patch(f'/api/alocacoes/{antiga.pk}/', {
            'turma': None, 'disciplina': None, 'demanda': None,
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        antiga.refresh_from_db()
        self.assertEqual(antiga.demanda_id, self.demanda.pk)
        antiga.turma = antiga.disciplina = antiga.demanda = None
        with self.assertRaisesMessage(ValidationError, 'Não é permitido remover todos os vínculos'):
            antiga.full_clean()

    def test_demanda_inativa_preserva_aulas_existentes_mas_bloqueia_novas(self):
        antiga = self.aula_demanda()
        antiga.save()
        self.demanda.ativa = False
        self.demanda.save()
        self.assertEqual(MotorRestricoes().validar([antiga]), [])
        self.assertEqual(validar_alocacao_individual(antiga), [])
        with self.assertRaisesMessage(ValidationError, 'demanda inexistente ou inativa'):
            MotorRestricoes().validar([self.aula_demanda(data=self.terca)])
        # Um pk existente de aula legada não autoriza vincular uma demanda inativa.
        outra = self.aula(data=self.terca)
        outra.save()
        response = self.api.patch(f'/api/alocacoes/{outra.pk}/', {
            'turma': self.turma.pk, 'disciplina': self.disciplina.pk, 'demanda': self.demanda.pk,
        }, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        outra.refresh_from_db()
        self.assertIsNone(outra.demanda_id)
