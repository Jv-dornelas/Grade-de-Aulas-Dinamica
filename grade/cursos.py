from datetime import timedelta
from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Curso, MatrizCurricular, Turma, Disciplina, AlocacaoGrade, Professor, Unidade
from .forms_cursos import TurmaForm


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['nome', 'observacoes']


MatrizFormSet = inlineformset_factory(Curso, MatrizCurricular,
    fields=['disciplina', 'quantidade_semana'], extra=3, can_delete=True,
    labels={'quantidade_semana': 'Aulas semanais'})


@staff_member_required(login_url='grade:inicio')
@require_http_methods(['GET', 'POST'])
def cursos(request, pk=None):
    curso = get_object_or_404(Curso, pk=pk) if pk else Curso()
    form = CursoForm(request.POST or None, instance=curso)
    matriz = MatrizFormSet(request.POST or None, instance=curso)
    erro = None
    if request.method == 'POST':
        try:
            with transaction.atomic():
                if request.POST.get('acao') == 'excluir' and curso.pk:
                    curso.delete()
                    return redirect('grade:cursos')
                if request.POST.get('acao') == 'exemplo' and not pk:
                    if Curso.objects.filter(nome='Preparatório 1').exists():
                        raise ValidationError('O exemplo já existe. Edite o cadastro existente.')
                    exemplo = Curso.objects.create(nome='Preparatório 1', observacoes='Exemplo editável: 24 aulas de 50 min = 20 horas semanais sem intervalos. Componentes compostos são uma escolha demonstrativa; podem ser separados. Inglês ou Espanhol representa uma única carga de idioma: escolha o idioma e a habilitação antes de gerar. Não cria professores, disponibilidades ou turmas.')
                    itens = [('Matemática',4,'EXATAS'), ('Português e interpretação',3,'HUMANAS'), ('Redação',2,'HUMANAS'), ('Biologia',3,'BIOLOGICAS'), ('Física',3,'EXATAS'), ('Química',3,'EXATAS'), ('História',2,'HUMANAS'), ('Geografia',2,'HUMANAS'), ('Filosofia e Sociologia',1,'HUMANAS'), ('Inglês ou Espanhol',1,'HUMANAS')]
                    for nome, quantidade, area in itens:
                        disciplina = Disciplina.objects.filter(nome=nome).order_by('pk').first()
                        if disciplina is None:
                            disciplina = Disciplina.objects.create(nome=nome, area=area)
                        MatrizCurricular.objects.create(curso=exemplo, disciplina=disciplina, quantidade_semana=quantidade)
                    return redirect('grade:curso_editar', pk=exemplo.pk)
                if form.is_valid() and matriz.is_valid():
                    form.save()
                    matriz.save()
                    return redirect('grade:curso_editar', pk=curso.pk)
        except (ValidationError, ProtectedError) as exc:
            erro = ' '.join(exc.messages) if isinstance(exc, ValidationError) else 'Curso vinculado a turmas: preserve o histórico; a exclusão foi impedida.'
    return render(request, 'grade/cursos.html', {'form':form, 'matriz':matriz, 'curso':curso, 'cursos':Curso.objects.all(), 'erro':erro})


@staff_member_required(login_url='grade:inicio')
@require_http_methods(['GET', 'POST'])
def turmas(request, pk=None):
    turma = get_object_or_404(Turma, pk=pk) if pk else Turma()
    legada = turma if turma.pk and not turma.curso_id else None
    adotar = request.method == 'POST' and request.POST.get('acao') == 'adotar_curso'
    dados = request.POST.copy() if adotar else request.POST or None
    if adotar:
        if not legada:
            return render(request, 'grade/turmas.html', {'form': TurmaForm(instance=turma),
                'turmas': Turma.objects.select_related('curso', 'unidade'),
                'erro': 'A adoção preserva somente turmas antigas ainda sem curso.'}, status=400)
        dados['nome'] = f'{legada.nome} · Curso'
        dados['unidade'] = str(legada.unidade_id)
        turma = Turma()
    form = TurmaForm(dados, instance=turma)
    erro = None
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
                if adotar:
                    legada.demandas.filter(origem_curso=False).update(ativa=False)
                    messages.success(request, 'Nova oferta do curso criada. A turma e as aulas antigas foram preservadas como histórico; suas demandas manuais foram desativadas.')
            return redirect('grade:turma_editar', pk=turma.pk)
        except ValidationError as exc:
            erro = ' '.join(exc.messages)
    return render(request, 'grade/turmas.html', {'form':form, 'turmas':Turma.objects.select_related('curso','unidade'), 'erro':erro, 'turma_legada':legada})


@staff_member_required(login_url='grade:inicio')
@require_http_methods(['GET'])
def consultar(request):
    try:
        dia = forms.DateField().clean(request.GET.get('semana') or timezone.localdate().isoformat())
    except ValidationError:
        dia = timezone.localdate()
    inicio = dia - timedelta(days=dia.weekday())
    aulas = AlocacaoGrade.objects.filter(data__range=(inicio,inicio+timedelta(days=6))).select_related('professor','unidade','turma__curso','disciplina','horario')
    filtros = [('professor', Professor), ('unidade', Unidade), ('curso', Curso), ('turma', Turma)]
    for campo, _ in filtros:
        valor = request.GET.get(campo, '')
        if valor.isdecimal():
            aulas = aulas.filter(**{('turma__curso_id' if campo=='curso' else campo+'_id'):int(valor)})
    agrupar = request.GET.get('por','turma')
    if agrupar not in dict(filtros):
        agrupar='turma'
    grupos={}
    for aula in aulas.order_by('data','horario__hora_inicio','unidade__nome','turma__nome'):
        grupo = getattr(aula.turma,'curso',None) if agrupar=='curso' else getattr(aula,agrupar)
        grupos.setdefault(f'{grupo} (#{grupo.pk})' if grupo else 'Legado / sem vínculo',[]).append(aula)
    return render(request,'grade/consultar.html',{'grupos':grupos, 'inicio':inicio, 'por':agrupar,
        'filtros':[{'nome':c,'opcoes':m.objects.all(),'selecionado':request.GET.get(c,'')} for c,m in filtros]})
