#  Sistema de Gestão de Grade Horária e Alocação Docente 

> Aplicação web desenvolvida em Django para centralização, mapeamento de disponibilidade e otimização do processo de montagem de grade horária acadêmica.

---

##  Objetivo do Projeto

O objetivo deste sistema é substituir processos manuais e controles descentralizados em planilhas por uma solução centralizada. A plataforma permite mapear a disponibilidade de professores por unidade, visualizar turmas e gerenciar restrições de horários de forma ágil, reduzindo conflitos operacionais na gestão acadêmica.

---

##  Tecnologias Utilizadas

* **Linguagem:** Python 3.x
* **Framework Web:** Django
* **Banco de Dados:** SQLite (Desenvolvimento)
* **Controle de Versão:** Git & GitHub

---

##  Funcionalidades Principais

* **Mapeamento de Disponibilidade:** Registro de restrições de dias e horários por docente.
* **Gestão de Unidades e Turmas:** Organização centralizada por campus ou local de aula.
* **Carga de Dados Fictícios:** Ingestão de massa de dados via script JSON para testes automatizados e demonstração do sistema.

---

##  Como Executar o Projeto Localmente

### Pré-requisitos
* Python 3.10+ instalado
* Git instalado

### Passo a Passo

1. **Clonar o repositório:**
git clone [https://github.com/Jv-dornelas/Grade-de-Aulas-Dinamica.git](https://github.com/Jv-dornelas/Grade-de-Aulas-Dinamica.git)
cd Grade-de-Aulas-Dinamica

2. **Criar e ativar o ambiente virtual (venv):**
python -m venv venv
.\venv\Scripts\activate

3. **Instalar as dependências:**
pip install django

4. **Executar as migrações e carregar dados de teste:**
python manage.py migrate
python manage.py loaddata dados_ficticios.json

5. **Iniciar o servidor de desenvolvimento:**
python manage.py runserver

Acesse a aplicação em: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## Estrutura do Projeto

```text
.
├── configuracao_site/   # Configurações globais do Django (settings, urls)
├── grade/               # App principal (models, views, templates)
├── .dockerignore        # Regras de exclusão do Docker
├── .gitignore           # Regras de exclusão do Git
├── dados_ficticios.json # Massa de dados de teste
├── docker-compose.yml   # Orchestrador de containers
├── Dockerfile           # Receita de construção do container
├── manage.py            # Utilitário de comando do Django
└── requirements.txt     # Dependências do projeto Python
