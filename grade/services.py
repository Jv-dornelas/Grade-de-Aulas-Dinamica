# grade/services.py
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import datetime, time
from .models import Professor, AlocacaoGrade, Disponibilidade, MatrizDistancia

class GradeServiceError(ValidationError):
    """Exceção customizada para erros de validação de regras de negócio da grade."""
    pass


class AlocacaoService:
    """Serviço para recuperar e formatar dados de alocações e disponibilidades para exibição."""
    
    @staticmethod
    def obter_dicionarios_de_visualizacao(data_alvo):
        """
        Retorna três dicionários formatados para uso no template:
        - disp_manha: {professor_id: True/False}
        - disp_tarde: {professor_id: True/False}
        - alocacoes_salvas: {horario_id: {unidade_id: professor_id}}
        """
        disponibilidades = Disponibilidade.objects.filter(data=data_alvo)
        disp_manha = {d.professor.id: d.disponivel_manha for d in disponibilidades}
        disp_tarde = {d.professor.id: d.disponivel_tarde for d in disponibilidades}

        alocacoes = AlocacaoGrade.objects.filter(data=data_alvo)
        alocacoes_salvas = {}
        for aloc in alocacoes:
            if aloc.horario.id not in alocacoes_salvas:
                alocacoes_salvas[aloc.horario.id] = {}
            alocacoes_salvas[aloc.horario.id][aloc.unidade.id] = aloc.professor.id

        return disp_manha, disp_tarde, alocacoes_salvas


class GradeService:

    @staticmethod
    def verificar_limite_aulas_diarias(professor_id, data, limite_maximo):
        """
        REGRA: Validar se o professor ultrapassa o 'limite_aulas' cadastrado no dia.
        """
        aulas_existentes = AlocacaoGrade.objects.filter(
            professor_id=professor_id,
            data=data
        ).count()

        if aulas_existentes >= limite_maximo:
            raise GradeServiceError(
                f"O professor atingiu o limite máximo de {limite_maximo} aulas para o dia {data}."
            )

    @staticmethod
    def verificar_conflito_horario(professor_id, data, horario_id):
        """
        REGRA: Professor não pode estar em dois lugares (unidades) no mesmo horário/data.
        """
        conflito = AlocacaoGrade.objects.filter(
            professor_id=professor_id,
            data=data,
            horario_id=horario_id
        ).exists()

        if conflito:
            raise GradeServiceError(
                "O professor já está alocado em outra unidade neste mesmo horário."
            )

    @staticmethod
    def verificar_deslocamento_e_transporte(professor, alocacoes_do_dia, nova_alocacao):
        """
        REGRA: Valida o tempo de deslocamento entre unidades vizinhas ou distantes,
        considerando o intervalo entre as aulas e o meio de transporte do professor.
        """
        # Ordena as alocações do dia do professor pelo ID do horário ou ordem de início
        # (Assumindo que os horários seguem uma ordem cronológica)
        alocacoes_ordenadas = sorted(alocacoes_do_dia, key=lambda x: x.horario.hora_inicio)
        alocacoes_ordenadas.append(nova_alocacao)
        
        # Re-ordena para garantir a sequência correta do dia
        alocacoes_ordenadas.sort(key=lambda x: x.horario.hora_inicio)

        for i in range(len(alocacoes_ordenadas) - 1):
            atual = alocacoes_ordenadas[i]
            proxima = alocacoes_ordenadas[i+1]

            # Se mudou de unidade entre uma aula e a imediatamente seguinte
            if atual.unidade != proxima.unidade:
                # Consulta a Matriz de Distância cadastrada no banco
                matriz = MatrizDistancia.objects.filter(
                    origem=atual.unidade,
                    destino=proxima.unidade
                ).first()

                tempo_deslocamento = matriz.tempo_minutos if matriz else 30 # Padrão de 30 min se não achar

                # Calcula a diferença de tempo entre o fim da aula atual e o início da próxima
                fim_atual = datetime.combine(datetime.today(), atual.horario.hora_fim)
                inicio_proxima = datetime.combine(datetime.today(), proxima.horario.hora_inicio)
                diferenca_minutos = (inicio_proxima - fim_atual).total_seconds() / 60

                if diferenca_minutos < 0:
                    raise GradeServiceError(f"Conflito crítico: Horários sobrepostos entre {atual.unidade.nome} e {proxima.unidade.nome}.")

                # Se o intervalo for menor que o tempo de deslocamento necessário
                if diferenca_minutos < tempo_deslocamento:
                    # Verifica restrição de transporte público / a pé
                    if professor.meio_de_transporte == 'PUBLICO' or professor.meio_de_transporte == 'OUTRO':
                        raise GradeServiceError(
                            f"Tempo insuficiente ({int(diferenca_minutos)} min) para deslocamento de "
                            f"{atual.unidade.nome} para {proxima.unidade.nome} usando {professor.get_meio_de_transporte_display()}."
                        )

    @staticmethod
    def verificar_parente_vinculado(professor, unidade_id, turno_atual, alocacoes_do_dia_geral):
        """
        REGRA: Professores relacionados por parentesco devem estar no mesmo turno/unidade.
        Retorna um alerta (não bloqueia, mas sinaliza) ou pode gerar exceção dependendo do rigor.
        """
        if not professor.parente_vinculado:
            return None

        parente = professor.parente_vinculado
        # Procura se o parente tem aula alocada no mesmo dia
        alocacao_parente = next((a for a in alocacoes_do_dia_geral if a.professor == parente), None)

        if alocacao_parente:
            if alocacao_parente.unidade_id != unidade_id:
                return f"Atenção: O(a) professor(a) {professor.nome} está em unidade diferente do seu parente vinculado ({parente.nome})."
        
        return None

    @staticmethod
    @transaction.atomic
    def salvar_grade_diaria(data_alvo, post_data, professores, horarios, unidades):
        """
        Serviço principal que valida e persiste as alocações e disponibilidades de forma segura.
        """
        # 1. Salvar Disponibilidades
        Disponibilidade.objects.filter(data=data_alvo).delete()
        disponibilidades_para_criar = []
        
        for prof in professores:
            manha = post_data.get(f"disp_manha_{prof.id}") == "on"
            tarde = post_data.get(f"disp_tarde_{prof.id}") == "on"
            disponibilidades_para_criar.append(Disponibilidade(
                data=data_alvo, professor=prof, disponivel_manha=manha, disponivel_tarde=tarde
            ))
        Disponibilidade.objects.bulk_create(disponibilidades_para_criar)

        # 2. Salvar e Validar Alocações
        AlocacaoGrade.objects.filter(data=data_alvo).delete()
        alocacoes_para_criar = []
        
        # Dicionário auxiliar para controlar contagem de aulas por professor no dia
        aulas_por_prof_contador = {}

        for horario in horarios:
            for unidade in unidades:
                campo_name = f"alocacao_{horario.id}_{unidade.id}"
                professor_id = post_data.get(campo_name)
                
                if professor_id:
                    professor_id = int(professor_id)
                    professor = Professor.objects.get(id=professor_id)

                    # Validação 1: Conflito direto no mesmo horário
                    if AlocacaoGrade.objects.filter(data=data_alvo, horario=horario, professor_id=professor_id).exists():
                        raise GradeServiceError(f"O professor {professor.nome} já está alocado em outro local no horário {horario.nome}.")

                    # Validação 2: Limite de aulas diárias
                    aulas_por_prof_contador[professor_id] = aulas_por_prof_contador.get(professor_id, 0) + 1
                    if aulas_por_prof_contador[professor_id] > professor.limite_aulas:
                        raise GradeServiceError(f"O professor {professor.nome} excedeu o limite de {professor.limite_aulas} aulas diárias.")

                    alocacoes_para_criar.append(AlocacaoGrade(
                        data=data_alvo,
                        horario=horario,
                        unidade=unidade,
                        professor=professor
                    ))

        AlocacaoGrade.objects.bulk_create(alocacoes_para_criar)
        return True
