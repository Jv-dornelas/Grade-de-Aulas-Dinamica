from django.db import models

# 1. TABELA DE UNIDADES / POLOS
class Unidade(models.Model):
    nome = models.CharField(max_length=50) # Ex: "DG", "JUSTI", "HIDAKA"
    responsavel = models.CharField(max_length=100) # Ex: "MEL", "KAROL"

    def __str__(self):
        return self.nome

# 2. TABELA DE PROFESSORES
class Professor(models.Model):
    # Opções para a área
    AREAS_CHOICES = [
        ('EXATAS', 'Exatas'),
        ('HUMANAS', 'Humanas'),
        ('BIOLOGICAS', 'Biológicas'),
    ]
    
    # NOVAS OPÇÕES PARA O TRANSPORTE (Cadastradas aqui!)
    TRANSPORTE_CHOICES = [
        ('PARTICULAR', 'Carro / Moto'),
        ('PUBLICO', 'Transporte Público'),
        ('OUTRO', 'A pé / Outro'),
    ]
    
    nome = models.CharField(max_length=100)
    disciplina = models.CharField(max_length=50)
    area = models.CharField(max_length=20, choices=AREAS_CHOICES, default='HUMANAS')
    
    # ATUALIZE ESTA LINHA ABAIXO:
    meio_de_transporte = models.CharField(
        max_length=20, 
        choices=TRANSPORTE_CHOICES, 
        default='PARTICULAR'
    )
    
    unidade_oficial = models.ForeignKey('Unidade', on_delete=models.SET_NULL, null=True, related_name='professores_oficiais')
    unidades_permitidas = models.ManyToManyField('Unidade', related_name='professores_permitidos')
    conjuge = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Casado(a) com")

    def __str__(self):
        return self.nome
    
# 3. TABELA DE HORÁRIOS DE AULA
class HorarioAula(models.Model):
    nome = models.CharField(max_length=20) # Ex: "1º AULA", "2º AULA"
    hora_inicio = models.TimeField() # Ex: 08:30
    hora_fim = models.TimeField()    # Ex: 09:45

    def __str__(self):
        return f"{self.nome} ({self.hora_inicio.strftime('%H:%M')})"

# 4. A GRADE HORÁRIA EM SI (Cada célula preenchida da sua tabela)
class AlocacaoGrade(models.Model):
    data = models.DateField() # O sábado específico, ex: 25/04/2026
    horario = models.ForeignKey(HorarioAula, on_delete=models.CASCADE)
    unidade = models.ForeignKey(Unidade, on_delete=models.CASCADE)
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.data} - {self.unidade} - {self.horario}: {self.professor}"
    
    # 5. TABELA DE DISPONIBILIDADE SEMANAL
class Disponibilidade(models.Model):
    data = models.DateField() # O sábado específico
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name='disponibilidades')
    disponivel_manha = models.BooleanField(default=False, verbose_name="Disponível de Manhã")
    disponivel_tarde = models.BooleanField(default=False, verbose_name="Disponível de Tarde")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.data} - {self.professor.nome} (M: {self.disponivel_manha}, T: {self.disponivel_tarde})"