from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


def dias_uteis():
    return [0, 1, 2, 3, 4]


def validar_dias_semana(value):
    if (not isinstance(value, list) or not value
            or any(type(day) is not int or day < 0 or day > 6 for day in value)
            or len(value) != len(set(value))):
        raise ValidationError('Informe dias únicos de 0 (segunda) a 6 (domingo), por exemplo [0,1,2,3,4].')

# 1. TABELA DE UNIDADES / POLOS
class Unidade(models.Model):
    nome = models.CharField(max_length=50) 
    responsavel = models.CharField(max_length=100)
    # Novos campos para cálculo de rota do aplicativo
    endereco = models.CharField(max_length=200, blank=True, null=True, help_text="Rua, Número e Bairro")
    cidade = models.CharField(max_length=100, blank=True, null=True)
    cep = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.nome

class Sala(models.Model):
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name='salas')
    nome = models.CharField(max_length=60)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ('unidade__nome', 'nome')
        constraints = [models.UniqueConstraint(fields=['unidade', 'nome'], name='sala_nome_por_unidade')]

    def __str__(self):
        return f'{self.nome} · {self.unidade.nome}'

    def clean(self):
        super().clean()
        self.nome = self.nome.strip()
        if self.pk and Sala.objects.filter(pk=self.pk).exclude(unidade_id=self.unidade_id).exists() and self.alocacaograde_set.exists():
            raise ValidationError('Sala com aulas vinculadas: preserve a unidade e cadastre outra sala.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


# 2. NOVO: TABELA DE DISCIPLINAS (Separada do Professor)
class Disciplina(models.Model):
    AREAS_CHOICES = [
        ('EXATAS', 'Exatas'),
        ('HUMANAS', 'Humanas'),
        ('BIOLOGICAS', 'Biológicas'),
    ]
    nome = models.CharField(max_length=100)
    area = models.CharField(max_length=20, choices=AREAS_CHOICES)

    def __str__(self):
        return f"{self.nome} ({self.get_area_display()})"

    def clean(self):
        super().clean()
        self.nome = self.nome.strip()
        if any(d.nome.strip().casefold() == self.nome.casefold() for d in
               Disciplina.objects.filter(area=self.area).exclude(pk=self.pk)):
            raise ValidationError({'nome': 'Já existe uma disciplina com este nome e área. Utilize o cadastro existente.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

# 3. TABELA DE PROFESSORES
class Professor(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='professor',
        help_text='Conta usada pelo professor para consultar sua grade no celular.',
    )
    TRANSPORTE_CHOICES = [
        ('PARTICULAR', 'Carro / Moto'),
        ('PUBLICO', 'Transporte Público'),
        ('OUTRO', 'A pé / Outro'),
    ]
    
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    disciplinas = models.ManyToManyField(Disciplina, related_name='professores')
    meio_de_transporte = models.CharField(max_length=20, choices=TRANSPORTE_CHOICES, default='PARTICULAR')
    limite_aulas = models.PositiveIntegerField(default=5, help_text="Limite de aulas por dia")
    
    unidade_oficial = models.ForeignKey('Unidade', on_delete=models.SET_NULL, null=True, related_name='professores_oficiais')
    unidades_permitidas = models.ManyToManyField('Unidade', related_name='professores_permitidos')
    parente_vinculado = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Parente (preferência de proximidade)",
        help_text='Vale para ambos, mesmo cadastrada em um só sentido, nos dias em que os dois lecionarem.')
    
    # NOVO CAMPO: Observações para o coordenador
    observacao = models.TextField(blank=True, null=True, help_text="Informações personalizadas para consulta na montagem da grade")

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        if self.pk and self.parente_vinculado_id == self.pk:
            raise ValidationError({'parente_vinculado': 'Selecione outro professor como parente.'})

# 4. NOVO: MATRIZ DE DISTÂNCIAS INTERNAS
class MatrizDistancia(models.Model):
    origem = models.ForeignKey(Unidade, related_name='distancias_origem', on_delete=models.CASCADE)
    destino = models.ForeignKey(Unidade, related_name='distancias_destino', on_delete=models.CASCADE)
    tempo_minutos = models.PositiveIntegerField(help_text="Tempo médio de deslocamento em minutos")
    distancia_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True,
                                      validators=[MinValueValidator(0)])
    fonte = models.CharField(max_length=30, blank=True, default='')
    consultado_em = models.DateTimeField(null=True, blank=True)
    enderecos_hash = models.CharField(max_length=64, blank=True, default='')

    def __str__(self):
        return f"{self.origem} -> {self.destino} ({self.tempo_minutos} min)"


class CacheConsultaMapas(models.Model):
    chave = models.CharField(max_length=64, unique=True)
    dados = models.JSONField()
    criado_em = models.DateTimeField(auto_now=True)


class ConfiguracaoAutomacao(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    proximidade_parentesco_minutos = models.PositiveSmallIntegerField(default=15,
        validators=[MinValueValidator(0), MaxValueValidator(240)],
        verbose_name='Limite de proximidade familiar (minutos)')

    def clean(self):
        super().clean()
        if self.pk != 1:
            raise ValidationError('Existe uma única configuração geral da automação.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class AprovacaoGrade(models.Model):
    semana = models.DateField()
    assinatura = models.CharField(max_length=64)
    aprovado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    aprovado_em = models.DateTimeField(auto_now_add=True)
    total_aulas = models.PositiveIntegerField()
    pendentes = models.PositiveIntegerField(default=0)
    parcial = models.BooleanField(default=False)

    class Meta:
        ordering = ('-aprovado_em',)
        constraints = [models.UniqueConstraint(fields=['semana', 'assinatura'], name='aprovacao_semana_versao')]

# 5. TABELA DE HORÁRIOS DE AULA
class AvisoGradeEmail(models.Model):
    aprovacao = models.ForeignKey(AprovacaoGrade, on_delete=models.CASCADE, related_name='avisos_email')
    professor = models.ForeignKey(Professor, on_delete=models.PROTECT)
    destinatario = models.EmailField(blank=True)
    assinatura_grade = models.CharField(max_length=64)
    assunto = models.CharField(max_length=200)
    corpo = models.TextField()
    estado = models.CharField(max_length=20, default='pendente')
    tentativas = models.PositiveIntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['aprovacao', 'professor'], name='aviso_aprovacao_professor')]


class HorarioAula(models.Model):
    nome = models.CharField(max_length=20) 
    hora_inicio = models.TimeField() 
    hora_fim = models.TimeField()    

    def __str__(self):
        return f"{self.nome} ({self.hora_inicio.strftime('%H:%M')})"

    def clean(self):
        super().clean()
        if self.hora_inicio and self.hora_fim and self.hora_fim <= self.hora_inicio:
            raise ValidationError('A hora final deve ser posterior à inicial, no mesmo dia.')
        if self.hora_inicio and self.hora_fim and HorarioAula.objects.filter(
                hora_inicio=self.hora_inicio, hora_fim=self.hora_fim).exclude(pk=self.pk).exists():
            raise ValidationError('Já existe um horário com esse início e fim. Reutilize o cadastro existente.')


class CadastroAtomico(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from django.db import transaction
        with transaction.atomic():
            self.full_clean()
            return super().save(*args, **kwargs)


class Curso(CadastroAtomico):
    nome = models.CharField(max_length=100, unique=True)
    observacoes = models.TextField(blank=True)

    @property
    def aulas_semanais(self):
        return sum(self.matriz.values_list('quantidade_semana', flat=True))

    @property
    def minutos_semanais(self):
        return self.aulas_semanais * 50

    def __str__(self):
        return self.nome


class MatrizCurricular(CadastroAtomico):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='matriz')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    quantidade_semana = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['curso', 'disciplina'], name='matriz_curso_disciplina')]

    def clean(self):
        super().clean()
        if not self.curso_id or not self.disciplina_id or not self.quantidade_semana:
            return
        from collections import Counter
        from .restricoes import segunda_da_semana
        for demanda in DemandaAula.objects.filter(turma__curso_id=self.curso_id, disciplina_id=self.disciplina_id):
            if not demanda.origem_curso:
                raise ValidationError('Há demanda manual nesta disciplina. Revise o vínculo antes de usar a matriz.')
            semanas = Counter(segunda_da_semana(d) for d in demanda.alocacaograde_set.values_list('data', flat=True))
            if semanas and max(semanas.values()) > self.quantidade_semana:
                raise ValidationError({'quantidade_semana': 'A redução excederia uma semana já salva. Preserve a matriz histórica ou crie outro curso/turma.'})


class Turma(CadastroAtomico):
    materias_fixas = models.BooleanField(default=False, help_text='Opcional: restringir a automação aos professores de horários curriculares fixos. Desmarcado: organizar matérias e professores.')
    curso = models.ForeignKey(Curso, null=True, blank=True, on_delete=models.PROTECT, related_name='turmas')
    turno_principal = models.CharField(max_length=5, blank=True, choices=[('manha', 'Manhã'), ('tarde', 'Tarde')], help_text='Vazio preserva o calendário legado. Configurado: quatro aulas por dia útil.')
    dia_contraturno = models.PositiveSmallIntegerField(null=True, blank=True, choices=list(enumerate(('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta'))))

    def permite_horario(self, dia, horario):
        if not self.turno_principal:
            return dia in self.dias_semana and any(h.pk == horario.pk for h in self.horarios.all())
        from .jornada import horarios_padrao
        padrao = horarios_padrao()
        principal = padrao[:4] if self.turno_principal == 'manha' else padrao[4:]
        contra = padrao[4:] if self.turno_principal == 'manha' else padrao[:4]
        intervalo = (horario.hora_inicio, horario.hora_fim)
        return (dia in self.dias_semana and dia < 5 and (
            intervalo in [(i, f) for _, i, f in principal]
            or (dia == self.dia_contraturno and intervalo in [(i, f) for _, i, f in contra])))

    def clean(self):
        super().clean()
        if self.dia_contraturno is not None and (not self.turno_principal or self.dia_contraturno not in self.dias_semana):
            raise ValidationError('O contraturno exige turno principal e dia entre os dias de aula.')
        if self.pk:
            anterior = Turma.objects.filter(pk=self.pk).first()
            if anterior and anterior.curso_id != self.curso_id and self.alocacaograde_set.exists():
                raise ValidationError('Turma com aulas salvas: preserve o curso histórico e crie outra turma para o novo curso.')
            if self.curso_id and self.demandas.filter(origem_curso=False, disciplina_id__in=self.curso.matriz.values('disciplina_id')).exists():
                raise ValidationError('Há demanda manual para esta matriz. Revise-a antes de vincular o curso; as demandas existentes serão preservadas.')

    nome = models.CharField(max_length=80)
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name='turmas')
    dias_semana = models.JSONField(default=dias_uteis, validators=[validar_dias_semana],
                                  help_text='0=segunda, 1=terça, …, 6=domingo. Exemplo: [0,1,2,3,4].')
    horarios = models.ManyToManyField(HorarioAula, help_text='Marque os horários em que esta turma pode receber aulas.')

    class Meta:
        ordering = ('unidade__nome', 'nome')
        constraints = [models.UniqueConstraint(fields=['unidade', 'nome'], name='turma_nome_por_unidade')]

    def __str__(self):
        return f'{self.nome} — {self.unidade}'


class DemandaAula(models.Model):
    turma = models.ForeignKey(Turma, on_delete=models.PROTECT, related_name='demandas')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT)
    quantidade_semana = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(100)])
    professor = models.ForeignKey(Professor, null=True, blank=True, on_delete=models.PROTECT,
                                  help_text='Opcional. Deixe vazio para o gerador escolher um professor habilitado.')
    ativa = models.BooleanField(default=True)
    origem_curso = models.BooleanField(default=False, editable=False)

    class Meta:
        verbose_name = 'demanda semanal de aulas'
        verbose_name_plural = 'demandas semanais de aulas'
        constraints = [models.UniqueConstraint(fields=['turma', 'disciplina'], name='demanda_turma_disciplina')]

    def clean(self):
        super().clean()
        if self.origem_curso and self.turma_id:
            item = MatrizCurricular.objects.filter(curso_id=self.turma.curso_id, disciplina_id=self.disciplina_id).first()
            if item and (not self.ativa or self.quantidade_semana != item.quantidade_semana):
                raise ValidationError('Edite a carga e os componentes na matriz do curso. A demanda é sincronizada automaticamente.')
            if not item and self.ativa:
                raise ValidationError('Componente removido da matriz: mantenha a demanda inativa para preservar o histórico.')
        if self.professor_id and self.disciplina_id and not self.professor.disciplinas.filter(pk=self.disciplina_id).exists():
            raise ValidationError({'professor': 'O professor não está habilitado nesta disciplina.'})

    def __str__(self):
        return f'{self.turma} / {self.disciplina.nome}: {self.quantidade_semana} aulas por semana'


class HorarioCurricular(CadastroAtomico):
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='distribuicao_curricular')
    demanda = models.ForeignKey(DemandaAula, on_delete=models.PROTECT, related_name='horarios_curriculares')
    dia_semana = models.PositiveSmallIntegerField(choices=list(enumerate(
        ('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'))))
    horario = models.ForeignKey(HorarioAula, on_delete=models.PROTECT)

    class Meta:
        ordering = ('dia_semana', 'horario__hora_inicio')
        constraints = [models.UniqueConstraint(fields=['turma', 'dia_semana', 'horario'], name='curriculo_turma_dia_horario')]

    def clean(self):
        super().clean()
        if not all((self.turma_id, self.demanda_id, self.horario_id)) or self.dia_semana is None:
            return
        if self.demanda.turma_id != self.turma_id or not self.demanda.ativa:
            raise ValidationError('Selecione uma demanda ativa desta turma.')
        if not self.turma.permite_horario(self.dia_semana, self.horario):
            raise ValidationError('Horário fora do calendário da turma.')
        outros = HorarioCurricular.objects.filter(turma__unidade_id=self.turma.unidade_id,
            dia_semana=self.dia_semana).exclude(pk=self.pk).select_related('horario')
        for outro in outros:
            if (self.horario.hora_inicio < outro.horario.hora_fim
                    and outro.horario.hora_inicio < self.horario.hora_fim):
                raise ValidationError('A unidade já tem uma matéria neste intervalo. Paralelo entre turmas permanece bloqueado.')
        if self.demanda.horarios_curriculares.exclude(pk=self.pk).count() >= self.demanda.quantidade_semana:
            raise ValidationError('Quantidade de horários excede a carga semanal desta disciplina.')

    def __str__(self):
        return f'{self.turma} / {self.demanda.disciplina.nome} / {self.get_dia_semana_display()} / {self.horario}'


class DisponibilidadeHorario(models.Model):
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)
    data = models.DateField()
    horario = models.ForeignKey(HorarioAula, on_delete=models.CASCADE)
    disponivel = models.BooleanField(default=True,
        help_text='Esta decisão específica tem prioridade sobre a disponibilidade de manhã/tarde.')

    class Meta:
        verbose_name = 'disponibilidade por horário'
        verbose_name_plural = 'disponibilidades por horário'
        constraints = [models.UniqueConstraint(fields=['professor', 'data', 'horario'], name='disponibilidade_slot_unica')]

    def __str__(self):
        return f'{self.professor} — {self.data:%d/%m/%Y} — {self.horario}'

# 6. TABELA DE DISPONIBILIDADE
class Disponibilidade(models.Model):
    data = models.DateField() 
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name='disponibilidades')
    disponivel_manha = models.BooleanField(default=False)
    disponivel_tarde = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.data} - {self.professor.nome} (M: {self.disponivel_manha}, T: {self.disponivel_tarde})"

# 7. A GRADE HORÁRIA (Alocação)
class AlocacaoGrade(models.Model):
    data = models.DateField() 
    horario = models.ForeignKey(HorarioAula, on_delete=models.CASCADE)
    unidade = models.ForeignKey(Unidade, on_delete=models.CASCADE)
    sala = models.ForeignKey(Sala, null=True, blank=True, on_delete=models.PROTECT)
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, null=True, blank=True)
    motivo_pendencia = models.CharField(max_length=240, blank=True, default='')
    turma = models.ForeignKey(Turma, null=True, blank=True, on_delete=models.PROTECT)
    disciplina = models.ForeignKey(Disciplina, null=True, blank=True, on_delete=models.PROTECT)
    demanda = models.ForeignKey(DemandaAula, null=True, blank=True, on_delete=models.PROTECT)

    # ===== SISTEMA DE EXCEÇÕES (Permitir desvios autorizados) =====
    eh_excecao_limite_aulas = models.BooleanField(
        default=False, 
        help_text="Autorizar exceção de limite de aulas/dia"
    )
    motivo_excecao_limite = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Justificativa para exceção de limite"
    )
    
    eh_excecao_horario = models.BooleanField(
        default=False, 
        help_text="Permitir duplicação de horário (raro)"
    )
    motivo_excecao_horario = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Justificativa para exceção de horário"
    )
    
    eh_excecao_deslocamento = models.BooleanField(
        default=False, 
        help_text="Autorizar deslocamento com tempo insuficiente"
    )
    motivo_excecao_deslocamento = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Justificativa para exceção de deslocamento"
    )
    
    eh_excecao_area_acumulo = models.BooleanField(
        default=False, 
        help_text="Permitir acúmulo de aulas da mesma área"
    )
    motivo_excecao_area_acumulo = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Justificativa para exceção de acúmulo de área"
    )
    
    # ===== AUDITORIA =====
    criado_em = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True, null=True, blank=True)
    autorizado_por = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Usuário que autorizou a exceção"
    )

    def __str__(self):
        return f"{self.data} - {self.unidade} - {self.horario}: {self.professor}"

    def clean(self):
        super().clean()
        if self.data and self.horario_id and self.unidade_id:
            from .restricoes import validar_alocacao_individual
            validar_alocacao_individual(self)
