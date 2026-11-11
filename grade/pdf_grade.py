"""PDF da mesma projeção semanal e da mesma prévia privada da tela principal."""
from datetime import date, timedelta
from io import BytesIO
from xml.sax.saxutils import escape
import time

from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .automacao import VALIDADE_SEGUNDOS, assinatura_atual_previa, contexto_automacao
from .distribuicao import dados_distribuicao


@never_cache
@staff_member_required(login_url='grade:inicio')
@require_GET
def grade_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, PageBreak

    try:
        dia = date.fromisoformat(request.GET.get('data') or timezone.localdate().isoformat())
        if not date(1900, 1, 8) <= dia <= date(2100, 12, 24):
            raise ValueError
    except ValueError:
        return HttpResponseBadRequest('Data inválida.')
    auto = contexto_automacao(request, processar=False)
    from .replicacao import aplicar_previa_replicacao
    aplicar_previa_replicacao(auto, request)
    previa = auto['previa']
    inicio = dia - timedelta(days=dia.weekday())
    if previa and date.fromisoformat(previa['inicio']) <= inicio <= date.fromisoformat(previa.get('ultima', previa['inicio'])) and (
            assinatura_atual_previa(previa) != previa['assinatura'] or time.time() - previa['criada_em'] > VALIDADE_SEGUNDOS):
        return HttpResponseBadRequest('A prévia está desatualizada ou expirada. Gere novamente antes de exportar.')
    context = dados_distribuicao(request, dia, auto)
    if context['visao'] == 'dia':
        grupos_pdf = []
        for grupo in context['distribuicao_diaria']:
            # Limitar turmas por página para manter a leitura e não omitir colunas.
            for offset in range(0, len(grupo['colunas']), 4):
                colunas = grupo['colunas'][offset:offset+4]
                grupos_pdf.append({'nome': grupo['nome'],
                    'cabecalhos': [escape(t.nome + ' / ' + (t.curso.nome if t.curso else 'Histórico')) if t else 'Sem turma / legado' for t in colunas],
                    'linhas': [{'horario': l['horario'], 'celulas': [c['aulas'] for c in l['celulas'][offset:offset+4]]} for l in grupo['linhas']]})
    else:
        grupos_pdf = context['distribuicao']
    aulas_pdf = [a for g in grupos_pdf for l in g['linhas'] for c in l['celulas'] for a in c]
    styles = getSampleStyleSheet()
    normal = ParagraphStyle('GradeCell', parent=styles['Normal'], fontSize=7.5, leading=9)
    header = ParagraphStyle('GradeHeader', parent=normal, textColor=colors.white, alignment=TA_CENTER)
    titulo = 'Grade horária' + (' - PRÉVIA NÃO CONFIRMADA' if context['previa_visivel'] else '')
    story = [Paragraph(titulo, styles['Title']),
             Paragraph(f"{inicio:%d/%m/%Y} a {context['fim_distribuicao']:%d/%m/%Y} | Por {context['nome_modo'].lower()} | {len(aulas_pdf)} aulas exibidas", styles['Normal']),
             Paragraph('Aulas de 50 minutos. Almoço: 11:20 - 12:20. Filtros seguem a seleção da tela.', styles['Normal']), Spacer(1, 12)]
    if context['visao'] == 'dia':
        story += [Paragraph(f'Visão diária por turma: {dia:%d/%m/%Y}. Contagens e aprovação referem-se à semana.', styles['Normal']), Spacer(1, 10)]
    if not context['previa_visivel']:
        from .aprovacao import estado_aprovacao
        estado = estado_aprovacao(inicio)
        if estado['aprovacao_vigente']:
            a = estado['aprovacao_vigente']
            texto = f"Grade aprovada{' parcialmente' if a.parcial else ''} em {timezone.localtime(a.aprovado_em):%d/%m/%Y %H:%M} por {a.aprovado_por or 'usuário removido'}."
        elif estado['aprovacao_alterada']:
            texto = 'Grade alterada após a aprovação. A versão atual aguarda nova aprovação.'
        else:
            texto = 'Grade aguardando aprovação.'
        story += [Paragraph(escape(texto), styles['Normal']), Spacer(1, 10)]
    sem_professor_pdf = sum(a['sem_professor'] for a in aulas_pdf)
    if sem_professor_pdf:
        story += [Paragraph(f"Há {sem_professor_pdf} aulas sem professor nesta seleção. Não representam carga atendida por docentes.", styles['Normal']), Spacer(1, 10)]
    if context['previa_visivel']:
        story += [Paragraph('PRÉVIA: contém aulas propostas ainda não salvas. Este PDF não confirma nem grava a distribuição.', styles['Normal']), Spacer(1, 10)]
        if auto['resultado'].get('resumo', {}).get('pendentes'):
            story.append(Paragraph(f"Há {auto['resultado']['resumo']['pendentes']} pendências no planejamento completo. As aulas sem professor estão identificadas nos quadros; consulte os motivos na aplicação.", normal))
    dias_nome = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    for index, grupo in enumerate(grupos_pdf):
        if index:
            story.append(PageBreak())
        story += [Paragraph(escape(grupo['nome']), styles['Heading2']), Spacer(1, 6)]
        cabecalhos = grupo.get('cabecalhos', [f'{dias_nome[d.weekday()]}<br/>{d:%d/%m}' for d in context['dias_distribuicao']])
        rows = [[Paragraph('Horário', header)] + [Paragraph(c, header) for c in cabecalhos]]
        for linha in grupo['linhas']:
            horario = linha['horario']
            row = [Paragraph(f'{horario.hora_inicio:%H:%M}<br/>{horario.hora_fim:%H:%M}', normal)]
            for celula in linha['celulas']:
                textos = []
                for aula in celula:
                    dados = [
                        aula['disciplina'].nome if aula['disciplina'] else 'Aula legada',
                        aula['professor'].nome if aula['professor'] else 'SEM PROFESSOR',
                        aula['sala'].nome if aula.get('sala') else 'Sem sala - reserva a unidade']
                    if context['visao'] != 'dia':
                        dados += [aula['unidade'].nome, aula['turma'].nome if aula['turma'] else 'Sem turma',
                                  aula['curso'].nome if aula['curso'] else 'Sem curso']
                    textos.append('<br/>'.join(escape(t) for t in (['PRÉVIA'] if aula['proposta'] else []) + dados))
                row.append(Paragraph('<br/><br/>'.join(textos) or '-', normal))
            rows.append(row)
        table = LongTable(rows, colWidths=[62] + [1050 / len(cabecalhos)] * len(cabecalhos), repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        story.append(table)
    if not grupos_pdf:
        story.append(Paragraph('Nenhuma aula nesta seleção.', styles['Normal']))
    buffer = BytesIO()
    def rodape(canvas, doc):
        canvas.setFont('Helvetica', 8)
        canvas.drawString(34, 20, 'Grade horária - ' + ('Prévia não confirmada' if context['previa_visivel'] else 'Distribuição curricular'))
        canvas.drawRightString(landscape(A3)[0] - 34, 20, f'Página {doc.page}')
    SimpleDocTemplate(buffer, pagesize=landscape(A3), leftMargin=34, rightMargin=34,
                      topMargin=30, bottomMargin=35, title=titulo).build(story, onFirstPage=rodape, onLaterPages=rodape)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'grade-{inicio}-{context["por"]}.pdf')
