#!/usr/bin/env python
"""
Script para popular banco de dados com dados de teste
Execute com: python popular_dados_teste.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configuracao_site.settings')
django.setup()

from grade.models import Unidade, Professor, HorarioAula, Disciplina, MatrizDistancia

print("🚀 Populando banco de dados com dados de teste...\n")

# ===== UNIDADES =====
print("📍 Criando unidades...")
u1, _ = Unidade.objects.get_or_create(
    nome="Unidade Hidaka",
    defaults={"responsavel": "João Silva", "endereco": "Rua A, 123", "cidade": "São Paulo", "cep": "01000-000"}
)
u2, _ = Unidade.objects.get_or_create(
    nome="Unidade Justiniano",
    defaults={"responsavel": "Maria Santos", "endereco": "Rua B, 456", "cidade": "São Paulo", "cep": "02000-000"}
)
print(f"✅ Unidades criadas: {u1.nome}, {u2.nome}\n")

# ===== DISCIPLINAS =====
print("📚 Criando disciplinas...")
d1, _ = Disciplina.objects.get_or_create(nome="Matemática", defaults={"area": "EXATAS"})
d2, _ = Disciplina.objects.get_or_create(nome="Português", defaults={"area": "HUMANAS"})
d3, _ = Disciplina.objects.get_or_create(nome="Biologia", defaults={"area": "BIOLOGICAS"})
d4, _ = Disciplina.objects.get_or_create(nome="História", defaults={"area": "HUMANAS"})
print(f"✅ Disciplinas criadas: {d1.nome}, {d2.nome}, {d3.nome}, {d4.nome}\n")

# ===== PROFESSORES =====
print("👨‍🏫 Criando professores...")
p1, _ = Professor.objects.get_or_create(
    nome="Prof. João",
    defaults={
        "meio_de_transporte": "PARTICULAR",
        "limite_aulas": 5,
        "telefone": "11999999999",
        "email": "joao@ccm.com"
    }
)
if not p1.disciplinas.exists():
    p1.disciplinas.add(d1)
if not p1.unidades_permitidas.exists():
    p1.unidades_permitidas.add(u1, u2)

p2, _ = Professor.objects.get_or_create(
    nome="Prof. Maria",
    defaults={
        "meio_de_transporte": "PUBLICO",
        "limite_aulas": 4,
        "telefone": "11988888888",
        "email": "maria@ccm.com"
    }
)
if not p2.disciplinas.exists():
    p2.disciplinas.add(d2)
if not p2.unidades_permitidas.exists():
    p2.unidades_permitidas.add(u1, u2)

p3, _ = Professor.objects.get_or_create(
    nome="Prof. Carlos",
    defaults={
        "meio_de_transporte": "OUTRO",
        "limite_aulas": 6,
        "telefone": "11977777777",
        "email": "carlos@ccm.com"
    }
)
if not p3.disciplinas.exists():
    p3.disciplinas.add(d3)
if not p3.unidades_permitidas.exists():
    p3.unidades_permitidas.add(u1, u2)

p4, _ = Professor.objects.get_or_create(
    nome="Prof. Ana",
    defaults={
        "meio_de_transporte": "PARTICULAR",
        "limite_aulas": 5,
        "telefone": "11966666666",
        "email": "ana@ccm.com"
    }
)
if not p4.disciplinas.exists():
    p4.disciplinas.add(d4)
if not p4.unidades_permitidas.exists():
    p4.unidades_permitidas.add(u1, u2)

print(f"✅ Professores criados: {p1.nome}, {p2.nome}, {p3.nome}, {p4.nome}\n")

# ===== HORÁRIOS =====
print("⏰ Criando horários...")
h1, _ = HorarioAula.objects.get_or_create(nome="1ª aula", defaults={"hora_inicio": "08:00", "hora_fim": "08:50"})
h2, _ = HorarioAula.objects.get_or_create(nome="2ª aula", defaults={"hora_inicio": "08:50", "hora_fim": "09:40"})
h3, _ = HorarioAula.objects.get_or_create(nome="3ª aula", defaults={"hora_inicio": "09:40", "hora_fim": "10:30"})
h4, _ = HorarioAula.objects.get_or_create(nome="Intervalo", defaults={"hora_inicio": "10:30", "hora_fim": "10:50"})
h5, _ = HorarioAula.objects.get_or_create(nome="4ª aula", defaults={"hora_inicio": "10:50", "hora_fim": "11:40"})
h6, _ = HorarioAula.objects.get_or_create(nome="5ª aula", defaults={"hora_inicio": "12:30", "hora_fim": "13:20"})
h7, _ = HorarioAula.objects.get_or_create(nome="6ª aula", defaults={"hora_inicio": "13:20", "hora_fim": "14:10"})
print(f"✅ Horários criados: {h1.nome}, {h2.nome}, {h3.nome}, {h5.nome}, {h6.nome}, {h7.nome}\n")

# ===== MATRIZ DE DISTÂNCIAS =====
print("🗺️ Criando matriz de distâncias...")
MatrizDistancia.objects.get_or_create(
    origem=u1,
    destino=u2,
    defaults={"tempo_minutos": 15}
)
MatrizDistancia.objects.get_or_create(
    origem=u2,
    destino=u1,
    defaults={"tempo_minutos": 15}
)
print("✅ Matriz de distâncias criada\n")

print("=" * 60)
print("✅ BANCO DE DADOS POPULADO COM SUCESSO!")
print("=" * 60)
print("\n📊 Resumo:")
print(f"  • Unidades: {Unidade.objects.count()}")
print(f"  • Professores: {Professor.objects.count()}")
print(f"  • Disciplinas: {Disciplina.objects.count()}")
print(f"  • Horários: {HorarioAula.objects.count()}")
print(f"  • Matriz de Distâncias: {MatrizDistancia.objects.count()}")
print("\n🌐 Acesse: http://localhost:8000")
print("🔐 Admin: http://localhost:8000/admin (admin / admin123)")
