"""Projeções da mesma grade: nenhuma escrita ao mudar o modo de visualização."""
from collections import Counter, defaultdict
from datetime import date, timedelta
from urllib.parse import urlencode

from django.urls import reverse

from .models import AlocacaoGrade, Curso, HorarioAula, HorarioCurricular, Professor, Turma, Unidade


MODOS = {'unidade': ('Unidade', Unidade), 'turma': ('Turma', Turma),
         'professor': ('Professor', Professor), 'curso': ('Curso', Curso)}


def url_grade(dia, por='unidade', entidade='', visao=None):
    return reverse('grade:exibir_grade') + '?' + urlencode({
        'data': dia.isoformat(), 'por': por, 'entidade': entidade, **({'visao': visao} if visao else {})})


def dados_distribuicao(request, dia, contexto_auto):
    inicio = dia - timedelta(days=dia.weekday())
    fim = inicio + timedelta(days=6)
    dias = [fim] + [inicio + timedelta(days=d) for d in range(6)]
    por = request.GET.get('por', request.POST.get('por', 'unidade'))
    if por not in MODOS:
        por = 'unidade'
    visao = request.GET.get('visao', request.POST.get('visao', 'dia')) if por == 'unidade' else 'semana'
    if visao not in ('dia', 'semana'):
        visao = 'dia'
    entidade = request.GET.get('entidade', request.POST.get('entidade', ''))
    if entidade != 'legado' and (not entidade.isascii() or not entidade.isdecimal() or len(entidade) > 10):
        entidade = ''
    modelo = MODOS[por][1]
    opcoes = list(modelo.objects.order_by('nome', 'pk'))
    if entidade not in ('', 'legado') and not any(str(o.pk) == entidade for o in opcoes):
        entidade = ''

    salvas = list(AlocacaoGrade.objects.filter(data__range=(inicio, fim)).select_related(
        'horario', 'professor', 'unidade', 'turma__curso', 'disciplina', 'sala'))
    previa = contexto_auto.get('previa')
    previa_visivel = bool(previa and date.fromisoformat(previa['inicio']) <= inicio <= date.fromisoformat(previa.get('ultima', previa['inicio']))
                          and not contexto_auto.get('previa_desatualizada'))
    propostas = [a for a in contexto_auto.get('linhas', []) if inicio <= a['data'] <= fim] if previa_visivel else []
    grupos = {}
    itens_visiveis = []
    contagem_visivel = novas_visiveis = 0
    mapa_cursos = {t.pk: t.curso for t in Turma.objects.select_related('curso')}

    def inserir(aula, proposta, indice=None, pendente=False):
        nonlocal contagem_visivel, novas_visiveis
        item = dict(aula) if proposta or pendente else {campo: getattr(aula, campo) for campo in (
            'data', 'horario', 'professor', 'unidade', 'sala', 'turma', 'disciplina')}
        item.setdefault('sala', None)
        turma = item['turma']
        item['curso'] = mapa_cursos.get(turma.pk) if turma else None
        item['proposta'] = proposta
        item['sem_professor'] = pendente or not item['professor']
        item['excecao_manual'] = bool(not proposta and not pendente and aula.eh_excecao_limite_aulas)
        item['justificativa_excecao'] = aula.motivo_excecao_limite if item['excecao_manual'] else ''
        item['motivo_pendencia'] = item.get('motivo_pendencia', '') if proposta or pendente else aula.motivo_pendencia
        item['id'] = None if proposta or pendente else aula.pk
        campos_editor = {'proposta': indice} if proposta else {'editar': aula.pk} if not pendente else {
            'nova': 1, 'data_aula': item['data'].isoformat(), 'horario': item['horario'].pk,
            'demanda': item['demanda'].pk, 'unidade': item['unidade'].pk}
        item['url_editar'] = url_grade(dia, por, entidade, visao) + '&' + urlencode(campos_editor) + '#editor-aula'
        grupo = item[por]
        chave = str(grupo.pk) if grupo else 'legado'
        if entidade and entidade != chave:
            return
        itens_visiveis.append(item)
        nome = str(grupo) if grupo else ('Sem professor' if por == 'professor' else 'Sem vínculo / legado')
        if por == 'curso' and turma:
            chave += ':turma:' + str(turma.pk)
            nome += f' · {turma.nome} · {item["unidade"].nome}'
        contagem_visivel += 1
        novas_visiveis += int(proposta)
        if chave not in grupos:
            grupos[chave] = {'nome': nome,
                             'chave': chave, 'quantidade': 0, 'celulas': defaultdict(list)}
        grupos[chave]['quantidade'] += 1
        # Lista por célula: nunca descartar registros ao projetar por curso/professor.
        grupos[chave]['celulas'][item['horario'].pk, item['data']].append(item)

    for aula in salvas:
        inserir(aula, False)
    for indice, aula in enumerate(propostas):
        inserir(aula, True, indice)
    preenchidas = Counter(a.demanda_id for a in salvas if a.demanda_id)
    cobertos = {(a.data, a.horario_id, a.demanda_id) for a in salvas}
    if previa_visivel:
        for item in previa['resultado']['propostas']:
            if not inicio <= date.fromisoformat(item['data']) <= fim:
                continue
            preenchidas[item['demanda_id']] += 1
            cobertos.add((date.fromisoformat(item['data']), item['horario_id'], item['demanda_id']))
    pendentes = 0
    for item in HorarioCurricular.objects.filter(turma__materias_fixas=True, demanda__ativa=True).select_related(
            'turma__unidade', 'demanda__disciplina', 'horario'):
        data_item = inicio + timedelta(days=item.dia_semana)
        if (preenchidas[item.demanda_id] >= item.demanda.quantidade_semana
                or (data_item, item.horario_id, item.demanda_id) in cobertos):
            continue
        preenchidas[item.demanda_id] += 1
        pendentes += 1
        inserir({'data': data_item, 'horario': item.horario, 'professor': None,
            'unidade': item.turma.unidade, 'turma': item.turma,
            'disciplina': item.demanda.disciplina, 'demanda': item.demanda}, False, pendente=True)

    horarios = list(HorarioAula.objects.order_by('hora_inicio', 'hora_fim', 'pk'))
    diario = []
    if por == 'unidade':
        turmas = list(Turma.objects.select_related('curso', 'unidade').prefetch_related('horarios', 'demandas'))
        for unidade in opcoes:
            if entidade and entidade != str(unidade.pk):
                continue
            itens = [a for a in itens_visiveis if a['unidade'].pk == unidade.pk]
            ids = {a['turma'].pk for a in itens if a['turma']}
            colunas = [t for t in turmas if t.unidade_id == unidade.pk and (t.pk in ids or any(d.ativa for d in t.demandas.all()))]
            if any(not a['turma'] for a in itens):
                colunas.append(None)
            if not colunas:
                continue
            linhas = []
            for h in horarios:
                celulas = []
                for t in colunas:
                    aulas = [a for a in itens if a['data'] == dia and a['horario'].pk == h.pk and a['turma'] == t]
                    campos = {'nova': 1, 'data_aula': dia.isoformat(), 'horario': h.pk, 'unidade': unidade.pk}
                    if t:
                        campos['turma'] = t.pk
                    celulas.append({'aulas': aulas, 'permitida': not t or t.permite_horario(dia.weekday(), h),
                        'url_nova': url_grade(dia, por, entidade, visao) + '&' + urlencode(campos) + '#editor-aula'})
                linhas.append({'horario': h, 'celulas': celulas})
            diario.append({'nome': unidade.nome, 'colunas': colunas, 'colspan': len(colunas)+1, 'linhas': linhas,
                           'largura': max(600, 88+len(colunas)*220),
                           'quantidade': sum(a['data'] == dia for a in itens)})
    for grupo in grupos.values():
        grupo['linhas'] = [{'horario': h, 'celulas': [grupo['celulas'].get((h.pk, d), []) for d in dias]}
                            for h in horarios]
        for linha in grupo['linhas']:
            linha['celulas_edicao'] = []
            for d, aulas in zip(dias, linha['celulas']):
                campos = {'nova': 1, 'data_aula': d.isoformat(), 'horario': linha['horario'].pk}
                if por in ('unidade', 'professor') and grupo['chave'].isdecimal():
                    campos[por] = grupo['chave']
                linha['celulas_edicao'].append({'data': d, 'aulas': aulas,
                    'url_nova': url_grade(dia, por, entidade, visao) + '&' + urlencode(campos) + '#editor-aula'})
        del grupo['celulas']
    return {
        'distribuicao': sorted(grupos.values(), key=lambda g: g['nome'].casefold()),
        'visao': visao, 'distribuicao_diaria': diario,
        'dia_distribuicao': dia,
        'url_visao_dia': url_grade(dia, por, entidade, 'dia'),
        'url_visao_semana': url_grade(dia, por, entidade, 'semana'),
        'dias_navegacao': [{'data': d, 'url': url_grade(d, por, entidade, visao)} for d in dias],
        'dias_distribuicao': dias, 'inicio_distribuicao': inicio, 'fim_distribuicao': fim,
        'por': por, 'entidade': entidade, 'opcoes_distribuicao': opcoes,
        'modos_distribuicao': [{'valor': m, 'nome': label, 'url': url_grade(dia, m)} for m, (label, _) in MODOS.items()],
        'nome_modo': MODOS[por][0], 'previa_visivel': previa_visivel,
        'url_semana_previa': url_grade(date.fromisoformat(previa['inicio']), por, visao=visao) if previa else '',
        'url_anterior': url_grade(dia - timedelta(days=1 if visao == 'dia' else 7), por, entidade, visao),
        'url_proxima': url_grade(dia + timedelta(days=1 if visao == 'dia' else 7), por, entidade, visao),
        'total_salvas': len(salvas), 'total_propostas': len(propostas),
        'total_visivel': contagem_visivel, 'propostas_visiveis': novas_visiveis,
        'total_sem_filtro': len(salvas) + len(propostas) + pendentes,
        'total_sem_professor': pendentes + sum(not a.professor_id for a in salvas) + sum(not a['professor'] for a in propostas),
        'url_sem_filtro': url_grade(dia, por, visao=visao),
        'url_nova_aula': url_grade(dia, por, entidade, visao) + '&nova=1#editor-aula',
        'url_pdf_grade': reverse('grade:grade_pdf') + '?' + urlencode({'data': dia.isoformat(), 'por': por, 'entidade': entidade, 'visao': visao}),
    }
