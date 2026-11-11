# Estrutura e responsabilidades

## Decisão para a primeira versão

Manter uma aplicação Django, `grade`, com módulos por responsabilidade. A base atual não exige vários apps, microserviços ou camadas artificiais. A reorganização inicial separa testes, documentação, dados históricos e artefatos sem modificar o fluxo de execução, as URLs ou o banco.

## Mapa dos módulos

| Responsabilidade | Arquivos |
|---|---|
| Configuração e entrada | `configuracao_site/`, `manage.py`, `grade/urls.py` |
| Dados e administração | `models.py`, `admin.py`, `migrations/` |
| Cursos e turmas | `cursos.py`, `forms_cursos.py`, `curriculo.py` |
| Jornada e validação | `jornada.py`, `restricoes.py` |
| Cálculo da proposta | `gerador.py`, `planejamento_curso.py` |
| Prévia, confirmação e aprovação | `automacao.py`, `aprovacao.py`, `edicao.py` |
| Replicação por período | `replicacao.py` |
| Projeções e exportação | `distribuicao.py`, `pdf_grade.py`, `mobile.py`, `dashboard.py` |
| Planejamento versus atendimento | `indicadores.py` |
| Cenários reproduzíveis isolados | `cenarios.py`, comando `preparar_cenario`, guia `docs/testes/CENARIOS.md` |
| Acesso e recuperação | `acesso.py`, `erros_acesso.py` |
| Cadastros legados e serviços | `views.py`, `services.py`, `unidades.py`, `disciplinas.py` |
| Ficha de professor e vínculos | `professores.py`, ProfessorForm |
| Parâmetros e exceções de disponibilidade | `parametros.py`, `restricoes_horario.py` |
| Espaços físicos e paralelismo | `salas.py`, modelo Sala, validação em `restricoes.py` |
| Mapas | `mapas.py` |
| API | `api.py`, `serializers.py` |
| Apresentação | `templates/grade/`, `static/grade/`, `templatetags/` |
| Operações explícitas | `management/commands/` |
| Testes | `tests/test_*.py`, `tests/factories.py` |

Os módulos continuam importáveis pelos caminhos atuais (`grade.gerador`, `grade.automacao`, etc.). As migrações mantêm os nomes e a ordem anteriores. Caminhos de templates e arquivos estáticos permanecem iguais.

## Testes

O antigo `grade/tests.py` tornou-se `grade/tests/test_mobile.py`. Os arquivos `grade/test_*.py` foram reunidos em `grade/tests/`; seus imports relativos foram atualizados. O cenário compartilhado da grade está em `tests/factories.py`, em vez de testes dependerem de métodos de outra classe de testes.

Use `python manage.py test grade.tests` para a suíte ou `python manage.py test grade.tests.test_gerador` para um módulo. `python manage.py test grade` continua descobrindo a suíte. Os nomes antigos `grade.test_gerador` presentes em registros históricos deixaram de ser caminhos executáveis.

## Bancos e arquivos gerados

Não mover o banco ativo durante uso da aplicação. `db.sqlite3` e `db.automacao.sqlite3` continuam na raiz; `.env` não foi alterado. Snapshots `db.automacao.antes-*.sqlite3` foram movidos para `backups/` com conferência de hash. Nenhum banco foi migrado, populado ou limpo nesta organização.

A fixture histórica foi movida para `grade/fixtures/dados_ficticios.json`, onde o Django pode descobri-la. Sua presença não a carrega automaticamente. Os scripts antigos estão em `scripts/legacy/` porque não representam o fluxo atual de população e um deles apaga dados.

## Próximos passos de arquitetura

Há melhorias reais além de mover pastas, a realizar separadamente depois dos testes funcionais da primeira versão:

1. Extrair os cadastros de professor/unidade/disciplina de `views.py` em módulos pequenos, com testes dos formulários e regras de permissão.
2. Retirar os estilos inline remanescentes dos templates antigos. O cabeçalho já é compartilhado, mas ainda existe CSS antigo duplicado nessas páginas.
3. Separar o cálculo/validação da proposta da manipulação da sessão e mensagens HTTP em `automacao.py` e `edicao.py`, reduzindo dependências circulares.
4. Centralizar formulários de cadastro e seus erros para web, Admin e API aplicarem as mesmas regras.
5. Definir um procedimento reproduzível de cenários fictícios antes de ampliar a população de teste.

Esses pontos não foram apresentados como concluídos. Uma refatoração ampla imediatamente antes da apresentação aumentaria o risco sem melhorar o uso da versão atual.

## Convenções

- Testes em `grade/tests/test_<funcionalidade>.py`; cenários reutilizáveis em `factories.py`.
- Comandos operacionais novos em `management/commands/`, sem execução de escrita durante importação.
- Documentação nova em `docs/`; manter `README.md` como ponto de entrada e `AUTOMACAO.md` no caminho solicitado para as regras locais.
- Recursos visuais em `static/grade/`, templates reutilizáveis por inclusão/herança.
- `.editorconfig` define codificação, quebras de linha e indentação para novas edições; não foi aplicada formatação geral aos arquivos antigos.
- Não versionar segredos, bancos, backups ou artefatos gerados.
