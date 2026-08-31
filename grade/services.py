# grade/services.py
from .models import Professor, AlocacaoGrade, MatrizDistancia

def verificar_limite_aulas_diarias(professor_id, data, quantidade_novas_aulas):
    """
    REGRA: Validar se o professor ultrapassa o 'limite_aulas' cadastrado no dia.
    TODO para a equipe: Buscar alocações do professor na data e somar com as novas aulas.
    """
    pass

def verificar_parente_vinculado(professor_id, horario_id, unidade_id, data):
    """
    REGRA: Se o professor tem 'parente_vinculado', garantir que ambos
    estejam alocados na mesma unidade no mesmo turno.
    TODO para a equipe: Checar a grade do parente no banco.
    """
    pass

def calcular_distancia_entre_unidades(unidade_origem_id, unidade_destino_id):
    """
    REGRA: Calcular e salvar na tabela MatrizDistancia com base no endereço.
    TODO para a equipe: Integrar com API de mapas ou mockar cálculo.
    """
    pass

def validar_alocacao(professor_id, horario_id, unidade_id, data):
    """
    Função principal que o DRF (api.py) vai chamar antes de salvar uma nova grade.
    Ela deve rodar todas as validações acima e retornar um erro amigável se algo falhar.
    """
    pass