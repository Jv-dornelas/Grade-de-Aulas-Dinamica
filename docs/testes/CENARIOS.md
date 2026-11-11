# Cenários reproduzíveis do MVP

Os cenários usam bancos separados em `tmp/cenarios/`. Não são misturados ao histórico ou à cópia `db.automacao.sqlite3`. Nenhum comando deste guia apaga o banco existente. O comando recusa o banco original, a cópia principal e destinos que apontem por links para outros arquivos.

## Resultados esperados na semana de 01/03/2027

| Cenário | Carga | Distribuídas | Com professor | Sem professor | Sem horário |
|---|---:|---:|---:|---:|---:|
| `completo` | 24 | 24 | 24 | 0 | 0 |
| `falta_professor` | 24 | 24 | 12 | 12 | 0 |
| `deslocamento` | 2 | 2 | 1 | 1 | 0 |
| `disputa_sala` | 48 | 24 | 24 | 0 | 24 |
| `paralelo` | 48 | 48 | 48 | 0 | 0 |

`completo` usa uma turma e docentes habilitados. `falta_professor` deixa uma disciplina sem docente habilitado. `disputa_sala` tem duas turmas e uma sala; `paralelo` oferece duas salas para comparar o resultado. São cursos fictícios de 24 aulas, com 20 no turno principal e 4 no contraturno.

`deslocamento` usa uma carga reduzida de duas aulas, em unidades distintas e horários consecutivos, para isolar uma única regra: um docente não consegue fazer o trajeto de 30 minutos no intervalo disponível. Alterar o trajeto para zero no teste automatizado permite atender as duas aulas, comprovando a causa. Não é uma matriz escolar sugerida.

## Preparar e validar

Execute na raiz do projeto, com o serviço Docker existente em execução:

```powershell
docker compose exec -e SQLITE_NAME=tmp/cenarios/db.cenario.completo.sqlite3 web python manage.py preparar_cenario --cenario completo
docker compose exec -e SQLITE_NAME=tmp/cenarios/db.cenario.falta_professor.sqlite3 web python manage.py preparar_cenario --cenario falta_professor
docker compose exec -e SQLITE_NAME=tmp/cenarios/db.cenario.deslocamento.sqlite3 web python manage.py preparar_cenario --cenario deslocamento
docker compose exec -e SQLITE_NAME=tmp/cenarios/db.cenario.disputa_sala.sqlite3 web python manage.py preparar_cenario --cenario disputa_sala
docker compose exec -e SQLITE_NAME=tmp/cenarios/db.cenario.paralelo.sqlite3 web python manage.py preparar_cenario --cenario paralelo
```

Cada execução compara esperado/obtido e escreve um relatório `.json` ao lado do banco. Repetir o comando valida os dados existentes sem duplicá-los. Se o banco tiver outros dados ou o resultado divergir, há erro explícito; não existe limpeza automática. Use `--semana AAAA-MM-DD` na primeira preparação para outra semana; reutilizar um banco de outro período não o sobrescreve.

O comando prepara cadastros e verifica a prévia, mas **não grava nem aprova aulas**. Os cinco cenários acima já foram preparados e conferidos nesta cópia local.

## Conferir um cenário pelo navegador

É possível abrir um ambiente temporário na porta 8001, mantendo o sistema atual na 8000. Exemplo para `completo`:

```powershell
docker compose exec -e SQLITE_NAME=tmp/cenarios/db.cenario.completo.sqlite3 web python manage.py createsuperuser
docker compose run --rm --no-deps -p 127.0.0.1:8001:8000 -e SQLITE_NAME=tmp/cenarios/db.cenario.completo.sqlite3 web python manage.py runserver --noreload 0.0.0.0:8000
```

A conta é criada apenas no banco do cenário, com senha escolhida pelo operador. Não foram criadas contas/senhas automáticas. O segundo comando fica aberto; acesse `http://localhost:8001/inicio/`, entre e selecione a semana de 01/03/2027. Para encerrar o ambiente temporário, use Ctrl+C nesse terminal. Isso não modifica o `.env` nem o servidor principal. Para outro cenário, substitua o nome do arquivo nos dois comandos.

## Roteiro de conferência

1. Gerar a grade: estado **Prévia em revisão — ainda não salva**, com indicadores incluindo a proposta.
2. Comparar aulas distribuídas, com professor, sem professor e sem horário com a tabela.
3. Trocar dia/semana e professor/unidade/curso/turma; conferir que a proposta permanece.
4. Usar **Salvar sem aprovar**: dados persistem, mas não há registro de aprovação.
5. Revisar a semana e aprovar. Se parcial, exigir aceite explícito; o número de pendências aceitas aparece sem zerar as pendências reais.
6. Atribuir um professor válido ou alterar uma aula: a aprovação anterior deixa de valer e a versão atual exige nova revisão.
7. Replicar para outra semana e conferir conflitos, idempotência, cards e PDF. A aprovação não é copiada.

Após salvar/editar aulas em um cenário, a validação passa a considerar essas aulas fixas junto com novas propostas. Mudanças intencionais nos cadastros podem fazer o relatório divergir; isso não dispara reset.
