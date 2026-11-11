# Grade de Aulas Dinâmica

Sistema Django do Cursinho Chico Mendes para cadastros, planejamento semanal, distribuição de matérias e professores, aprovação e consulta mobile.

Versão funcional com automação semanal integrada. A publicação do código no GitHub não implanta o sistema nem transfere bancos ou credenciais. Não há deploy automático configurado por esta implementação.

## Acesso local

| Área | Endereço |
|---|---|
| Home e login da gestão | http://localhost:8000/inicio/ |
| Grade horária | http://localhost:8000/ |
| Consulta do professor | http://localhost:8000/mobile/ |
| Administração técnica | http://localhost:8000/admin/ |

A gestão exige conta ativa com permissão de equipe. O mobile utiliza conta vinculada a um professor. Não há credenciais no repositório.

## Executar o ambiente existente

Com Docker Desktop aberto, execute na raiz:

```powershell
docker compose up -d
```

O serviço local usa `runserver --noreload`. Após alterar código Python, reinicie:

```powershell
docker compose restart web
```

A configuração vem do `.env` local. Para uma instalação nova, utilize `.env.example` como referência; não substitua o `.env` de uma instalação existente.

Nesta cópia, o banco de trabalho é `db.automacao.sqlite3`. O original `db.sqlite3` é preservado. Confirme o banco efetivo e faça backup antes de migrar ou preparar cenários. Não execute os scripts históricos de população na base atual.

## Validação

```powershell
docker compose exec web python manage.py check
docker compose exec web python manage.py test grade.tests --noinput
docker compose exec web python manage.py makemigrations --check --dry-run
```

Para um módulo específico:

```powershell
docker compose exec web python manage.py test grade.tests.test_gerador --noinput
```

Os testes Django utilizam banco de teste separado. Não é necessário popular ou apagar o banco de trabalho para executá-los.

## Estrutura

```text
configuracao_site/       Configurações, URLs globais e interfaces ASGI/WSGI
grade/                   Aplicação Django
  models.py              Persistência e validações dos cadastros
  views.py, urls.py      Rotas e telas legadas preservadas
  gerador.py             Otimização de cobertura docente
  planejamento_curso.py  Distribuição curricular sem docente
  restricoes.py          Validações compartilhadas
  automacao.py           Prévia privada e confirmação
  aprovacao.py           Aprovação e controle de versão semanal
  curriculo.py           Sincronização da matriz com turmas
  tests/                 Testes por funcionalidade e cenário compartilhado
  fixtures/              Massa histórica de dados; não carregada automaticamente
  management/commands/   Comandos de manutenção e cenários locais
  migrations/            Histórico de evolução do banco
  templates/grade/       Templates web e mobile
  static/grade/          CSS, JavaScript e recursos mobile
docs/                    Guias, arquitetura, processos e retomada local
scripts/legacy/          Scripts antigos preservados como referência
android-app/             Aplicativo Android e instruções próprias
backups/                 Cópias locais dos bancos (não versionadas)
output/, tmp/, dist/     Artefatos locais de validação e compilação
manage.py                Entrada dos comandos Django
requirements.txt         Dependências Python
AUTOMACAO.md             Regras e histórico da implementação local
```

Bancos ativos e `.env` permanecem na raiz para preservar a configuração existente. Backups antigos foram apenas movidos para `backups/`, sem alteração do conteúdo.

## Documentação

- [Mapa da documentação](docs/README.md)
- [Arquitetura e decisões de organização](docs/arquitetura/ESTRUTURA.md)
- [Regras e histórico da automação](AUTOMACAO.md)
- [Guia mobile](docs/guias/MOBILE.md)
- [Ponto de retomada local](docs/RETOMADA_LOCAL.md)
- [Cenários reproduzíveis do MVP](docs/testes/CENARIOS.md)
- [Proposta de hospedagem gratuita](docs/guias/HOSPEDAGEM_GRATUITA.md)

Antes de alterar regras da geração ou preparar dados, leia `AUTOMACAO.md`. Prévia não grava aulas; confirmação valida novamente os dados e detecta alterações concorrentes. As aulas existentes são preservadas como fixas.
