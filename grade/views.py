from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from .models import Unidade, HorarioAula, Professor, AlocacaoGrade, Disponibilidade
from datetime import datetime
from .services import GradeService, GradeServiceError, AlocacaoService

@staff_member_required
def exibir_grade(request):

    # Carrega dados base
    unidades = Unidade.objects.all()
    horarios = HorarioAula.objects.all()
    professores = Professor.objects.all().order_by('nome')
    
    # Captura a data vinda da URL (?data=2026-04-25) ou do formulário POST. Se não houver, usa a padrão.
    data_str = request.GET.get('data') or request.POST.get('data_grade')
    
    if data_str:
        try:
            data_atual_projeto = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            data_atual_projeto = datetime.strptime('2026-04-25', '%Y-%m-%d').date()
    else:
        data_atual_projeto = datetime.strptime('2026-04-25', '%Y-%m-%d').date()
    
    sucesso = False
    erro_negocio = None

    # POST - Salvar dados usando a CAMADA DE SERVIÇO
    if request.method == 'POST' and "senha_acesso" not in request.POST:
        try:
            # Tenta salvar rodando as validações do serviço
            GradeService.salvar_grade_diaria(
                data_alvo=data_atual_projeto,
                post_data=request.POST,
                professores=professores,
                horarios=horarios,
                unidades=unidades
            )
            sucesso = True
            
        except GradeServiceError as e:
            # SE ALGUMA REGRA FALHAR: O Python cai aqui direto!
            # Vamos recarregar a tela passando a mensagem de erro que o serviço gerou.
            erro_negocio = str(e)

    # Buscar dados do dia selecionado
    disp_manha_salvas, disp_tarde_salvas, alocacoes_salvas = AlocacaoService.obter_dicionarios_de_visualizacao(data_atual_projeto)

    context = {
        'unidades': unidades,
        'horarios': horarios,
        'professores': professores,
        'data_grade': data_atual_projeto.strftime('%Y-%m-%d'), # Formato do input date (YYYY-MM-DD)
        'alocacoes_salvas': alocacoes_salvas,
        'disp_manha_salvas': disp_manha_salvas,
        'disp_tarde_salvas': disp_tarde_salvas,
        'sucesso': sucesso,
        'erro_negocio': erro_negocio,
    }
    
    return render(request, 'grade/grade_tabela.html', context)
