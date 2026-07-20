from django.shortcuts import render, redirect
from .models import Unidade, HorarioAula, Professor, AlocacaoGrade, Disponibilidade
from datetime import datetime

def exibir_grade(request):
    SENHA_PROTECAO = "CCM_2026"  # Defina a senha que você preferir aqui
    
    # Se o usuário tentar logar pela tela de bloqueio
    if request.method == "POST" and "senha_acesso" in request.POST:
        senha_digitada = request.POST.get("senha_acesso")
        if senha_digitada == SENHA_PROTECAO:
            request.session["grade_autorizada"] = True
            return redirect(request.get_full_path())
        else:
            return render(request, "grade/login_grade.html", {"erro": "Senha incorreta! Tente novamente."})

    # Se o usuário não estiver autorizado, barra e manda para a tela de senha
    if not request.session.get("grade_autorizada"):
        return render(request, "grade/login_grade.html")

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

    if request.method == 'POST':
        # 1. Salvar as Disponibilidades da data selecionada
        Disponibilidade.objects.filter(data=data_atual_projeto).delete()
        for prof in professores:
            manha_marcada = request.POST.get(f"disp_manha_{prof.id}") == "on"
            tarde_marcada = request.POST.get(f"disp_tarde_{prof.id}") == "on"
            
            Disponibilidade.objects.create(
                data=data_atual_projeto,
                professor=prof,
                disponivel_manha=manha_marcada,
                disponivel_tarde=tarde_marcada
            )

        # 2. Salvar as Alocações da data selecionada
        AlocacaoGrade.objects.filter(data=data_atual_projeto).delete()
        for horario in horarios:
            for unidade in unidades:
                campo_name = f"alocacao_{horario.id}_{unidade.id}"
                professor_id = request.POST.get(campo_name)
                if professor_id:
                    professor = Professor.objects.get(id=professor_id)
                    AlocacaoGrade.objects.create(
                        data=data_atual_projeto,
                        horario=horario,
                        unidade=unidade,
                        professor=professor
                    )
        sucesso = True

    # Buscar dados do dia selecionado
    disponibilidades = Disponibilidade.objects.filter(data=data_atual_projeto)
    disp_manha_salvas = {d.professor.id: d.disponivel_manha for d in disponibilidades}
    disp_tarde_salvas = {d.professor.id: d.disponivel_tarde for d in disponibilidades}

    alocacoes = AlocacaoGrade.objects.filter(data=data_atual_projeto)
    alocacoes_salvas = {}
    for aloc in alocacoes:
        if aloc.horario.id not in alocacoes_salvas:
            alocacoes_salvas[aloc.horario.id] = {}
        alocacoes_salvas[aloc.horario.id][aloc.unidade.id] = aloc.professor.id

    context = {
        'unidades': unidades,
        'horarios': horarios,
        'professores': professores,
        'data_grade': data_atual_projeto.strftime('%Y-%m-%d'), # Formato do input date (YYYY-MM-DD)
        'alocacoes_salvas': alocacoes_salvas,
        'disp_manha_salvas': disp_manha_salvas,
        'disp_tarde_salvas': disp_tarde_salvas,
        'sucesso': sucesso,
    }
    
    return render(request, 'grade/grade_tabela.html', context)