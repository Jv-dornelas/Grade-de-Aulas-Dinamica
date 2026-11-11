# Retomada local — 09/11/2026

## Auditoria dos inputs — 11/11/2026

Critérios da automação mapeados em `docs/guias/CADASTROS_AUTOMACAO.md`. Entradas que faltavam na interface principal agora em Professor → Restrições por horário (`/professores/restricoes/`) e Professor → Critérios da automação (`/configuracoes/`). Ficha do professor usa ProfessorForm compartilhado e inclui vínculo de conta mobile existente, com proteção de concorrência e rollback de mudanças incompatíveis com aulas salvas. Criação de contas/permissões continua técnica no Admin, fora do cálculo da grade. Não alterado parâmetro ou cadastro real automaticamente.

Migração 0012 aplicada somente na cópia após backup `backups/db.automacao.antes-cadastros-criterios-20261111_192857.sqlite3`; tabelas anteriores idênticas ao backup e original preservado. 256 testes passaram. Próxima rodada pode conferir visualmente as novas fichas e realizar o roteiro de cenários.

## Ajustes do MVP — 11/11/2026

Indicadores separam distribuídas/com professor/sem professor/sem horário/pendências aceitas. Estado e próxima ação explícitos, prévia expirada bloqueada, Salvar sem aprovar separado de Aprovar e gravar. Formulários compartilham `formularios.css` em 22 telas-base/legadas. 246 testes passaram, sem migração ou população do banco principal; 732 aulas preservadas.

Cinco bancos de cenários em `tmp/cenarios/` foram preparados e validados sem contaminar a cópia atual: completo, falta_professor, deslocamento, disputa_sala e paralelo. Instruções de repetição e uso opcional no navegador/porta 8001 em `docs/testes/CENARIOS.md`. Nenhuma proposta desses cenários foi salva/aprovada. Próxima rodada: testes funcionais com o grupo, incluindo revisão visual dos formulários. Tudo apenas local.

## Atualização: paralelismo por salas

Migração 0011 e modelo Sala implementados na cópia local, com backup `backups/db.automacao.antes-salas-20261110_234836.sqlite3`. Menu Unidade → Salas e ficha da unidade dão acesso ao cadastro. Duas turmas podem ser simultâneas em salas/professores distintos; turma/professor/sala não sobrepõem. Legado sem sala reserva a unidade inteira. 732 aulas anteriores intactas; nenhuma sala foi atribuída automaticamente ao histórico.

Unidade usa visualização diária lado a lado com opção Semana; Professor/Turma continuam semanais e Curso separa ofertas por turma/unidade. Sala presente no editor, prévia, assinatura, replicação, API/Admin, mobile e PDF. Cinco salas fictícias e uma nova turma Preparatório B em Escola Centro foram preparadas para demonstração. Testar `/?data=2027-03-01&por=unidade` e clicar Gerar grade: 120 matérias (58 com docente, 62 sem docente), com 24 por turma. Nada gravado/aprovado automaticamente. 232 testes passaram; PDF diário de duas turmas renderizado e inspecionado. Detalhes e limites em AUTOMACAO.md.

## Atualização: disponibilidade e cópia de semanas

Professores agora disponíveis em todas as datas por padrão; restrições explícitas continuam válidas. Nova opção na grade para replicar uma semana salva para até 26 semanas, com prévia na mesma página, conferência do período e confirmação transacional. Duplicatas exatas são preservadas; conflitos bloqueiam e aulas sem professor exigem aceite parcial. Não copia aprovação. Para março/2027, última semana de 29/03 inclui 04/04. 220 testes passaram. Nenhuma cópia mensal foi aplicada ao banco de trabalho; gerar/salvar uma semana modelo atual antes de replicar. Consultar seção mais recente de AUTOMACAO.md para detalhes.

## Organização concluída em 10/11/2026

Testes agora em `grade/tests/`, com cenário compartilhado em `factories.py`. Executar `docker compose exec web python manage.py test grade.tests --noinput`. Documentação indexada em `docs/README.md`; mapa da arquitetura em `docs/arquitetura/ESTRUTURA.md`. Scripts antigos em `scripts/legacy/`, fixture em `grade/fixtures/`, todos os snapshots em `backups/`. Banco original, cópia ativa e `.env` continuam na raiz. As referências anteriores a nomes de backup devem ser procuradas em `backups/`. Nenhuma população ou migração foi executada nesta reorganização. Próxima sessão: testes funcionais com o usuário/colegas.

## Atualização de 10/11/2026

Implementados Home/dashboard, entrada autenticada em `/inicio/`, recuperação de CSRF expirado e menu compartilhado com Turma/Curso. Etapa atual: escopo por matriz de curso e aula curricular persistente sem professor (migração 0010). Ver seção mais recente de AUTOMACAO.md para detalhes e limites.

Teste preparado em `/?data=2027-02-01`: clicar Gerar grade para criar a prévia na sessão do usuário. São quatro ofertas de 24 aulas: Centro manhã/contraturno segunda, Norte tarde/contraturno quinta, Horizonte/Jardim calendários anteriores. Disponibilidades fictícias copiadas apenas nessa semana, com autorização do usuário. Prévia verificada distribui 96 matérias, 48 com docente e 48 sem docente por permissão/habilitação dos cadastros atuais. Nada foi aprovado ou salvo automaticamente. Turmas/demandas antigas permanecem históricas e as 732 aulas salvas estão intactas. Cópia migrada com backup `db.automacao.antes-planejamento-curso-20261110_213024.sqlite3`; original preservado. 206 testes passaram; HTML real conferido nos quatro modos.

Trabalho pausado a pedido do usuário para continuar amanhã.

## Ambiente e preservação

- Diretório autorizado: `C:\Users\Kelvin\Downloads\grade horaria\Grade-de-Aulas-Dinamica`.
- Branch de trabalho: `feat/automacao-semanal`. Preservar todas as alterações locais, inclusive anteriores a esta sessão.
- Sem push, PR, deploy ou publicação. Não usar cópia em Documents.
- Banco de trabalho: `db.automacao.sqlite3`; preservar `db.sqlite3` original. Conferir configuração efetiva antes de qualquer migração e fazer backup da cópia.
- Ler `AUTOMACAO.md` e eventuais `AGENTS.md` antes de editar.

## Estado atual

- Grade semanal unificada com edição manual, geração/prévia/confirmação na mesma página, quatro visualizações (unidade, turma, curso, professor) e PDF.
- Cursos/matrizes/demandas reais; calendário de turma com turno principal e contraturno configurável. Jornada de quatro aulas de 50 minutos por turno preservada.
- Automação organiza matérias e escolhe professores; horários fixos são opcionais.
- Distâncias consultadas pelos endereços na administração da unidade; não mostrar controles de distância na Home.
- Vínculo familiar/conjugal é entre professores; priorizar mesma unidade ou próximas. Pode alocar longe, com aviso.
- Aprovação explícita por semana disponível no botão verde no topo, inclusive para aulas já salvas. Revisão considera todas as unidades e registra versão/usuário/data. Alterações invalidam o estado vigente, mantendo histórico. Nenhuma aprovação foi feita automaticamente.
- Migração 0009 aplicada somente à cópia após backup `db.automacao.antes-aprovacao-20261109_222725.sqlite3`; 732 aulas preservadas.
- Último pedido concluído: retirar cards informativos da Home e compactar verticalmente a grade (fontes/espaçamentos/cards), mantendo larguras e ações.

## Validação e próximos passos

- 182 testes passaram após implementação da aprovação; 27 testes de integração/aprovação passaram após compactação da Home.
- Dry-run de migrações sem alterações após 0009. HTML de revisão verificado pelo Django; última alteração visual não foi inspecionada em navegador.
- Servidor Docker local reiniciado após alterações, porta 8000. Atualizar navegador com Ctrl+F5 se necessário.
- Sem tarefa pendente definida: aguardar novas observações do usuário sobre a interface compacta.
- Alterações permanecem nos arquivos de trabalho, sem criar commit nesta pausa.

## Combinado para a próxima sessão

Planejar e criar cenários controlados de população na cópia de testes, preservando os dados atuais. O usuário considera a aparência da distribuição atual estranha, mas ainda não há evidência de erro no motor. Comparar resultados esperados com resultados gerados nos seguintes cenários: professores suficientes e disponíveis; falta de docentes/habilitação/disponibilidade; conflitos de horários e deslocamentos; vínculos familiares com avisos; preservação de aulas manuais existentes.

Esclarecimento já dado: “Sem aula” indica ausência de registro naquele horário, não necessariamente falta de professor. “Sem professor” identifica matéria previamente definida sem docente. Carga não atendida deve ser explicada nas pendências da prévia. Nenhuma nova população foi executada após esse combinado.
