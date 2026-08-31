from django.db import models

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

# 3. TABELA DE PROFESSORES
class Professor(models.Model):
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
    parente_vinculado = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Parente (Mesmo turno/unidade)")
    
    # NOVO CAMPO: Observações para o coordenador
    observacao = models.TextField(blank=True, null=True, help_text="Informações personalizadas para consulta na montagem da grade")

    def __str__(self):
        return self.nome

# 4. NOVO: MATRIZ DE DISTÂNCIAS INTERNAS
class MatrizDistancia(models.Model):
    origem = models.ForeignKey(Unidade, related_name='distancias_origem', on_delete=models.CASCADE)
    destino = models.ForeignKey(Unidade, related_name='distancias_destino', on_delete=models.CASCADE)
    tempo_minutos = models.PositiveIntegerField(help_text="Tempo médio de deslocamento em minutos")

    def __str__(self):
        return f"{self.origem} -> {self.destino} ({self.tempo_minutos} min)"

# 5. TABELA DE HORÁRIOS DE AULA
class HorarioAula(models.Model):
    nome = models.CharField(max_length=20) 
    hora_inicio = models.TimeField() 
    hora_fim = models.TimeField()    

    def __str__(self):
        return f"{self.nome} ({self.hora_inicio.strftime('%H:%M')})"

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
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.data} - {self.unidade} - {self.horario}: {self.professor}"