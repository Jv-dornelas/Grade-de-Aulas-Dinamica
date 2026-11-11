"""Caixa de saída por versão aprovada; nenhum destinatário recebe a grade alheia."""
import hashlib
import json
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import AlocacaoGrade, AprovacaoGrade, AvisoGradeEmail, Professor

logger = logging.getLogger(__name__)


def preparar_avisos(aprovacao):
    anterior = AprovacaoGrade.objects.filter(semana=aprovacao.semana).exclude(pk=aprovacao.pk).order_by('-aprovado_em').first()
    anteriores = {a.professor_id: a for a in anterior.avisos_email.all()} if anterior else {}
    aulas = AlocacaoGrade.objects.filter(data__range=(aprovacao.semana, aprovacao.semana + timedelta(days=6)),
        professor__isnull=False).select_related('horario', 'unidade', 'turma', 'disciplina', 'sala').order_by('data', 'horario__hora_inicio', 'pk')
    por_professor = {}
    for aula in aulas:
        por_professor.setdefault(aula.professor_id, []).append(aula)
    for professor in Professor.objects.filter(pk__in=set(por_professor) | set(anteriores)):
        linhas = [f"{a.data:%d/%m/%Y} {a.horario.hora_inicio:%H:%M}–{a.horario.hora_fim:%H:%M} | "
                  f"{a.disciplina or 'Disciplina não informada'} | {a.turma or 'Turma não informada'} | "
                  f"{a.unidade} | {a.sala or 'Sala não informada'}" for a in por_professor.get(professor.pk, [])]
        assinatura = hashlib.sha256(json.dumps(linhas, ensure_ascii=False).encode()).hexdigest()
        anterior_aviso = anteriores.get(professor.pk)
        # Mantém referência da versão mesmo quando não houve mudança individual.
        igual = (anterior_aviso and anterior_aviso.assinatura_grade == assinatura
                 and anterior_aviso.estado in ['enviado', 'simulado', 'sem_alteracao'])
        corpo = (f"Olá, {professor.nome}!\n\nSua grade da semana de {aprovacao.semana:%d/%m/%Y} foi atualizada e aprovada.\n\n"
                 + ('\n'.join(linhas) if linhas else 'Você não possui aulas nesta versão aprovada da semana.')
                 + f"\n\nConsulte sua grade atual em {settings.GRADE_URL_PUBLICA}/mobile/\n"
                   'Este aviso retrata a versão aprovada; alterações posteriores podem exigir nova aprovação.')
        AvisoGradeEmail.objects.get_or_create(aprovacao=aprovacao, professor=professor, defaults={
            'destinatario': professor.email or '', 'assinatura_grade': assinatura,
            'assunto': f'Grade atualizada — semana de {aprovacao.semana:%d/%m/%Y}', 'corpo': corpo,
            'estado': 'sem_alteracao' if igual else ('pendente' if professor.email else 'sem_email')})
    transaction.on_commit(lambda: enviar_avisos(aprovacao.pk), robust=True)


def enviar_avisos(aprovacao_id=None):
    ids = AvisoGradeEmail.objects.filter(estado__in=['pendente', 'erro', 'sem_email'])
    if aprovacao_id is not None:
        ids = ids.filter(aprovacao_id=aprovacao_id)
    for pk in list(ids.values_list('pk', flat=True)):
        # SQLite: atualização condicional impede dois processos de reivindicar o mesmo aviso.
        with transaction.atomic():
            if not AvisoGradeEmail.objects.filter(pk=pk, estado__in=['pendente', 'erro', 'sem_email']).update(estado='enviando'):
                continue
        aviso = AvisoGradeEmail.objects.select_related('professor', 'aprovacao').get(pk=pk)
        from .automacao import assinatura_dados
        if assinatura_dados(aviso.aprovacao.semana) != aviso.aprovacao.assinatura:
            aviso.estado = 'desatualizado'
        elif not (aviso.destinatario or aviso.professor.email):
            aviso.estado = 'sem_email'
        else:
            aviso.destinatario = aviso.destinatario or aviso.professor.email
            aviso.tentativas += 1
            try:
                total = send_mail(aviso.assunto, aviso.corpo, settings.DEFAULT_FROM_EMAIL, [aviso.destinatario])
                if total != 1:
                    raise RuntimeError('Backend não aceitou a mensagem')
                aviso.estado = 'enviado' if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend' else 'simulado'
            except Exception:
                # Não registrar corpo, endereço ou credenciais nos logs.
                logger.warning('Falha no envio do aviso de grade %s', aviso.pk)
                aviso.estado = 'erro'
        aviso.save(update_fields=['estado', 'destinatario', 'tentativas', 'atualizado_em'])
