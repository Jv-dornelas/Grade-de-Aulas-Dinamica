from grade.models import Unidade, Professor, HorarioAula, Disciplina

# Unidades
u1 = Unidade.objects.create(nome="Unidade Norte", responsavel="João Silva", endereco="Rua A, 123")
u2 = Unidade.objects.create(nome="Unidade Sul", responsavel="Maria Santos", endereco="Rua B, 456")

# Disciplinas
d1 = Disciplina.objects.create(nome="Matemática", area="EXATAS")
d2 = Disciplina.objects.create(nome="Português", area="HUMANAS")
d3 = Disciplina.objects.create(nome="Biologia", area="BIOLOGICAS")

# Professores
p1 = Professor.objects.create(nome="Prof. João", meio_de_transporte="PARTICULAR", limite_aulas=5)
p1.disciplinas.add(d1)
p1.unidades_permitidas.add(u1, u2)

p2 = Professor.objects.create(nome="Prof. Maria", meio_de_transporte="PUBLICO", limite_aulas=4)
p2.disciplinas.add(d2)
p2.unidades_permitidas.add(u1, u2)

p3 = Professor.objects.create(nome="Prof. Carlos", meio_de_transporte="OUTRO", limite_aulas=6)
p3.disciplinas.add(d3)
p3.unidades_permitidas.add(u1, u2)

# Horários
h1 = HorarioAula.objects.create(nome="1ª aula", hora_inicio="08:00", hora_fim="08:50")
h2 = HorarioAula.objects.create(nome="2ª aula", hora_inicio="08:50", hora_fim="09:40")
h3 = HorarioAula.objects.create(nome="3ª aula", hora_inicio="09:40", hora_fim="10:30")
h4 = HorarioAula.objects.create(nome="4ª aula", hora_inicio="10:50", hora_fim="11:40")
h5 = HorarioAula.objects.create(nome="5ª aula", hora_inicio="12:30", hora_fim="13:20")
h6 = HorarioAula.objects.create(nome="6ª aula", hora_inicio="13:20", hora_fim="14:10")

print("✅ Dados criados com sucesso!")
exit()
