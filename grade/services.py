"""Consulta e persistência da grade, usando as mesmas regras em todas as entradas."""
from django.core.exceptions import ValidationError
from django.db import transaction
from datetime import timedelta

from .models import Professor, AlocacaoGrade, Disponibilidade
from .restricoes import MotorRestricoes, segunda_da_semana


class GradeServiceError(ValidationError):
    """Erro de negócio que pode ser exibido na montagem manual."""


class AlocacaoService:
    @staticmethod
    def obter_dicionarios_de_visualizacao(data_alvo):
        disponibilidades = Disponibilidade.objects.filter(data=data_alvo)
        disp_manha = {pk: True for pk in Professor.objects.values_list('pk', flat=True)}
        disp_tarde = dict(disp_manha)
        for d in disponibilidades:
            disp_manha[d.professor_id] = disp_manha[d.professor_id] and d.disponivel_manha
            disp_tarde[d.professor_id] = disp_tarde[d.professor_id] and d.disponivel_tarde
        alocacoes_salvas = {}
        for aloc in AlocacaoGrade.objects.filter(data=data_alvo):
            alocacoes_salvas.setdefault(aloc.horario_id, {})[aloc.unidade_id] = aloc.professor_id
        return disp_manha, disp_tarde, alocacoes_salvas


class GradeService:
    @staticmethod
    def verificar_limite_aulas_diarias(professor_id, data, limite_maximo):
        if AlocacaoGrade.objects.filter(professor_id=professor_id, data=data).count() >= limite_maximo:
            raise GradeServiceError(f'O professor atingiu o limite de {limite_maximo} aulas em {data}.')

    @staticmethod
    def verificar_conflito_horario(professor_id, data, horario_id):
        motor = MotorRestricoes()
        horario = motor.horarios[horario_id]
        for existente in AlocacaoGrade.objects.filter(professor_id=professor_id, data=data).select_related('horario'):
            if (horario.hora_inicio < existente.horario.hora_fim
                    and existente.horario.hora_inicio < horario.hora_fim):
                raise GradeServiceError('O professor já está alocado em um horário sobreposto.')

    @staticmethod
    def verificar_deslocamento_e_transporte(professor, alocacoes_do_dia, nova_alocacao):
        motor = MotorRestricoes()
        for outra in alocacoes_do_dia:
            if outra.professor_id == professor.pk:
                motivo = motor.motivo_conflito(outra, nova_alocacao)
                if motivo:
                    raise GradeServiceError(motivo)

    @staticmethod
    def verificar_parente_vinculado(professor, unidade_id, turno_atual, alocacoes_do_dia_geral):
        # Compatibilidade: a preferência agora vale simetricamente no dia inteiro.
        avisos = MotorRestricoes().avisos_parentesco(alocacoes_do_dia_geral)
        return '\n'.join(avisos) or None

    @staticmethod
    @transaction.atomic
    def salvar_grade_diaria(data_alvo, post_data, professores, horarios, unidades):
        """Valida a proposta inteira ANTES de alterar a grade ou disponibilidade.

        As células mantidas preservam ID, auditoria e vínculos com turma/demanda.
        A tabela legada não representa esses vínculos; por isso, não pode remover
        ou trocar o professor de uma aula vinculada à automação.
        """
        professores, horarios, unidades = list(professores), list(horarios), list(unidades)
        list(Professor.objects.select_for_update().order_by('pk'))
        anteriores = list(AlocacaoGrade.objects.select_for_update().filter(data=data_alvo))
        existentes = {}
        for a in anteriores:
            chave = (a.horario_id, a.unidade_id)
            if chave in existentes:
                raise GradeServiceError('Há aulas simultâneas no dia. Use o editor do quadro por turma/sala; a tabela manual antiga não pode substituir esses registros.')
            existentes[chave] = a
        disponibilidade_proposta = {
            (p.pk, data_alvo): (
                post_data.get(f'disp_manha_{p.pk}') == 'on',
                post_data.get(f'disp_tarde_{p.pk}') == 'on',
            ) for p in professores
        }
        permitidos = {p.pk for p in professores}
        propostas, mantidos = [], set()
        for horario in horarios:
            for unidade in unidades:
                valor = post_data.get(f'alocacao_{horario.pk}_{unidade.pk}')
                try:
                    professor_id = int(valor) if valor else None
                except (TypeError, ValueError):
                    raise GradeServiceError('Selecione um professor válido em cada aula.')
                if professor_id is not None and professor_id not in permitidos:
                    raise GradeServiceError('Professor inexistente ou fora do cadastro consultado. Atualize a página.')
                anterior = existentes.get((horario.pk, unidade.pk))
                if anterior and anterior.professor_id == professor_id:
                    propostas.append(anterior)
                    mantidos.add(anterior.pk)
                elif professor_id:
                    propostas.append(AlocacaoGrade(
                        data=data_alvo, horario=horario, unidade=unidade, professor_id=professor_id,
                    ))
        for anterior in anteriores:
            if (anterior.pk not in mantidos
                    and (anterior.demanda_id or anterior.turma_id or anterior.disciplina_id)):
                raise GradeServiceError(
                    'Uma aula vinculada a turma, disciplina ou demanda não pode ser alterada '
                    'pela tabela manual. Use a administração para editar essa aula preservando '
                    'seus vínculos. Nenhuma alteração foi salva.'
                )
        inicio = segunda_da_semana(data_alvo)
        outras = list(AlocacaoGrade.objects.filter(
            data__gte=inicio, data__lt=inicio + timedelta(days=7),
        ).exclude(data=data_alvo))
        try:
            avisos = MotorRestricoes(disponibilidades=disponibilidade_proposta).validar(outras + propostas)
        except ValidationError as exc:
            raise GradeServiceError(exc.messages) from exc
        # Apenas depois da validação, efetiva todas as mudanças na mesma transação.
        for professor in professores:
            manha, tarde = disponibilidade_proposta[(professor.pk, data_alvo)]
            atualizados = Disponibilidade.objects.filter(
                data=data_alvo, professor=professor,
            ).update(disponivel_manha=manha, disponivel_tarde=tarde)
            if not atualizados:
                Disponibilidade.objects.create(
                    data=data_alvo, professor=professor,
                    disponivel_manha=manha, disponivel_tarde=tarde,
                )
        AlocacaoGrade.objects.filter(data=data_alvo).exclude(pk__in=mantidos).delete()
        AlocacaoGrade.objects.bulk_create([a for a in propostas if a.pk is None])
        return avisos
