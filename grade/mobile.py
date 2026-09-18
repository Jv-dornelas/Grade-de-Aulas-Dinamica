"""Consulta mobile: a identidade vem da sessão, nunca de um ID enviado pelo cliente."""
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .models import AlocacaoGrade, Professor


class MobileLoginView(LoginView):
    template_name = 'grade/mobile/login.html'
    next_page = reverse_lazy('grade:mobile')


class MobileLogoutView(LogoutView):
    next_page = reverse_lazy('grade:mobile_login')


class SemanaForm(forms.Form):
    semana = forms.DateField(required=False, input_formats=['%Y-%m-%d'])

    def clean_semana(self):
        value = self.cleaned_data['semana'] or timezone.localdate()
        if not date(1900, 1, 1) <= value <= date(2100, 12, 31):
            raise forms.ValidationError('Escolha uma data entre 1900 e 2100.')
        return value


def consultar_semana(request):
    professor = Professor.objects.filter(usuario=request.user).first()
    form = SemanaForm(request.GET)
    if not form.is_valid():
        return None, render(request, 'grade/mobile/erro.html', {
            'mensagem': 'Data inválida. Escolha uma data entre 1900 e 2100.'
        }, status=400)
    if professor is None:
        return None, render(request, 'grade/mobile/erro.html', {
            'mensagem': 'Sua conta ainda não está vinculada a um professor. Peça ao responsável para fazer o vínculo no painel administrativo.'
        }, status=403)
    selected = form.cleaned_data['semana']
    inicio = selected - timedelta(days=selected.weekday())
    fim = inicio + timedelta(days=6)
    aulas = list(AlocacaoGrade.objects.filter(
        professor=professor, data__range=(inicio, fim)
    ).select_related('horario', 'unidade').order_by('data', 'horario__hora_inicio', 'pk'))
    dias = [{'data': inicio + timedelta(days=i), 'aulas': []} for i in range(7)]
    for aula in aulas:
        dias[(aula.data - inicio).days]['aulas'].append(aula)
    return {
        'professor': professor, 'inicio': inicio, 'fim': fim,
        'anterior': inicio - timedelta(days=7), 'proxima': inicio + timedelta(days=7),
        'dias': dias, 'aulas': aulas, 'hoje': timezone.localdate(),
    }, None


@never_cache
@login_required(login_url='grade:mobile_login')
@require_GET
def minha_grade(request):
    context, error = consultar_semana(request)
    return error if error is not None else render(request, 'grade/mobile/semana.html', context)


@never_cache
@login_required(login_url='grade:mobile_login')
@require_GET
def baixar_pdf(request):
    context, error = consultar_semana(request)
    if error is not None:
        return error
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buffer = BytesIO()
    styles = getSampleStyleSheet()
    story = [Paragraph('Minha grade semanal', styles['Title']),
             Paragraph(escape(context['professor'].nome), styles['Heading2']),
             Paragraph(f"{context['inicio']:%d/%m/%Y} a {context['fim']:%d/%m/%Y}", styles['Normal']),
             Spacer(1, 18)]
    rows = [['Data', 'Horário', 'Aula', 'Unidade']]
    for aula in context['aulas']:
        rows.append([
            aula.data.strftime('%d/%m/%Y'),
            f'{aula.horario.hora_inicio:%H:%M}–{aula.horario.hora_fim:%H:%M}',
            Paragraph(escape(aula.horario.nome), styles['Normal']),
            Paragraph(escape(aula.unidade.nome), styles['Normal']),
        ])
    if context['aulas']:
        table = Table(rows, colWidths=[80, 95, 120, 180], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#164e47')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('LINEBELOW', (0, 1), (-1, -1), .5, colors.HexColor('#dce6e2')),
        ]))
        story.append(table)
    else:
        story.append(Paragraph('Nenhuma aula cadastrada nesta semana.', styles['Normal']))
    story.extend([Spacer(1, 18), Paragraph('Consulte o aplicativo para verificar atualizações da grade.', styles['Normal'])])
    SimpleDocTemplate(buffer, pagesize=A4, title='Minha grade semanal').build(story)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"minha-grade-{context['inicio']}.pdf")


@require_GET
def manifesto(request):
    return JsonResponse({
        'id': '/mobile/', 'name': 'Minha Grade • Professores', 'short_name': 'Minha Grade',
        'lang': 'pt-BR', 'start_url': '/mobile/', 'scope': '/mobile/',
        'display': 'standalone', 'theme_color': '#164e47', 'background_color': '#f4f7f5',
        'icons': [{'src': f'/static/grade/mobile/icon-{size}.png',
                   'sizes': f'{size}x{size}', 'type': 'image/png'} for size in (192, 512)],
    }, content_type='application/manifest+json')


@require_GET
def service_worker(request):
    source = Path(__file__).parent / 'static/grade/mobile/sw.js'
    response = HttpResponse(source.read_text(encoding='utf-8'), content_type='application/javascript')
    response['Cache-Control'] = 'no-cache'
    return response
