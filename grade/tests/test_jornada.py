from datetime import date, time, datetime
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from ..jornada import horarios_padrao, jornada, obter_horarios_padrao
from ..models import (AlocacaoGrade, Disponibilidade, DisponibilidadeHorario,
                     HorarioAula, MatrizDistancia, Professor, Turma, Unidade)
from ..restricoes import MotorRestricoes
from ..serializers import HorarioAulaSerializer


@override_settings(GRADE_AULAS_POR_TURNO=4)
class JornadaTests(TestCase):
    def setUp(self):
        self.dia = date(2026, 9, 21)
        self.escola = Unidade.objects.create(nome='Centro', responsavel='Gestor')
        self.outra = Unidade.objects.create(nome='Norte', responsavel='Gestor')
        self.prof = Professor.objects.create(nome='Ana', unidade_oficial=self.escola)
        self.prof.unidades_permitidas.add(self.outra)
        Disponibilidade.objects.create(data=self.dia, professor=self.prof,
                                        disponivel_manha=True, disponivel_tarde=True)

    def aula(self, horario, escola=None):
        return AlocacaoGrade(data=self.dia, horario=horario, professor=self.prof,
                             unidade=escola or self.escola)

    def test_blocos_consecutivos_50_minutos_com_almoco_de_uma_hora(self):
        padrao = horarios_padrao()
        self.assertEqual(len(padrao), 8)
        self.assertEqual([inicio.strftime('%H:%M') for _, inicio, _ in padrao],
                         ['08:00', '08:50', '09:40', '10:30', '12:20', '13:10', '14:00', '14:50'])
        self.assertEqual(padrao[-1][2], time(15, 40))
        for _, inicio, fim in padrao:
            self.assertEqual((datetime.combine(self.dia, fim) - datetime.combine(self.dia, inicio)).seconds, 3000)
        self.assertEqual(jornada()['fim_manha'], time(11, 20))
        for i in (0, 1, 2, 4, 5, 6):
            self.assertEqual(padrao[i][2], padrao[i + 1][1])

    @override_settings(GRADE_AULAS_POR_TURNO=5)
    def test_cinco_aulas_mantem_50_minutos_e_uma_hora_de_almoco(self):
        self.assertEqual(len(horarios_padrao()), 10)
        self.assertEqual(jornada()['fim_manha'], time(12, 10))
        self.assertEqual(jornada()['inicio_tarde'], time(13, 10))
        self.assertEqual(jornada()['fim_tarde'], time(17, 20))

    def test_intervalo_almoco_conta_para_deslocamento_sem_somar_outra_hora(self):
        horarios = obter_horarios_padrao()
        rota = MatrizDistancia.objects.create(origem=self.escola, destino=self.outra, tempo_minutos=60)
        aulas = [self.aula(horarios[3]), self.aula(horarios[4], self.outra)]
        self.assertEqual(MotorRestricoes().validar(aulas), [])
        rota.tempo_minutos = 61
        rota.save()
        with self.assertRaisesMessage(ValidationError, 'Tempo insuficiente'):
            MotorRestricoes().validar(aulas)

    def test_aulas_seguidas_mesma_escola_ok_mudanca_exige_tempo(self):
        horarios = obter_horarios_padrao()
        MatrizDistancia.objects.create(origem=self.escola, destino=self.outra, tempo_minutos=1)
        self.assertEqual(MotorRestricoes().validar([self.aula(horarios[0]), self.aula(horarios[1])]), [])
        with self.assertRaisesMessage(ValidationError, 'Tempo insuficiente'):
            MotorRestricoes().validar([self.aula(horarios[0]), self.aula(horarios[1], self.outra)])

    def test_almoco_bloqueado_mesmo_com_disponibilidade_especifica(self):
        for inicio, fim in ((time(11, 20), time(12, 10)), (time(11), time(11, 50)), (time(12), time(12, 50))):
            horario = HorarioAula.objects.create(nome='Invade almoço', hora_inicio=inicio, hora_fim=fim)
            DisponibilidadeHorario.objects.create(data=self.dia, professor=self.prof, horario=horario, disponivel=True)
            with self.assertRaisesMessage(ValidationError, 'intervalo de uma hora de almoço'):
                MotorRestricoes().validar([self.aula(horario)])

    def test_primeira_aula_da_tarde_usa_disponibilidade_tarde(self):
        horarios = obter_horarios_padrao()
        Disponibilidade.objects.update(disponivel_manha=False, disponivel_tarde=True)
        motor = MotorRestricoes()
        self.assertFalse(motor.disponivel(self.prof.pk, self.dia, horarios[0].pk))
        self.assertTrue(motor.disponivel(self.prof.pk, self.dia, horarios[4].pk))

    def test_reutilizar_horarios_nao_duplica_e_admin_api_rejeitam_duplicado(self):
        horarios = obter_horarios_padrao()
        self.assertEqual([h.pk for h in horarios], [h.pk for h in obter_horarios_padrao()])
        duplicado = HorarioAula(nome='Outro nome', hora_inicio=time(8), hora_fim=time(8, 50))
        with self.assertRaisesMessage(ValidationError, 'Já existe um horário'):
            duplicado.full_clean()
        serializer = HorarioAulaSerializer(data={'nome': 'Duplicado', 'hora_inicio': '08:00', 'hora_fim': '08:50'})
        self.assertFalse(serializer.is_valid())

    def normalizar(self):
        call_command('normalizar_horarios', stdout=StringIO())

    def test_corrigir_demo_transfere_aula_e_turma_sem_perder_ids(self):
        oficial = HorarioAula.objects.create(nome='Primeira', hora_inicio=time(8), hora_fim=time(8, 50))
        HorarioAula.objects.create(nome='[DEMO] Aula 1', hora_inicio=time(8), hora_fim=time(8, 50))
        errado = HorarioAula.objects.create(nome='[DEMO] Aula 2', hora_inicio=time(9), hora_fim=time(9, 50))
        turma = Turma.objects.create(materias_fixas=False, nome='6A', unidade=self.escola)
        turma.horarios.add(errado)
        aula = self.aula(errado)
        aula.save()
        self.normalizar()
        aula.refresh_from_db()
        self.assertEqual(aula.horario.hora_inicio, time(8, 50))
        self.assertEqual(list(turma.horarios.values_list('pk', flat=True)), [aula.horario_id])
        self.assertTrue(HorarioAula.objects.filter(pk=oficial.pk).exists())
        self.assertEqual(HorarioAula.objects.count(), 8)
        self.assertEqual(AlocacaoGrade.objects.count(), 1)
        self.normalizar()
        self.assertEqual(HorarioAula.objects.count(), 8)

    def test_disponibilidade_duplicada_preserva_resposta_mais_restritiva(self):
        a = HorarioAula.objects.create(nome='Primeira', hora_inicio=time(8), hora_fim=time(8, 50))
        b = HorarioAula.objects.create(nome='[DEMO] Aula 1', hora_inicio=time(8), hora_fim=time(8, 50))
        for h, livre in ((a, True), (b, False)):
            DisponibilidadeHorario.objects.create(data=self.dia, professor=self.prof, horario=h, disponivel=livre)
        self.normalizar()
        self.assertEqual(DisponibilidadeHorario.objects.count(), 1)
        self.assertFalse(DisponibilidadeHorario.objects.get().disponivel)

    def test_conflito_apos_consolidacao_desfaz_todas_as_mudancas(self):
        a = HorarioAula.objects.create(nome='Primeira', hora_inicio=time(8), hora_fim=time(8, 50))
        b = HorarioAula.objects.create(nome='[DEMO] Aula 1', hora_inicio=time(8), hora_fim=time(8, 50))
        self.aula(a).save()
        self.aula(b).save()
        with self.assertRaises(CommandError):
            self.normalizar()
        self.assertEqual(HorarioAula.objects.count(), 2)
        self.assertEqual(set(AlocacaoGrade.objects.values_list('horario_id', flat=True)), {a.pk, b.pk})

    def test_horario_desconhecido_nao_e_apagado(self):
        HorarioAula.objects.create(nome='Noturno', hora_inicio=time(18), hora_fim=time(19))
        with self.assertRaisesMessage(CommandError, 'Horário fora do padrão'):
            self.normalizar()
        self.assertEqual(HorarioAula.objects.count(), 1)
