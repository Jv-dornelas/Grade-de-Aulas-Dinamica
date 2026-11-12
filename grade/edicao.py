"""Edição da grade salva ou da proposta privada, no mesmo quadro semanal."""
from copy import deepcopy
from datetime import date, timedelta
import secrets
import time

from django import forms
from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import OperationalError, transaction
from django.shortcuts import get_object_or_404, redirect

from .automacao import CHAVE_PREVIA, VALIDADE_SEGUNDOS, assinatura_dados
from .distribuicao import url_grade
from .models import AlocacaoGrade, DemandaAula, Disponibilidade, Professor, Sala
from .restricoes import MotorRestricoes, validar_alocacao_individual


@transaction.atomic
def salvar_disponibilidades(request, dia, previa):
    if previa:
        raise ValidationError('Confirme ou descarte a prévia antes de alterar disponibilidades.')
    inicio = dia - timedelta(days=dia.weekday())
    if request.POST.get('assinatura') != assinatura_dados(inicio):
        raise ValidationError('Os dados mudaram. Atualize antes de salvar disponibilidades.')
    professores = list(Professor.objects.select_for_update().order_by('pk'))
    valores = {(p.pk, dia): (request.POST.get(f'disp_manha_{p.pk}') == 'on',
                             request.POST.get(f'disp_tarde_{p.pk}') == 'on') for p in professores}
    MotorRestricoes(disponibilidades=valores).validar(
        AlocacaoGrade.objects.filter(data__range=(inicio, inicio + timedelta(days=6))))
    for p in professores:
        manha, tarde = valores[p.pk, dia]
        registros = Disponibilidade.objects.filter(professor=p, data=dia)
        if not registros.update(disponivel_manha=manha, disponivel_tarde=tarde):
            Disponibilidade.objects.create(professor=p, data=dia, disponivel_manha=manha, disponivel_tarde=tarde)


class DemandaSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if hasattr(value, 'instance'):
            option['attrs']['data-unidade'] = value.instance.turma.unidade_id
        return option


class AulaForm(forms.ModelForm):
    confirmar_excecao = forms.BooleanField(required=False, label='Confirmo a exceção manual de limite diário')
    justificativa_excecao = forms.CharField(required=False, max_length=200, label='Justificativa da exceção',
        widget=forms.Textarea(attrs={'rows': 2}))
    class Meta:
        model = AlocacaoGrade
        fields = ['data', 'horario', 'unidade', 'sala', 'demanda', 'professor']
        widgets = {'data': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'), 'demanda': DemandaSelect}
        labels = {'demanda': 'Turma e disciplina (matriz semanal)'}
        help_texts = {'demanda': 'Selecione o vínculo curricular. Vazio mantém uma aula legada, sem turma/curso.'}

    def __init__(self, *args, proposta=False, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.proposta = proposta
        self.usuario = usuario
        if proposta:
            self.fields.pop('confirmar_excecao')
            self.fields.pop('justificativa_excecao')
        self.fields['professor'].required = False
        self.fields['professor'].empty_label = 'Sem professor'
        self.fields['sala'].empty_label = 'Sem sala · reserva toda a unidade'
        self.fields['sala'].help_text = 'Selecione uma sala para permitir aulas paralelas de outras turmas. Sem sala, o intervalo fica reservado para toda a unidade.'
        unidade = (self.data.get('unidade') if self.is_bound else None) or self.instance.unidade_id or self.initial.get('unidade')
        if unidade and str(unidade).isdecimal():
            self.fields['sala'].queryset = Sala.objects.filter(unidade_id=unidade)
        self.fields['demanda'].queryset = DemandaAula.objects.select_related('turma__unidade', 'disciplina').order_by('turma__nome', 'disciplina__nome')
        if not self.instance.pk:
            self.fields['demanda'].required = True
            self.fields['demanda'].queryset = self.fields['demanda'].queryset.filter(ativa=True, origem_curso=True)
        self.fields['demanda'].help_text = 'Disciplina da matriz do curso da turma. Não é um cadastro independente de carga.'
        if proposta:
            self.fields['demanda'].disabled = True
            self.fields['unidade'].disabled = True
        if self.instance.turma_id and self.instance.turma.materias_fixas and (proposta or self.instance.pk):
            for campo in ('data', 'horario', 'demanda', 'unidade'):
                self.fields[campo].disabled = True

    def clean(self):
        dados = super().clean()
        demanda = dados.get('demanda')
        self.instance.turma = demanda.turma if demanda else None
        self.instance.disciplina = demanda.disciplina if demanda else None
        self.instance.motivo_pendencia = '' if dados.get('professor') else 'Docente ainda não atribuído pela coordenação.'
        if not self.proposta:
            confirmar = dados.get('confirmar_excecao', False)
            motivo = (dados.get('justificativa_excecao') or '').strip()
            if confirmar and (not motivo or not self.usuario or not self.usuario.is_active or not self.usuario.is_staff):
                raise ValidationError('Para confirmar a exceção manual, informe a justificativa. A ação exige um administrador ativo.')
            self.instance.eh_excecao_limite_aulas = confirmar
            self.instance.motivo_excecao_limite = motivo if confirmar else ''
            self.instance._limite_manual_autorizado = confirmar
            if confirmar:
                self.instance.autorizado_por = self.usuario
        return dados


def estado_aula(aula):
    return {c: str(getattr(aula, c)) for c in ('pk', 'data', 'horario_id', 'unidade_id',
        'sala_id', 'professor_id', 'demanda_id', 'turma_id', 'disciplina_id', 'atualizado_em')}


def contexto_editor(request, auto, dia):
    dados = request.POST if request.method == 'POST' else request.GET
    if not any(c in dados for c in ('editar', 'proposta', 'nova')):
        return {}
    proposta = 'proposta' in dados
    previa = auto['previa']
    if previa and previa.get('tipo') == 'replicacao':
        return {'erro_editor': 'Confirme ou descarte a replicação antes de editar aulas. Depois de copiar, cada semana pode ser ajustada normalmente.'}
    erro = None
    indice = None
    if proposta:
        try:
            indice = int(dados['proposta'])
            if indice < 0 or not previa:
                raise ValueError
            item = previa['resultado']['propostas'][indice]
        except (ValueError, TypeError, IndexError):
            return {'erro_editor': 'Proposta não encontrada. Atualize a grade.'}
        aula = AlocacaoGrade(**{**item, 'data': date.fromisoformat(item['data'])})
    elif dados.get('editar', '').isascii() and dados.get('editar', '').isdecimal() and len(dados['editar']) < 11:
        aula = get_object_or_404(AlocacaoGrade, pk=dados['editar'])
    else:
        aula = AlocacaoGrade()
    estado = signing.dumps(estado_aula(aula), salt='grade-editor')
    inicial = {'data': dados.get('data_aula', dia.isoformat())}
    for campo in ('horario', 'unidade', 'sala', 'professor', 'demanda'):
        if dados.get(campo, '').isdecimal() and len(dados[campo]) < 11:
            inicial[campo] = dados[campo]
    form = AulaForm(request.POST if request.method == 'POST' else None,
                    instance=aula, initial=inicial if not aula.pk and not proposta else None, proposta=proposta,
                    usuario=request.user)
    if request.method == 'GET' and dados.get('turma', '').isdecimal() and not aula.pk and not proposta:
        form.fields['demanda'].queryset = form.fields['demanda'].queryset.filter(turma_id=dados['turma'])
    if request.method == 'POST' and request.POST.get('acao') == 'salvar_aula':
        try:
            if proposta:
                if (auto.get('previa_desatualizada') or time.time() - previa['criada_em'] > VALIDADE_SEGUNDOS
                        or not secrets.compare_digest(str(dados.get('token', '')), previa['token'])):
                    raise ValidationError('Prévia alterada, expirada ou token inválido. Gere novamente.')
            else:
                if previa:
                    raise ValidationError('Confirme ou descarte a prévia antes de alterar aulas já salvas.')
                if signing.loads(dados.get('estado', ''), salt='grade-editor', max_age=1800) != estado_aula(aula):
                    raise ValidationError('Esta aula mudou desde que o editor foi aberto. Atualize antes de salvar.')
            if form.is_valid():
                with transaction.atomic():
                    if proposta:
                        inicio = date.fromisoformat(previa['inicio'])
                        if not inicio <= aula.data <= inicio + timedelta(days=6):
                            raise ValidationError('Mantenha a aula na semana da proposta.')
                        if assinatura_dados(inicio) != previa['assinatura']:
                            raise ValidationError('Os dados mudaram. Gere uma nova prévia.')
                        nova = deepcopy(previa)
                        nova['resultado']['propostas'][indice] = {
                            'data': aula.data.isoformat(), 'motivo_pendencia': aula.motivo_pendencia, **{c: getattr(aula, c) for c in (
                                'horario_id', 'unidade_id', 'sala_id', 'professor_id', 'turma_id', 'disciplina_id', 'demanda_id')}}
                        fixas = list(AlocacaoGrade.objects.filter(data__range=(inicio, inicio + timedelta(days=6))))
                        propostas = [AlocacaoGrade(**{**p, 'data': date.fromisoformat(p['data'])}) for p in nova['resultado']['propostas']]
                        nova['resultado']['avisos'] = MotorRestricoes().validar(fixas + propostas, proximidade=nova['proximidade'])
                        from collections import Counter
                        contagem = Counter(a.demanda_id for a in fixas + propostas if a.demanda_id and a.professor_id)
                        faltas = [(d, max(0, d.quantidade_semana - contagem[d.pk])) for d in DemandaAula.objects.filter(ativa=True)]
                        nova['resultado']['resumo']['pendentes'] = sum(n for d, n in faltas)
                        nova['resultado']['pendencias'] = [f'{d.turma} / {d.disciplina}: {n} aula(s) sem docente ou horário.' for d, n in faltas if n]
                        # Rotação protege contra outro editor aberto na mesma sessão.
                        nova['token'] = secrets.token_urlsafe(24)
                        nova['resultado']['status'] = 'feasible'
                        nova['resultado']['ajustada_manualmente'] = True
                        request.session[CHAVE_PREVIA] = nova
                        messages.success(request, 'Proposta ajustada na grade. Confirme para gravar as aulas.')
                    else:
                        if aula.pk:
                            atual = AlocacaoGrade.objects.select_for_update().get(pk=aula.pk)
                            if signing.loads(dados.get('estado', ''), salt='grade-editor', max_age=1800) != estado_aula(atual):
                                raise ValidationError('Esta aula foi alterada por outro usuário. Atualize.')
                        avisos = validar_alocacao_individual(aula)
                        aula.autorizado_por = request.user
                        aula.save()
                        if aula.eh_excecao_limite_aulas:
                            from django.contrib.admin.models import LogEntry, CHANGE
                            from django.contrib.contenttypes.models import ContentType
                            LogEntry.objects.log_action(user_id=request.user.pk,
                                content_type_id=ContentType.objects.get_for_model(aula).pk,
                                object_id=aula.pk, object_repr=str(aula)[:200], action_flag=CHANGE,
                                change_message='Exceção manual de limite diário: ' + aula.motivo_excecao_limite)
                        messages.success(request, 'Aula salva na distribuição.')
                        for aviso in avisos:
                            messages.warning(request, aviso)
                return redirect(url_grade(aula.data, request.GET.get('por', dados.get('por', 'unidade')),
                                          request.GET.get('entidade', dados.get('entidade', '')), request.GET.get('visao', dados.get('visao'))))
        except (ValidationError, signing.BadSignature) as exc:
            erro = ' '.join(exc.messages) if isinstance(exc, ValidationError) else 'Editor inválido ou expirado. Atualize a página.'
        except OperationalError:
            erro = 'O banco está ocupado. Atualize a grade e tente novamente; nenhuma confirmação foi concluída.'
    return {'aula_form': form, 'aula_editor': aula, 'editor_proposta': proposta,
            'indice_editor': indice, 'estado_editor': estado, 'erro_editor': erro,
            'url_fechar_editor': url_grade(dia, request.GET.get('por', 'unidade'), request.GET.get('entidade', ''))}
