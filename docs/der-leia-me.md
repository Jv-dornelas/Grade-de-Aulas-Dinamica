# DER para apresentação

O arquivo `diagrama-entidade-relacionamento.puml` contém cinco blocos independentes `@startuml ... @enduml`. Cada bloco gera uma imagem. Para usar um editor que mostre apenas um diagrama por vez, copie o bloco correspondente inteiro ou posicione o cursor nele na extensão PlantUML.

As cinco vistas compõem o mesmo DER. Nenhuma tabela foi removida: são 10 entidades próprias, o usuário do Django e três tabelas associativas. Os 25 relacionamentos e todos os campos dos modelos próprios foram conferidos com `grade/models.py`.

## Ordem de apresentação

1. **Professores:** conta de acesso, unidade oficial, unidades permitidas, habilitações e parentesco.
2. **Planejamento:** unidades, turmas, horários permitidos e demandas semanais.
3. **Disponibilidades:** decisão por turno e decisão específica por horário.
4. **Alocações:** aula agendada e suas referências, exceções e auditoria.
5. **Deslocamentos:** origem, destino e tempo entre unidades.

As imagens PNG e SVG estão em `der-renderizado/`. O PDF para apresentação está em `../output/pdf/diagrama-entidade-relacionamento-revisado.pdf`. Os SVG permitem ampliar sem perda de nitidez. O PDF tem cinco páginas A3 em paisagem.

## Como ler as cardinalidades

O número junto a uma entidade indica quantos registros dela podem estar relacionados a um registro da entidade na outra ponta.

Por exemplo, `Professor "1" -- "0..*" AlocacaoGrade` significa: cada alocação tem exatamente um professor; um professor pode ter zero ou muitas alocações.

`0..1` significa zero ou um. `0..*` significa zero ou muitos. O símbolo `*` **dentro de um bloco, antes de um campo**, significa NOT NULL, não uma cardinalidade.

Os blocos cinza apresentam apenas o identificador de uma entidade detalhada em outra vista. Professor no papel de parente é a mesma tabela Professor; Unidade nos papéis de origem e destino é a mesma tabela Unidade. Essas repetições evitam linhas sobrepostas e não criam tabelas novas.

## Resultado da revisão dos relacionamentos

Não foi identificada divergência entre as cardinalidades do script anterior e os modelos atuais. A revisão corrigiu a apresentação e tornou explícitos os casos que podiam gerar interpretação errada:

| Vínculo | Leitura conforme o modelo atual |
|---|---|
| Usuário e Professor | Opcional nos dois lados: um usuário pode não ser professor; um professor pode não ter conta. No máximo uma conta por professor e um professor por conta. |
| Unidade oficial | Um professor pode ter zero ou uma unidade oficial. Uma unidade pode ser oficial para vários professores. |
| Parente vinculado | Cada professor aponta para zero ou um outro professor. Vários professores podem apontar para o mesmo professor; a FK não é única. A preferência na lógica de negócio vale nos dois sentidos. |
| Habilitações, unidades permitidas e horários de turma | São N:N, resolvidos por três tabelas associativas com unicidade no par de FKs. |
| Professor da demanda | Opcional: cada demanda pode fixar zero ou um professor; um professor pode ser fixado em várias demandas. |
| Alocação | Professor, unidade e horário são obrigatórios. Turma, disciplina, demanda e usuário autorizador são opcionais no banco atual. |
| Matriz de distância | Cada registro tem exatamente uma origem e um destino, ambos referenciando Unidade por FKs distintas. Não existe exigência de tempo simétrico ou unicidade do par no modelo. |

As FKs de turma e disciplina em AlocacaoGrade foram mantidas, mesmo com a referência à demanda. Elas existem no código atual. Uma eventual normalização ou mudança de obrigatoriedade exigiria alterar os modelos e as migrações, não apenas o diagrama.

As regras de exclusão, os nomes físicos das tabelas, os campos completos e as validações estão em `der-dicionario.md`. As tabelas internas de grupos, permissões, sessões e logs do Django permanecem fora do escopo.

## Verificação realizada

- Renderização local dos cinco blocos com PlantUML, em PNG e SVG.
- Inspeção visual das cinco imagens e do PDF resultante.
- Comparação das 25 associações com as declarações ForeignKey, OneToOneField e ManyToManyField dos modelos, incluindo nulabilidade e multiplicidade.
- Comparação dos campos de todas as entidades próprias e tabelas associativas com os modelos.

Nenhum modelo, regra de negócio ou banco de dados foi alterado.
