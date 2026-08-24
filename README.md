#  Sistema de Gestão de Grade Horária e Alocação Docente 

> Aplicação web desenvolvida em Django para centralização, mapeamento de disponibilidade e otimização do processo de montagem de grade horária acadêmica.

---

##  Objetivo do Projeto

O objetivo deste sistema é substituir processos manuais e controles descentralizados em planilhas por uma solução centralizada. A plataforma permite mapear a disponibilidade de professores por unidade, visualizar turmas e gerenciar restrições de horários de forma ágil, reduzindo conflitos operacionais na gestão acadêmica.

---

##  Tecnologias Utilizadas

* **Linguagem:** Python 3.11
* **Framework Web:** Django 5.2
* **Banco de Dados:** SQLite (Desenvolvimento)
* **Containerização:** Docker & Docker Compose
* **Controle de Versão:** Git & GitHub

---

##  Funcionalidades Principais

* **Mapeamento de Disponibilidade:** Registro de restrições de dias e horários por docente.
* **Gestão de Unidades e Turmas:** Organização centralizada por campus ou local de aula.
* **Carga de Dados Fictícios:** Ingestão de massa de dados via script JSON para testes automatizados e demonstração do sistema.

---

##  Como Executar o Projeto Localmente (via Docker)

Todo o ambiente (Python, Django e dependências) já vem pronto dentro do container. Não é necessário instalar Python nem criar ambiente virtual (venv) na máquina.

### Pré-requisitos
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e em execução
* Git instalado

### Passo a Passo (primeira vez)

1. **Clonar o repositório:**
   ```bash
   git clone https://github.com/Jv-dornelas/Grade-de-Aulas-Dinamica.git
   cd Grade-de-Aulas-Dinamica
   ```

2. **Criar o arquivo de variáveis de ambiente:**

   Copie o exemplo e gere sua própria `SECRET_KEY`:
   ```bash
   copy .env.example .env
   ```
   Edite o `.env` e substitua o valor de `SECRET_KEY` por uma chave gerada com:
   ```bash
   docker compose run --rm web python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

3. **Subir o container:**
   ```bash
   docker compose up -d
   ```

4. **Aplicar as migrações do banco de dados:**
   ```bash
   docker exec grade-de-aulas-dinamica-web-1 python manage.py migrate
   ```

5. **Carregar os dados fictícios de teste:**
   ```bash
   docker exec grade-de-aulas-dinamica-web-1 python manage.py loaddata dados_ficticios.json
   ```

6. **Criar um usuário administrador (para acessar o /admin):**
   ```bash
   docker exec -it grade-de-aulas-dinamica-web-1 python manage.py createsuperuser
   ```

7. **Acessar a aplicação:**
   * App: [http://127.0.0.1:8000/grade](http://127.0.0.1:8000/grade)
   * Admin: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

---

### Uso no dia a dia (depois da primeira configuração)

Ligar o ambiente:
```bash
docker compose up -d
```

Parar o ambiente:
```bash
docker compose down
```

Rodar qualquer comando do Django (migrate, shell, createsuperuser, etc.):
```bash
docker exec grade-de-aulas-dinamica-web-1 python manage.py <comando>
```

Ver logs do container:
```bash
docker logs grade-de-aulas-dinamica-web-1
```

---

##  Estrutura do Projeto

```text
.
├── configuracao_site/   # Configurações globais do Django (settings, urls)
├── grade/                # App principal (models, views, templates)
├── .dockerignore         # Regras de exclusão do Docker
├── .env                  # Variáveis de ambiente locais (NÃO versionado)
├── .env.example          # Modelo de variáveis de ambiente (versionado)
├── .gitignore            # Regras de exclusão do Git
├── dados_ficticios.json  # Massa de dados de teste
├── docker-compose.yml    # Orquestrador de containers
├── Dockerfile            # Receita de construção do container
├── manage.py             # Utilitário de comando do Django
└── requirements.txt      # Dependências do projeto Python
```
