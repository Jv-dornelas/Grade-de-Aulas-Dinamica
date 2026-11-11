import os
import django
from datetime import time

# Configura o script para reconhecer o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configuracao_site.settings')
django.setup()

from grade.models import Unidade, Disciplina, Professor, MatrizDistancia, HorarioAula

def popular():
    print("Limpando dados para evitar duplicidade...")
    Unidade.objects.all().delete()
    Disciplina.objects.all().delete()
    Professor.objects.all().delete()
    HorarioAula.objects.all().delete()

    print(" Criando Unidades...")
    u1 = Unidade.objects.create(nome="Polo Centro", responsavel="Carlos", endereco="Rua Principal, 100", cidade="São Paulo")
    u2 = Unidade.objects.create(nome="Polo Zona Sul", responsavel="Ana", endereco="Av. Sul, 500", cidade="São Paulo")

    print(" Criando Disciplinas...")
    d1 = Disciplina.objects.create(nome="Matemática", area="EXATAS")
    d2 = Disciplina.objects.create(nome="História", area="HUMANAS")
    d3 = Disciplina.objects.create(nome="Biologia", area="BIOLOGICAS")

    print(" Criando Professores...")
    p1 = Professor.objects.create(
        nome="João Silva", telefone="11999999999", email="joao@teste.com", 
        meio_de_transporte="PARTICULAR", limite_aulas=4, unidade_oficial=u1, 
        observacao="Professor de Exatas. Chega sempre às 08h."
    )
    p1.disciplinas.add(d1)
    p1.unidades_permitidas.add(u1, u2)

    p2 = Professor.objects.create(
        nome="Maria Souza", telefone="11888888888", email="maria@teste.com", 
        meio_de_transporte="PUBLICO", limite_aulas=6, unidade_oficial=u2
    )
    p2.disciplinas.add(d2, d3)
    p2.unidades_permitidas.add(u2)

    print("Criando Matriz de Distância...")
    MatrizDistancia.objects.create(origem=u1, destino=u2, tempo_minutos=30)
    MatrizDistancia.objects.create(origem=u2, destino=u1, tempo_minutos=35)

    print("Criando Horários de Aula...")
    HorarioAula.objects.create(nome="1ª Aula", hora_inicio=time(8, 0), hora_fim=time(8, 50))
    HorarioAula.objects.create(nome="2ª Aula", hora_inicio=time(8, 50), hora_fim=time(9, 40))

    print("Banco populado com sucesso! Já pode testar.")

if __name__ == '__main__':
    popular()