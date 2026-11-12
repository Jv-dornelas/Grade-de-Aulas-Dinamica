# Automação semanal — versão para testes

## Diagnósticos e refatoração incremental — 11/11/2026

Validação final: 269 testes passaram, incluindo ações de diagnóstico, candidato alternativo sem bloqueio e isolamento do portal público. Dry-run de migrações sem mudanças. Não alterados cadastros, aulas ou aprovações nesta etapa.

`diagnosticos.py` centraliza causas e ações verificáveis: habilitação ausente, unidade não permitida, vínculo legado incompatível, indisponibilidade explícita, limite diário e conflitos de professor/trajeto. Os cards sem docente são diagnosticados com a distribuição resultante, incluindo aulas fixas. Trata-se de bloqueios locais nessa distribuição, não de prova de causa única ou de inviabilidade global. Um candidato localmente livre mantém mensagem explícita de incerteza. Mensagens antigas já persistidas não são reescritas automaticamente; nova geração usa os novos diagnósticos. Não altera restrições nem atribui disponibilidade fictícia.

Orquestração da página movida de `views.py` para `pagina_grade.py`, com reexportação para preservar rotas e imports; CSS principal extraído do template para `grade_principal.css`, incluído no versionamento dos assets. Diagnóstico separado da sessão/apresentação. A refatoração é incremental: ainda há estilos legados e dependências a separar, sem reestruturação ampla nesta etapa.

Incluídos também os ajustes locais anteriores do mobile, APK 1.3 e configuração de túnel isolado. Binários, bancos e credenciais continuam fora do Git. Portal público testado por HTTPS, sem acesso a Admin/API/gestão; interação em aparelho depende da validação do usuário. Não recriar túnel só para aplicar ajustes da gestão local.

## Avisos por e-mail — 11/11/2026

Validação: 262 testes passaram, migrações dry-run sem alterações, backend local de arquivos confirmado e hash do banco original inalterado. Não realizado teste de entrega SMTP real.

Novas aprovações preparam avisos individuais para professores cuja semana mudou; rascunhos/prévias/salvar sem aprovar não disparam. Inclui retirada de aulas, comparação com versão anterior e registro único aprovação/professor. Caixa de saída transacional na migração 0013; envio somente após commit, falha não desfaz aprovação, status na revisão e comando `enviar_avisos_grade` para novas tentativas. Versões desatualizadas não são reenviadas. Modo padrão de arquivos em `tmp/emails/` é simulação, sem entrega real. Configuração SMTP, cuidados e limitações em `docs/guias/EMAIL_GRADE.md`. Backup `backups/db.automacao.antes-email-20261111_195102.sqlite3` antes de migrar somente a cópia. Não foram aprovadas grades nem enviados e-mails reais para teste.

## Auditoria de entradas dos critérios — 11/11/2026

Conferidos campos de professor, unidade/trajetos, curso/matriz, turma/calendário, salas e grade. Distâncias, vínculo familiar, habilitação, unidades permitidas e limite diário já tinham entrada; estavam faltando na interface principal as exceções de disponibilidade por horário e a configuração administrativa do limite de proximidade familiar. Foram integradas em `/professores/restricoes/` e `/configuracoes/`, com links no menu Professor e na grade. Cadastro de exceção valida o período afetado e faz rollback se invalidar aula salva. Remover uma liberação também valida a regra de turno que passa a valer.

Migração `0012` adiciona ConfiguracaoAutomacao, com uma única configuração geral e limite de proximidade 0–240 minutos. Sem cadastro explícito, utiliza o valor anterior do ambiente; nenhum parâmetro foi alterado automaticamente. Formulário, motor, gerador e assinatura leem esse valor; o campo oculto enviado pelo navegador não o substitui. A jornada global continua fixa em quatro aulas de 50 minutos por turno e é mostrada sem edição.

A ficha de professor foi unificada em `professores.py`/ProfessorForm, com todos os campos editáveis, incluindo vínculo de conta mobile existente. Há validação de tipo, M2M, auto-parentesco, conta já vinculada e escolhas de contas não privilegiadas. Edição detecta concorrência e valida as semanas salvas; mudanças incompatíveis com habilitação/unidade/limite fazem rollback. Sucesso usa redirect para a ficha editável, evitando repetir criação ao atualizar a página. Os templates de cadastro/edição usam a base e o formulário compartilhados. Contas novas e permissões continuam na administração técnica; o vínculo mobile não participa do gerador.

Documentado em `docs/guias/CADASTROS_AUTOMACAO.md` o caminho de cada entrada e seu uso efetivo: o motor usa minutos dirigidos de deslocamento; km, meio de transporte, contato e observações não são regras inferidas automaticamente. Demanda curricular, cache/assinaturas e auditoria são calculados/internos. Não foi reintroduzido cadastro individual de carga nem controle que relaxe conflitos obrigatórios.

Backup anterior: `backups/db.automacao.antes-cadastros-criterios-20261111_192857.sqlite3`. Confirmado o banco efetivo antes de migrar somente `db.automacao.sqlite3`. Todas as tabelas anteriores de cadastros/aulas foram comparadas integralmente com o backup e permanecem iguais; configuração geral sem registro automático; integridade SQLite OK e hash do original inalterado. Validação: 256 testes passaram, incluindo campos renderizados, POST de vínculos, consumo do parâmetro pelo motor, concorrência, rollback, permissões/CSRF e novas telas. Dry-run sem migrações pendentes. Não houve inspeção visual em navegador nesta etapa.

## Clareza do MVP, cadastros e cenários reproduzíveis — 11/11/2026

Novo `indicadores.py` calcula separadamente aulas distribuídas da matriz, atendimento com professor, aulas sem docente, carga sem horário e registros fora da matriz ativa. Na grade, os indicadores informam que consideram a semana inteira/todas as unidades e se incluem prévia. Pendências aceitas aparecem somente quando a aprovação da versão salva continua vigente; não reduzem as pendências reais. Ao alterar dados e invalidar aprovação, o aceite anterior deixa de ser apresentado como vigente. Dashboard e revisão de aprovação distinguem planejamento de atendimento, sem confundir grade ocupada com carga atendida.

O estado da grade agora apresenta uma próxima ação: gerar/replicar, revisar prévia, salvar, aprovar novamente ou resolver pendências aceitas. Prévia expirada é sinalizada e não pode ser salva; prévia de outro período orienta voltar a ela. Há ações separadas **Salvar sem aprovar** e **Aprovar e gravar**, usando a mesma validação transacional já existente. Não foram relaxadas regras do motor ou de aprovação parcial.

`formularios.css` padroniza campos, labels, botões, espaçamentos, erros, sucessos, foco por teclado e confirmações de exclusão em 22 templates-base/legados, cobrindo também cursos, turmas e salas via herança. As confirmações existentes foram mantidas, sem diálogos adicionais ou mudanças no efeito das exclusões. Reduzidos textos redundantes da prévia. Não houve inspeção visual em navegador de todas as telas nesta etapa; HTML e preservação dos formulários foram verificados pelos testes.

`preparar_cenario` cria/valida cenários exclusivamente em `tmp/cenarios/db.cenario.<nome>.sqlite3`, via SQLITE_NAME explícito. Não usa a cópia principal e recusa banco original, destinos externos, links e bases com outros cadastros. Migra somente esses arquivos isolados, prepara dados fictícios, valida a proposta e registra relatório JSON; não salva/aprova aulas. Reexecutar valida o cenário existente sem duplicar ou limpar dados. Cinco cenários já executados com esperado/obtido conferidos: completo (24 com docente); falta_professor (12 com docente + 12 sem); deslocamento (1 com docente + 1 sem numa carga reduzida para isolar a regra); disputa_sala (24 distribuídas + 24 sem horário); paralelo (48 com docente em duas salas). Roteiro em `docs/testes/CENARIOS.md`, incluindo ambiente opcional na porta 8001, separado do sistema atual.

Validação: 246 testes aprovados, dry-run sem migrações no banco principal, formulário/indicadores renderizados com dados locais, 5 relatórios de cenários válidos e repetição idempotente conferida. A cópia de trabalho permanece com 732 aulas; nenhum cenário foi inserido nela. Hash do banco original inalterado e integridade SQLite OK. Nenhum push, PR, deploy ou publicação.

## Salas, paralelismo e unidade por dia — 10/11/2026

Implementada a decisão aprovada: salas individuais por unidade e aulas simultâneas de turmas diferentes, sem sobreposição de professor, turma ou sala. Aulas sem professor também reservam sala/turma. Modelo `Sala` (unidade, nome, ativa) e FK opcional em AlocacaoGrade, migração `0011`. Sala não pode mudar de unidade quando já vinculada a aulas. Inativação impede novas alocações e mantém as existentes; exclusão de sala vinculada é protegida.

Sem sala cadastrada, uma unidade mantém a capacidade conservadora anterior de uma aula por intervalo. Se todas as salas cadastradas estiverem inativas, não são criadas vagas implícitas. Alocação sem sala, inclusive histórica, reserva toda a unidade enquanto não for revisada; cadastrar duas salas não redistribui aulas antigas automaticamente. Salas foram incluídas nas assinaturas de prévia, validação compartilhada, gerador de docentes, preenchimento curricular, editor, API/Admin, replicação, mobile e PDFs. Mudanças de sala invalidam prévias/assinaturas antigas. O gerador escolhe salas ativas junto com horário/docente, com limite de 4.000 candidatos e os demais limites de cálculo existentes.

Cadastro em `/salas/`, pelo menu Unidade → Salas e pela ficha da unidade. Permissões administrativas e CSRF mantidos. O editor identifica que deixar sala vazia reserva toda a unidade. A tabela manual legada recusa operações em dias com paralelismo para não substituir silenciosamente registros; o editor integrado por aula é o fluxo suportado.

No modo Unidade, o padrão é **Dia**, com as turmas lado a lado, data/navegação diária, alternância para Semana, indicação de fora do calendário e salas nos cards. Contagens, geração e aprovação continuam semanais, informado no quadro. Professor e Turma permanecem semanais. Curso agora separa quadros por turma/unidade em vez de misturar ofertas na mesma célula. As projeções usam as mesmas alocações e preservam a sessão de prévia. PDF acompanha Dia/Semana/filtro, pagina até quatro turmas por quadro diário e identifica salas/pendências. Mobile mantém consulta individual semanal e mostra a sala.

Backup anterior: `backups/db.automacao.antes-salas-20261110_234836.sqlite3`. Migração aplicada apenas após confirmar `db.automacao.sqlite3`. Comparadas as 732 aulas anteriores em todos os campos preexistentes: idênticas ao backup, todas ainda com sala nula. Original `db.sqlite3` com hash inalterado, integridade da cópia OK.

Para demonstração fictícia autorizada, cadastradas cinco salas: duas em Escola Centro e uma em Escola Norte/Horizonte/Jardim. Criada Preparatório B em Escola Centro, compartilhando curso e calendário da oferta atual dessa unidade. Não foram alteradas habilitações, permissões, disponibilidades ou aulas existentes. Na semana vazia de 01/03/2027, prévia real conferida: 120 matérias distribuídas (24 em cada uma de cinco turmas), 58 com professor e 62 sem professor, zero carga sem horário. Não foi gravada/aprovada automaticamente.

Validação: 232 testes aprovados, incluindo paralelismo, conflitos de sala/professor/turma, ocupação por aula sem docente, sala errada/inativa, histórico sem sala, geração de 48 aulas em duas turmas, replicação, API/permissões, quatro modos e PDF. Dry-run sem novas migrações. HTML conferido com dados locais e PDF diário renderizado/inspecionado visualmente em uma página para duas turmas. Não houve conferência visual em navegador. Dependência temporária de renderização foi retirada do workspace após a inspeção.

## Disponibilidade padrão e replicação de semanas — 10/11/2026

O usuário definiu professores disponíveis em qualquer data por padrão, sem exigir atualização semanal de disponibilidade. `MotorRestricoes.disponivel` utiliza manhã/tarde disponíveis na ausência de cadastro. Restrições explícitas por data ou horário continuam sendo aplicadas, assim como limite diário, habilitação, unidades permitidas, conflitos e deslocamentos. A tela diária de disponibilidades reflete o mesmo padrão; apagar uma restrição retorna ao padrão disponível. A política entrou na assinatura para invalidar prévias antigas. Não foi criada população de disponibilidades nem descartado nenhum bloqueio existente. Feriados não retiram aulas do calendário.

Auditoria dos cadastros atuais: 12 professores têm ao menos uma unidade permitida/oficial. Existem 4 trajetos dirigidos, suficientes para os pares de unidades em que os professores atuais podem circular; nenhum desses pares está sem trajeto utilizável. Não significa que todas as unidades tenham professores habilitados para todas as matérias, nem que todos os pares possíveis entre as seis unidades tenham rota cadastrada.

Na própria grade há **Replicar uma grade semanal por um período**. Origem padrão é a semana anterior à exibida; pode escolher outra semana salva, primeira semana de destino e última semana a incluir. As datas são normalizadas para semanas completas, de segunda a domingo, mantendo domingo na primeira coluna visual. Por exemplo, incluir a semana de 29/03/2027 alcança 04/04/2027; isso é informado antes da confirmação. Limites: 26 semanas e 4.000 aulas propostas por lote. O filtro visual não restringe a cópia: ela considera toda a semana, explicitamente informado na interface.

`replicacao.py` prepara uma prévia privada em sessão, sem gravar aulas. A proposta é visível no mesmo quadro nos quatro modos; links permitem percorrer todas as semanas do lote e exportar o PDF da semana visível como prévia não confirmada. Não permite manter uma geração normal e uma replicação concorrentes na mesma sessão; também bloqueia edição durante a prévia de cópia. Após confirmar, cada semana pode ser editada normalmente.

A confirmação exige revisão explícita do período, token e validade de 30 minutos. Detecta alterações na origem, em qualquer semana de destino e nos cadastros. Valida o período inteiro transacionalmente e preserva registros existentes; aulas idênticas são reconhecidas sem duplicar, mas conflitos impedem todo o lote. Matérias sem professor são copiadas como pendência e exigem aceite parcial. A aprovação da origem não é copiada; aprovação existente no destino só continua vigente se os dados permanecerem idênticos. Semana modelo vazia ou com demandas históricas inativas é recusada, orientando escolher uma oferta atual já salva.

Validação: 220 testes passaram, incluindo replicação de cinco semanas de março, fronteira de abril, ausência de disponibilidade datada, bloqueios explícitos, idempotência, concorrência, revisão/CSRF/permissões, preservação de origem, quatro modos e PDF. Dry-run sem migrações. Formulário HTML renderizado com os dados locais; nenhuma replicação foi aplicada à cópia de trabalho: permanecem 732 aulas, sem alocações em março. Banco original preservado. Não houve inspeção visual em navegador nesta etapa.

## Organização da primeira versão — 10/11/2026

Os testes foram reunidos em `grade/tests/` (18 módulos); o antigo `grade/tests.py` virou `test_mobile.py`. Imports relativos foram ajustados e o cenário comum foi extraído para `tests/factories.py`, eliminando dependência de testes em métodos de outra classe de testes. Comando atual: `python manage.py test grade.tests`; para um módulo, `python manage.py test grade.tests.test_gerador`. Os caminhos `grade.test_*` registrados em etapas anteriores são históricos.

Validação da organização: 210 testes aprovados tanto pelo pacote `grade.tests` quanto pela descoberta padrão `grade`; `manage.py check` sem problemas; migrações dry-run sem alterações; links dos índices locais conferidos. Hashes dos bancos original/ativo permaneceram idênticos aos do início desta etapa. Não houve commit, push, PR ou publicação.

Documentação técnica foi organizada em `docs/guias/`, `docs/arquitetura/` e `docs/processos/`, com índice em `docs/README.md`. `AUTOMACAO.md` permanece na raiz, no caminho solicitado. README atualizado com os acessos e comandos atuais; scripts históricos foram preservados em `scripts/legacy/`, e a fixture foi movida para `grade/fixtures/dados_ficticios.json`, sem executar população. `backups/` agora reúne os 12 snapshots existentes: todos tiveram hash conferido antes/depois, sem mudanças. Bancos ativo e original continuam na raiz, byte a byte iguais durante a organização; `.env` intacto.

Artefatos `output/`, `tmp/`, `dist/` e backups foram excluídos do Git/contexto Docker. `.editorconfig` define convenções para novas edições e há configuração apenas local do VS Code para ocultar caches e retirar artefatos das buscas. Nenhum motor, regra de negócio, modelo, migração, rota ou template foi reorganizado nesta etapa. O mapa de responsabilidades e a dívida técnica restante estão em `docs/arquitetura/ESTRUTURA.md`; extração de views e CSS inline fica para outra etapa após os testes funcionais da primeira versão.

## Cabeçalhos dos cadastros e disciplinas duplicadas — 10/11/2026

As 21 telas legadas de professor, unidade e disciplina (cadastro, lista, seleção, edição, confirmação e sucesso de exclusão) passaram a incluir o mesmo `navegacao_principal.html` usado pela Home/grade. CSS compartilhado é carregado depois dos estilos antigos, com ajustes para não herdar estilos de botões/formulários do conteúdo. Home, grade, turma, curso e Sair ficam disponíveis nesses cabeçalhos. Setas dos cards de disciplinas agora abrem a edição real; foram eliminados destinos `#` dessa lista.

Com backup `db.automacao.antes-disciplinas-20261110_215600.sqlite3`, foram consolidadas duplicidades exatas de nome/área na cópia local: Matemática 4/7 → 9, História 5 → 15 e Biologia 6 → 12. O cadastro usado na matriz foi priorizado. Professores receberam a habilitação correspondente e referências de matriz, demanda e aula foram redirecionadas transacionalmente antes de retirar as duplicatas; nenhuma aula, carga, data, horário, professor ou turma foi excluído/alterado. Os IDs de disciplina dessas referências foram a única alteração nas 732 alocações, conferida campo a campo. Caso haja cargas duplicadas na mesma turma/curso, a função recusa consolidar automaticamente. Português e Português e interpretação continuam distintos. Catálogo atual: 11 disciplinas.

Novas duplicatas por nome sem espaços externos/casefold e mesma área são recusadas no modelo e na validação da API/Admin; importações em bulk continuam exigindo conferência explícita. Mudança de catálogo invalida prévias e assinaturas de aprovação anteriores; gerar/revisar novamente. Habilitações agora coerentes podem melhorar cobertura das ofertas de teste, sem inventar disponibilidade. Validação: 210 testes passaram, incluindo 18 rotas de navegação, links reais, consolidação idempotente e preservação de vínculos; dry-run sem migrações pendentes. Banco original com hash inalterado e integridade da cópia OK. Não houve inspeção visual em navegador nesta etapa.

## Curso como escopo e aulas sem professor — 10/11/2026

O usuário confirmou disciplinas/cargas semanais definidas no curso, sem dia fixo, com ordem variável. Novos cadastros de turma exigem curso e turno. Para a matriz de 24 aulas, a interface e o gerador exigem cinco dias úteis e dia de contraturno configurado: 20 + 4 aulas de 50 minutos. DemandaAula continua como projeção interna sincronizada da matriz e como histórico legado, sem CRUD independente no Admin. O editor principal exige disciplina curricular para novas aulas; edição/consulta de registros legados permanece compatível. Divergência entre projeção e matriz bloqueia geração e orienta sincronizar o curso.

O gerador conserva as alocações gravadas, maximiza a cobertura docente com as regras existentes e completa a distribuição curricular restante em horários livres com professor nulo. Não atribui professor fictício, não inventa salas, não libera paralelo por turma e mantém almoço/jornada. Calendário sem capacidade deixa carga explicitamente não distribuída. O planejamento curricular adicional usa CP-SAT com limites de tempo e opções; não promete distribuição global ótima se o cálculo encerrar antes. Aulas já salvas sem professor ficam reservadas e são resolvidas pelo editor; gerar novamente não as sobrescreve.

Migração `0010` permite professor nulo em AlocacaoGrade e registra motivo da pendência. Aulas sem professor exigem vínculo curricular de curso e respeitam conflitos de turma/unidade e limites semanais; não consomem disponibilidade/limite de um docente inexistente. Cards laranja persistem nas quatro visualizações, inclusive grupo “Sem professor”, e o editor oferece essa opção. A falta de horário e a falta de atribuição docente são contadas separadamente. Aprovação parcial exige aceite explícito tanto na prévia quanto na semana gravada; preencher matéria sem docente não aumenta cobertura no dashboard. PDF identifica SEM PROFESSOR. Diagnóstico distingue falta de habilitação, ausência de permissão e indisponibilidade conhecida, usando orientação genérica quando a causa global não foi comprovada.

Para adotar um curso numa turma antiga, há ação explícita **Adotar curso preservando histórico**: cria nova oferta na mesma unidade e desativa as demandas manuais antigas, sem alterar nenhuma aula ou vínculo anterior. Não muda o curso retroativamente em turmas com aulas salvas.

Após o usuário autorizar manipular os dados fictícios, foram adotadas ofertas do curso Preparatório 1 em Escola Centro (manhã, contraturno segunda) e Escola Norte (tarde, contraturno quinta). Horizonte/Jardim mantêm os calendários anteriormente cadastrados. Agora são quatro ofertas curriculares de 24 aulas (96 semanais), além das duas turmas históricas preservadas. Para o teste de 01–07/02/2027, 50 disponibilidades dos professores fictícios 5–14 foram copiadas de 09–13/11/2026. Habilitações, unidades permitidas e deslocamentos não foram modificados. Prévia real verificada: 96 matérias distribuídas, 48 com professor e 48 sem professor nas novas ofertas, cujos docentes da matriz não estão permitidos nessas unidades. Nenhuma dessas propostas foi gravada/aprovada. Em semanas antigas, aulas fixas legadas ainda podem ocupar espaços necessários ao curso; use a semana vazia para avaliar o novo modelo.

Backup anterior: `db.automacao.antes-planejamento-curso-20261110_213024.sqlite3`. Migração aplicada somente após confirmar `db.automacao.sqlite3`. As 732 alocações anteriores foram comparadas campo a campo com o backup e permanecem idênticas; integridade SQLite OK e hash de `db.sqlite3` original inalterado. Validação: 206 testes aprovados e prévia HTML renderizada com 96 cards nos quatro modos; sem inspeção visual em navegador nesta etapa.

## Recuperação de formulário expirado — 10/11/2026

Reproduzido o CSRF inválido ao abrir login mobile e autenticar a gestão em outra aba antes de enviar o primeiro formulário: o Django rotaciona o token. A proteção permanece ativa; nenhum POST inválido é reaproveitado. A página de falha agora explica a expiração no visual do sistema e oferece link GET para uma entrada atualizada (mobile, gestão ou admin). Não revela motivo técnico, credenciais ou conteúdo do POST e não permite cache. Nove testes de autenticação/recuperação passaram, incluindo token antigo rejeitado e login com token novo aceito. Contas em abas do mesmo perfil compartilham sessão; usar janela anônima/outro perfil para testar professor e gestão simultaneamente.

## Home como entrada autenticada — 10/11/2026

`/inicio/` apresenta login visual do sistema quando não há sessão administrativa ativa e o painel quando há. Autenticação utiliza usuário e senha individuais existentes no Django, exigindo conta ativa com `is_staff`; não utiliza senha compartilhada. A grade, cadastros, automação e PDF direcionam usuários sem acesso para essa entrada, preservando o destino em `next`, com validação de URL pelo LoginView. Professores continuam com entrada própria mobile. Django Admin permanece separado para manutenção.

Botão Sair usa POST com CSRF. Erros de credencial/permissão são genéricos, senha nunca é devolvida ao HTML e o controle de exibição funciona sem dependências externas. Formulário mantém labels, autocomplete e navegação por teclado. Sem alteração de bancos/usuários ou migrações. Validação: 195 testes passaram, incluindo autenticação, conta inativa, conta sem permissão, CSRF, logout e recusa de redirecionamento externo. Conferência visual em navegador não executada nesta etapa.

## Página inicial e indicadores — 10/11/2026

Nova Home em `/inicio/`, no menu superior compartilhado. A grade permanece em `/` com aba “Grade horária”, preservando URLs, edição e sessões de prévia existentes. Painel apenas de leitura para usuários administrativos ativos: semana configurável, aulas gravadas, atendimento das demandas ativas, carga pendente, aprovação vigente, distribuição por dia e unidade, cadastros e período disponível no banco. Prévia não entra nas contagens e não é descartada ao navegar. Cobertura soma por demanda até o limite solicitado; aulas sem demanda continuam na contagem total, mas não aumentam cobertura. Pendências não atribuem automaticamente culpa à falta de professor. Disponibilidade exibida conta cadastros por turno, sem afirmar viabilidade da alocação.

Auditoria local: `db.automacao.sqlite3`, integridade SQLite OK, 6 unidades, 12 professores, 15 disciplinas, 1 curso, 4 turmas, 24 demandas, 662 disponibilidades por turno e 732 aulas entre 21/09/2026 e 29/01/2027. Carga ativa: 60 aulas semanais. Duas turmas legadas sem curso e duas vinculadas ao Preparatório 1; duas unidades sem aulas gravadas. Duas aprovações constam no histórico na consulta desta data; o painel verifica a assinatura antes de indicar aprovação vigente. Banco contém população de testes; não mede frequência ou aulas ministradas. Nenhuma migração ou população foi necessária para o painel.

## Home e grade compactas — 09/11/2026

Removidos os cards informativos acima da distribuição, mantendo gerar, aprovar, edição e PDF no topo/quadro. A grade recebeu fontes e espaçamentos verticais menores nos cards, células, cabeçalhos e áreas de controle; larguras e colunas permanecem iguais. Nenhuma alteração de banco ou regras de geração nesta etapa.

## Aprova??o expl?cita na pr?pria grade ? 09/11/2026

O bot?o verde **Aprovar grade** fica no topo tamb?m para semanas j? gravadas. Abre uma revis?o na mesma p?gina, considerando a semana inteira e todas as unidades, independentemente dos filtros. A confirma??o exige confer?ncia expl?cita; pend?ncias de carga exigem aceite adicional de aprova??o parcial. Conflitos obrigat?rios impedem aprova??o. Uma pr?via com novas aulas ? gravada e aprovada na mesma transa??o; uma gera??o sem novas propostas n?o bloqueia a aprova??o das aulas existentes.

A aprova??o registra usu?rio, data, semana e assinatura da vers?o, sem modificar aulas. Mudan?as posteriores na grade ou nos cadastros invalidam o estado vigente, preservando o hist?rico. O PDF informa o estado de aprova??o. Acesso e confirma??o exigem usu?rio administrativo ativo no servidor, CSRF e vers?o atual. Nenhuma semana foi aprovada automaticamente.

Migra??o aditiva `0009` aplicada somente a `db.automacao.sqlite3`, ap?s backup `db.automacao.antes-aprovacao-20261109_222725.sqlite3`. As tabelas anteriores foram comparadas integralmente com o backup e preservadas; 732 aulas mantidas e original `db.sqlite3` com hash inalterado. Valida??o: 182 testes aprovados, migra??es dry-run sem altera??es e revis?o HTML renderizada pelo Django. N?o houve verifica??o visual em navegador nesta etapa.

## Trajetos administrativos e vínculo familiar/conjugal — 09/11/2026

Conforme a orientação do usuário, foram retirados da Home o bloco de distâncias/endereços, os atalhos de consulta de trajetos e o controle numérico de proximidade. Os trajetos e mapas permanecem na ficha administrativa da unidade, sendo consumidos automaticamente pelo motor. A Home mantém geração, revisão/aprovação e edição da grade.

Parentesco é exclusivamente o **vínculo cadastrado entre dois professores**, incluindo casamento/cônjuges e outros familiares; proximidade geográfica não cria vínculo. Basta cadastrar em um dos lados. Quando ambos lecionam no mesmo dia, a automação prioriza mesma unidade ou unidades próximas. O usuário confirmou que, se não for possível, é permitido alocá-los longe **com aviso**, mantendo as demais regras obrigatórias. Essa é a política de preferência já aplicada pelo motor; não foi convertida em bloqueio. O aviso cita os professores e a situação, sem expor parâmetros técnicos de distância na Home, e aparece aberto na revisão da prévia.

O campo nos cadastros normal/admin de professor passou a se chamar **Vínculo familiar ou conjugal (opcional)**, com explicação de funcionamento nos dois sentidos. O limite interno de proximidade é administrativo (`GRADE_PROXIMIDADE_PARENTESCO_MINUTOS`, inicial 15), não um valor a ser escolhido pelo usuário ao gerar; o formulário do servidor utiliza a configuração e ignora tentativas de substituí-la por outro valor válido enviado pelo navegador. Mudanças nessa configuração invalidam prévias antigas. Validação: 94 testes relevantes aprovados e dry-run de migrações sem mudanças. Nenhuma aula ou cadastro foi alterado nesta etapa.

## Visibilidade das alterações na Home — 09/11/2026

A Home agora destaca três blocos antes do quadro: **Automação da semana** (modo efetivo e contagem de turmas flexíveis/fixas), **Distâncias pelos endereços** (unidades com endereço e atalhos para consultar trajetos/completar cadastro) e **Revisão da distribuição** (prévia pendente ou aulas já gravadas). A geração e a edição continuam no mesmo quadro. O estado deixa explícito que gerar preserva aulas já gravadas e que não há aprovação de nova proposta enquanto nenhuma estiver pendente. CSS/JS recebem versão baseada na alteração dos arquivos para evitar reutilização de recursos antigos após recarregar. Os 15 testes da integração da página principal passaram; nenhuma mudança de banco foi necessária nesta etapa.

## Endereços de referência para as unidades fictícias — 09/11/2026

A pedido do usuário, os nomes Polo Centro e Polo Zona Sul foram mantidos sem marcadores e receberam endereços públicos de referência, apenas para testes. **Não são escolas reais nesses locais**:

- Polo Centro: Rua da Consolação, 94, República, São Paulo/SP, 01302-000 (referência: [Biblioteca Mário de Andrade](https://prefeitura.sp.gov.br/web/cultura/w/bma/menu/servico/9709)).
- Polo Zona Sul: Rua Vergueiro, 1000, Liberdade, São Paulo/SP, 01504-000 (referência: [Centro Cultural São Paulo](https://centrocultural.sp.gov.br/visite/)).

Consulta real concluída com Nominatim e OSRM/FOSSGIS: **ida 3,75 km / 7 minutos; volta 3,82 km / 7 minutos**, estimativas de carro sem trânsito em tempo real. Os resultados foram armazenados no cache; não substituíram os trajetos anteriores. Para aplicá-los à matriz, use a ficha da unidade, **Consultar pelo endereço → conferir os pontos → Aplicar trajetos à automação**. As 732 aulas foram preservadas.

O geocodificador pode retornar vários objetos do mesmo prédio (equipamento, edifício, monumento). A validação agora agrupa somente candidatos com município, rua, número e CEP idênticos, compatíveis com o número/CEP informado, e coordenadas próximas. Correspondências em ruas/municípios distintos continuam recusadas. Os 11 testes da consulta passaram. Backup anterior: `db.automacao.antes-enderecos-exemplo-20261109_220405.sqlite3`; somente a cópia local recebeu os endereços.

## Teste externo autorizado — 09/11/2026

Após autorização específica do usuário para Nominatim/OpenStreetMap e OSRM/FOSSGIS, foram feitas consultas reais de geocodificação para as duas unidades com endereço. O Polo Centro está cadastrado como “Rua Principal, 100, São Paulo”, sem CEP: o serviço retornou ruas distintas em Parque Novo Mundo e Perus, portanto a localização permaneceu ambígua. O Polo Zona Sul está cadastrado como “Av. Sul, 500, São Paulo”, sem CEP: o resultado apontou para Mairinque, não para o município informado. Nenhuma distância/rota foi aplicada e a matriz anterior permaneceu idêntica. Não houve chamada de roteamento, pois os pontos de origem/destino não ficaram confiáveis.

Foi acrescentada uma validação explícita do município retornado pelo geocodificador; um resultado em outra cidade é recusado antes do cálculo de rota. Os 10 testes de consulta passaram, incluindo o novo caso. A obtenção das distâncias reais depende de completar/corrigir os endereços de ambas as unidades com logradouro, número, bairro, cidade/UF e CEP. A autorização anterior já foi recebida; o bloqueio restante é a qualidade/localização dos endereços, não a permissão de consulta.

## Respostas corrigidas: geração flexível e consulta por endereço — 09/11/2026

O usuário corrigiu as respostas anteriores: a automação deve **organizar os horários das matérias e escolher os professores**, e os trajetos podem ser consultados **pelos endereços**. O modo flexível voltou a ser o padrão e foi reativado nas quatro turmas locais. A opção “Manter matérias em horários fixos” continua disponível, desmarcada; os 60 horários curriculares anteriores foram preservados como configuração opcional. Não foram alteradas as 732 aulas já gravadas.

Em **Unidade → Atualizar**, salve endereço, cidade/UF e CEP e use **Consultar pelo endereço**, escolhendo outra unidade. A integração consulta Nominatim/OpenStreetMap para localizar os endereços e OSRM/FOSSGIS para distância rodoviária e duração de ida e volta. A tela identifica os pontos retornados, links para conferência no mapa, km e minutos. **Aplicar trajetos à automação** usa somente a proposta privada da sessão, exige conferência dos pontos e recusa token inválido, alteração posterior dos endereços/matriz ou consulta expirada. Os resultados são estimativas de carro, sem trânsito em tempo real; não equivalem automaticamente a ônibus/caminhada. Cadastros manuais anteriores permanecem válidos e não são substituídos por falha de consulta.

Uma rota automática aplicada guarda fonte, data e assinatura dos endereços; se o endereço mudar, ela deixa de ser utilizada pelo motor até nova consulta. Há cache persistente de 30 dias e requisições serializadas com intervalo mínimo de 1,1 s no processo local. Não há geocodificação em lote, tarefas periódicas ou consulta externa ao gerar cada grade. Os provedores são configuráveis por ambiente; o acesso externo é habilitado por padrão só em `db.automacao.sqlite3`. Uso em múltiplos processos/produção exigirá um limitador compartilhado e revisão de capacidade/termos. Referências oficiais: [Nominatim](https://operations.osmfoundation.org/policies/nominatim/), [OSRM/FOSSGIS](https://routing.openstreetmap.de/about.html) e [API OSRM](https://project-osrm.org/docs/v5.24.0/api/).

Migração aditiva `0008` aplicada apenas à cópia local após backup `db.automacao.antes-mapas-20261109_215144.sqlite3`. Só duas das seis unidades têm endereço e cidade preenchidos; Escola Centro, Escola Norte, Horizonte e Jardim precisam completar seus endereços antes de consultar. Não foram criados endereços fictícios. A tentativa de consulta real pela ferramenta foi bloqueada pela revisão automática de permissões por exigir autorização específica do envio de endereço/cidade/CEP ao Nominatim e das coordenadas ao OSRM/FOSSGIS. Essa consulta não foi executada. Os testes de integração usam respostas simuladas, sem enviar dados externos; o teste real fica pendente dessa autorização.

## Automação somente de professores e trajetos na unidade — 09/11/2026

Com a definição confirmada pelo usuário, **novas turmas usam matérias com dias/horários fixos** (`materias_fixas=True`). Em **Cadastros → Turmas e calendário → Horários das matérias**, a coordenação distribui as demandas da matriz pelos horários da turma. A automação consulta essa distribuição e escolhe somente professores habilitados, disponíveis e permitidos; não troca matérias de horário para contornar uma indisponibilidade. Se a carga curricular não estiver inteiramente distribuída, solicita completar o cadastro. `materias_fixas=False` fica como compatibilidade explícita com o motor/cadastros legados; não é oferecido pelo formulário normal de turmas. A matriz de curso pode ser compartilhada, enquanto a oferta, o calendário e a distribuição fixa pertencem a cada turma/unidade.

Na grade, uma matéria com dia/horário definido e sem alocação aparece como **Sem professor**, nos quatro modos e no PDF. **Sem aula** significa ausência de horário curricular/aula naquela célula. Definir professor manualmente usa as mesmas validações da automação. Nos registros vinculados a turmas com matérias fixas, o editor de aula permite mudar somente o professor; mudanças de distribuição são feitas no cadastro das matérias. As aulas históricas já gravadas continuam fixas e não são reescritas para coincidir com a nova distribuição. Prévias detectam alterações de horários curriculares ou trajetos e exigem nova geração.

Em **Unidade → Atualizar**, a ficha agora contém cursos/turmas da unidade e a tabela de trajetos: outra unidade, minutos de ida/volta e km opcionais. Esses valores atualizam a matriz consultada automaticamente pelo motor. Ida e volta podem diferir. Campos de tempo vazios não apagam trajetos. Km sem minutos não resulta em uma velocidade/tempo presumido; o formulário pede o tempo. Trajeto ausente continua bloqueando deslocamentos. Nenhum mapa/serviço externo foi contratado ou utilizado. A preferência de proximidade entre parentes permanece separada dos trajetos obrigatórios.

Aplicada somente à cópia `db.automacao.sqlite3` a migração aditiva `0007`, após backup consistente em `db.automacao.antes-materias-fixas-20261109_213946.sqlite3`. A semana existente de **09/11/2026** foi aproveitada como distribuição fixa inicial das quatro turmas: 6 + 6 + 24 + 24 = **60 horários**. Os 1.526 registros/campos anteriores foram comparados com o backup e preservados; continuam **732 aulas**, incluindo o período preenchido até janeiro. SHA-256 do banco original inalterado e integridade SQLite aprovada. Não foram inventados novos horários de matérias nem disponibilidades para pessoas reais.

O comando `adotar_semana_curricular --semana 2026-11-09 --turmas 1 2 3 4` reutiliza a distribuição já cadastrada, sem copiar professores e sem substituir uma distribuição fixa já existente. Validação funcional com 01/02/2027: grade e PDF retornaram 200 com 60 matérias sem professor; o gerador retornou zero propostas e 60 pendências porque não há disponibilidade cadastrada nessa semana, sem mover matérias ou presumir disponibilidade.

## Clareza da confirmação e das células vazias — 09/11/2026

A ação **Aprovar e gravar prévia** agora aparece em verde no topo da Grade Horária e na revisão da proposta. A tela explica quando não existe prévia aguardando aprovação; nas semanas preenchidas pelo comando, as aulas já estavam gravadas, motivo pelo qual o botão anterior não aparecia. Isso representa confirmação da proposta, não um fluxo persistente separado de homologação de aulas já salvas. Os espaços vazios exibem **Sem aula**, sem afirmar falta de professor. A preferência de proximidade por parentesco foi identificada explicitamente como tal: não é o tempo de deslocamento entre escolas.

Verificação atual do domínio: cursos são matrizes compartilhadas e chegam às unidades por meio de turmas; o motor hoje escolhe também os horários das disciplinas. Transformar esse comportamento em seleção exclusiva de professores sobre uma distribuição de matérias fixa depende da definição dos horários curriculares por turma. O motor consulta `MatrizDistancia.tempo_minutos`; endereços ainda não geram trajetos automaticamente. A forma de obter trajetos e a fixação da distribuição curricular estão sendo esclarecidas com o usuário antes de alterar esse modelo. Os 15 testes de integração da página principal passaram após os ajustes de clareza.

## Preenchimento até janeiro de 2027 — 09/11/2026

A pedido, o cenário local foi preenchido de 09/11/2026 a 31/01/2027, com 60 aulas por semana nas 12 semanas do período. Foram adicionadas 660 aulas; a semana de 09/11 já preenchida e as 12 aulas antigas de setembro foram preservadas. As disponibilidades foram copiadas por dia da semana a partir de 09/11/2026, exclusivamente para os professores fictícios IDs 5 a 14 do cenário conhecido. Recusas e disponibilidades existentes não são sobrescritas. Nenhum nome novo foi criado e não há marcadores nos nomes.

O comando `preencher_periodo_local --de 2026-11-09 --ate 2027-01-31 --semana-modelo 2026-11-09 --professores 5 6 7 8 9 10 11 12 13 14` executa o gerador e a mesma confirmação/validação transacional para cada semana, preservando aulas fixas e sem duplicação. Todo o lote é revertido se uma semana não for completada. É restrito a `db.automacao.sqlite3`; backup anterior em `db.automacao.antes-janeiro-20261109_211731.sqlite3`. O cenário segue o calendário semanal cadastrado; não representa feriados/recessos reais. Não houve migração, alteração de jornada ou escrita no banco original.

Removido o rótulo **Salva** de cada card e de cada célula do PDF; o marcador **Prévia** permanece somente para propostas não confirmadas. A edição e o estado real das aulas continuam preservados.

## Grade editável unificada e PDF — 09/11/2026

O quadro semanal passou a ser a própria área de edição, sem segunda tabela diária. Cada aula oferece **Editar** (salva) ou **Ajustar** (prévia); os horários vazios oferecem **+**. O editor abre na mesma página e mantém os modos por unidade, turma, professor ou curso, filtros e datas. A seleção curricular reúne turma e disciplina e preserva os vínculos da demanda. Uma aula legada pode continuar sem esses vínculos. A geração e as correções manuais usam a mesma distribuição.

Correções de prévia validam novamente o lote inteiro, mantêm as aulas fixas e não gravam no banco. Turma e unidade da aula proposta são mantidas; professor, data dentro da semana e horário podem ser ajustados se respeitarem as regras. Cada ajuste troca o token para rejeitar editores antigos. A confirmação continua necessária. Para corrigir aulas já salvas ou adicionar manualmente, confirme/descarte a prévia pendente primeiro. A edição salva usa controle de versão assinado e nova validação transacional, preservando IDs e vínculos; não há sobregravação silenciosa. Disponibilidade do dia está em uma seção própria na mesma página e não mantém uma grade duplicada.

**Baixar PDF** exporta o período, agrupamento e filtro exibidos para `/grade.pdf`. O PDF identifica aulas salvas e propostas; uma prévia sai explicitamente marcada **PRÉVIA NÃO CONFIRMADA** e não grava nada. Prévias expiradas/desatualizadas são recusadas na exportação. A tabela inclui os sete dias e todos os registros de cada célula, com cabeçalho repetido em páginas adicionais. Os PDFs mobile anteriores continuam disponíveis.

A pedido, foram retirados os marcadores dos nomes de 31 registros de exemplo (curso, turmas, unidades, professores e disciplinas), mantendo IDs, relações e notas de que o cenário é fictício. Backup anterior: `db.automacao.antes-renomear-20261109_210519.sqlite3`. Essa alteração ocorreu somente na cópia local, sem migração. O novo exemplo opcional de curso também usa nome sem marcador. A restrição de uma aula por unidade/intervalo e a jornada de quatro aulas por turno permanecem.

Validação desta etapa: **140 testes aprovados**, migrações em dry-run sem mudanças, grade principal e endpoint PDF renderizados com status 200 usando os cadastros atuais. O PDF de QA foi renderizado em PNG e inspecionado visualmente, incluindo os sete dias, 24 aulas, aviso de prévia e rodapé; o cenário cabe em uma página A3 horizontal. A interface HTML foi validada por renderização/testes; não houve nova inspeção por navegador nesta etapa devido ao bloqueio anterior do controle de navegador. Foram comparados 316 registros do banco com o backup: somente os nomes autorizados mudaram, mantendo os demais campos e relações. Integridade SQLite aprovada e SHA-256 do banco original inalterado. Serviço local reiniciado.

## Cenário visual cadastrado a pedido — semana de 09/11/2026

Abra **http://localhost:8000/?data=2026-11-09&por=curso** com sua conta administrativa. Foram adicionados à cópia local um curso `[DEMO VISUAL] Preparatório 1`, sua matriz de 24 aulas de 50 minutos, duas unidades (Horizonte e Jardim), duas turmas e oito professores fictícios com habilitações e disponibilidades demonstrativas. Cada turma tem 20 aulas na manhã e quatro no contraturno de quarta-feira, escolhido explicitamente somente para este cenário; turno e dia continuam editáveis. Inglês foi escolhido para a única aula de idioma, sem impor essa escolha a cadastros reais. Os componentes compostos são escolhas demonstrativas editáveis.

Há duas aulas fixas demonstrativas na segunda às 08:00 (uma por unidade). Clique **Gerar grade**: a validação com os cadastros presentes produziu **58 novas propostas sem pendências**, totalizando 60 aulas nesta semana (48 do novo curso e 12 demandas do cenário antigo). As 58 propostas não foram persistidas pelo povoamento. As disponibilidades dos dois professores fictícios do cenário antigo foram completadas apenas nas novas datas, sem alterar registros/recusas existentes, para que suas demandas também possam ser atendidas. Nenhuma disponibilidade de professor real foi inventada. Não foram criadas contas.

Comando reprodutível: `python manage.py preparar_demo_visual --semana 2026-11-09 --dia-contraturno 2`. Recusa outros bancos, executa em transação, não duplica ou sobrescreve o cenário existente e reverte tudo se o gerador não validar a viabilidade. O banco foi protegido pelo backup SQLite `db.automacao.antes-demo-visual-20261109_205225.sqlite3` antes do povoamento. Não houve migração nem alteração de jornada. Aulas antigas de setembro e demais cadastros foram preservados.

## Correção de integração — 09/11/2026

A **página principal Grade Horária (`/`)** agora contém a geração, a prévia, a confirmação e as quatro perspectivas da distribuição. As rotas `/automacao/` e `/consultar/` descritas no histórico abaixo foram mantidas por compatibilidade; não são necessárias para esse fluxo e não são usadas pelos controles principais.

1. Escolha a data na Grade Horária. A distribuição mostra todos os sete dias da semana, inclusive sábado e domingo para não esconder alocações existentes. Os controles **Unidade, Turma, Professor e Curso** reorganizam as mesmas aulas na própria página. Existe um único filtro contextual, relativo ao modo selecionado. Aulas sem curso/turma aparecem em **Sem vínculo / legado**. Cada célula pode representar todos os registros de sua projeção, sem substituir uma aula por outra.
2. Clique **Gerar grade**, na própria página. O cálculo usa os cursos, matrizes, demandas, turmas e disponibilidades cadastrados. As novas aulas aparecem como **Prévia**, ao lado das aulas **Salvas**, na distribuição semanal. Os selects da edição manual do dia também são preenchidos com a proposta correspondente àquela data. Nada é gravado nessa etapa.
3. Troque de modo, filtro ou dia sem descartar a prévia da sessão. Ao visitar outra semana, um aviso oferece voltar à semana da proposta. A confirmação é oferecida na semana da proposta. Filtros só mudam a visualização: gerar e confirmar abrangem a semana inteira; a interface informa quantas aulas existem fora do filtro.
4. Clique **Confirmar e salvar** ali mesmo. A confirmação usa o token e as propostas da sessão no servidor; não aceita uma lista de aulas enviada pelo navegador como fonte de verdade. Mantém validação transacional, detecção de mudanças, validade de 30 minutos, disponibilidade, habilitações, deslocamento, parentesco, limites, preservação das aulas fixas e proteção contra duplicação. Prévia parcial exige aceite específico. Pendências aparecem junto à distribuição.
5. A **Edição manual**, expansível na mesma página, preserva os campos e o serviço anteriores. Durante uma prévia pendente, fica bloqueada no navegador **e no servidor**, evitando salvar uma proposta como aula legada sem seus vínculos. Confirme ou descarte antes de editar. Mudanças manuais não salvas recebem aviso ao sair; a geração pede que sejam salvas primeiro. O preenchimento da prévia não altera disponibilidade de professor.

Não há nova migração nesta correção. Mantida a restrição de **uma aula por unidade/intervalo**, sem criar salas ou liberar paralelo entre turmas da mesma unidade. A projeção por curso pode mostrar simultaneamente aulas de unidades diferentes, e não as colapsa em um único registro. A geração complementa a distribuição preservando alocações fixas; não reorganiza silenciosamente aulas já salvas. CRUD de cursos/matrizes e calendário continua disponível em **Cadastros**.

Arquivos centrais da correção: `grade/views.py`, `grade/automacao.py`, `grade/distribuicao.py`, `grade/templates/grade/grade_tabela.html`, `grade/templates/grade/distribuicao_semana.html`, `grade/static/grade/distribuicao.css`, `grade/static/grade/distribuicao.js` e `grade/test_grade_integrada.py`. A nova suíte inclui preenchimento de campos, todos os dias, quatro modos, navegação e filtros sem perda de estado, legado, múltiplos registros por projeção, geração real, preservação de fixas, confirmação/descartar na página principal, compatibilidade manual, stale detection, proposta parcial, token, CSRF e permissões. HTMLs opcionais em `output/grade-integrada-qa/` são artefatos de inspeção com dados fictícios do banco temporário de testes; não são cadastros de demonstração no banco de trabalho.

## Cursos e calendário por turma — implementação local de 03/11/2026

Na branch `feat/automacao-semanal`, a grade principal oferece **Cursos**, **Turmas**, **Gerar grade** e **Consultar por professor, unidade, curso ou turma**. Todas essas rotas exigem autenticação e usuário ativo da coordenação (`is_staff`), conferidos no servidor. Professores continuam usando sua consulta restrita em `/mobile/` e o PDF existente. Nada foi publicado.

- `/cursos/`: criar, consultar, editar e excluir cursos. A matriz informa **quantidade de aulas semanais por disciplina**. Após salvar, demandas das turmas vinculadas são sincronizadas automaticamente e de forma idempotente. Cursos vinculados a turmas não podem ser excluídos.
- `/turmas/`: cadastrar/editar turma, unidade, curso, dias, turno principal e dia opcional do contraturno. Nenhum dia de contraturno é escolhido automaticamente. O turno vazio preserva o produto dias × horários do calendário legado. Com turno configurado, valem os quatro intervalos oficiais do turno principal nos dias úteis selecionados, mais os quatro do turno oposto **apenas no dia escolhido**. Para o arranjo aprovado de 20 + 4, selecione segunda a sexta e um dia de contraturno. Horários manuais são usados somente no modo legado. Não são criadas disponibilidades de professores.
- `/automacao/`: usa as demandas alimentadas pelos cursos, com prévia privada, confirmação transacional e detecção de alterações inclusive na matriz. Disponibilidade, habilitações, deslocamento, parentesco, limites e aulas fixas continuam sendo validados.
- `/consultar/`: consulta semanal das mesmas alocações salvas, com filtros combináveis e agrupamento por professor, unidade, curso ou turma. Aulas legadas sem vínculo aparecem em grupo próprio; não se atribui um curso fictício a elas. Filtros por turma/curso selecionam somente vínculos conhecidos.

O botão **Criar exemplo editável [DEMO]** em Cursos é opt-in. Cria `Preparatório 1 [DEMO]` com Matemática 4; Português e interpretação 3; Redação 2; Biologia 3; Física 3; Química 3; História 2; Geografia 2; Filosofia e Sociologia 1; Inglês ou Espanhol 1. São 24 aulas de 50 minutos, 1.200 minutos = 20 horas semanais sem intervalos. Não cria turma, professor, disponibilidade ou aula e recusa repetir o exemplo. Reutiliza a primeira disciplina de nome exatamente igual quando existente, sem modificar esse cadastro; caso contrário cria o componente. A coordenação deve revisar os componentes compostos e definir o idioma/habilitação: os nomes são escolhas demonstrativas editáveis, não regra universal nem habilitação automática para duas disciplinas/idiomas.

Ao retirar um componente ou desvincular um curso de turma sem aulas, a demanda originada da matriz fica inativa, preservando ID e alocações. Reintroduzir o componente reutiliza a demanda. O professor opcional é preservado. Demandas manuais que colidem com uma matriz bloqueiam o vínculo/edição, sem conversão silenciosa; devem ser revisadas pela coordenação. Reduções abaixo da quantidade já alocada em qualquer semana são recusadas, com rollback. Para mudar esse histórico, crie outra versão de curso/turma. Não é permitido trocar/remover o curso de turma que já possui aulas. A carga de demandas geridas deve ser editada na matriz, não diretamente no admin. Não use `bulk_create`, `bulk_update` ou `QuerySet.update` em cursos/matrizes/turmas: esses caminhos não executam os sinais de sincronização; use as telas ou `save()` em transação.

**Paralelo por turma permanece bloqueado.** A consulta nova representa cada turma explicitamente, mas a edição diária e os serviços legados ainda têm uma célula por unidade/intervalo. Liberar paralelo apenas no motor criaria perda de representação/edição. Sem um modelo consistente de capacidade/salas e adaptação desses serviços, a restrição conservadora continua em vigor; não foram inventadas salas. Isso pode deixar demandas de várias turmas da mesma unidade pendentes.

A migração `0006` é aditiva: não transforma cadastros legados nem cria o exemplo. O banco efetivo foi conferido pelo `settings.DATABASES` do contêiner como `db.automacao.sqlite3`. A cópia deve receber backup SQLite antes de migrar. Não execute migrações no `db.sqlite3` original. O contêiner está com `--noreload`: após alterações de código, reinicie o serviço local para carregá-las (`docker compose restart web`). A jornada global permanece com quatro aulas, almoço 11:20–12:20, manhã 08:00–11:20 e tarde 12:20–15:40.

Validação realizada em 03/11/2026: `python manage.py test grade --noinput` passou com **112 testes**; `makemigrations --check --dry-run` não detectou mudanças; `migrate --plan` mostrou somente `0006`; `check` não encontrou problemas. Backup consistente criado via API SQLite em `db.automacao.antes-cursos-20261103_225923.sqlite3`, com integridade verificada. A migração foi aplicada somente à cópia e o serviço local foi reiniciado. Após migrar, o SHA-256 do `db.sqlite3` original permaneceu idêntico ao registrado antes da migração, a cópia passou em `PRAGMA integrity_check` e foram preservadas as contagens de aulas, turmas, demandas, professores, horários e usuários. Nenhum exemplo foi cadastrado automaticamente. As cinco páginas principais renderizaram com status 200 usando usuário administrativo existente; acesso HTTP sem autenticação levou ao login. A suíte inclui CRUD pela interface, sincronização, rollback, proteção de histórico, permissões, 24 aulas com contraturno específico, confirmação sem duplicar e consultas nas quatro perspectivas.

A coordenação pode gerar uma proposta para a semana inteira em `/automacao/`, pelo botão **Automatizar semana** na grade diária. O cálculo roda no servidor com OR-Tools CP-SAT, sem enviar dados a uma IA ou serviço de mapas e sem cobrança por chamada. Permanecem os custos de hospedagem, processamento e manutenção.

## Testar agora neste ambiente

1. Abra http://localhost:8000/automacao/?semana=2026-09-21 e entre com sua conta administrativa existente.
2. Selecione uma data da semana de **21 a 27/09/2026**. A semana começa na segunda-feira.
3. Mantenha proximidade em **15 minutos** e clique em **Gerar prévia da semana**.
4. Confira os professores `[DEMO] Ana` e `[DEMO] Bruno`, as duas escolas e as 12 aulas solicitadas. A prévia inicial atende às 12 aulas sem pendências neste cenário.
5. Clique em **Confirmar e adicionar aulas** para experimentar a gravação. Gere novamente: as aulas confirmadas serão fixas e não serão duplicadas.
6. Consulte a grade diária na data indicada na proposta. Para corrigir uma aula planejada, use **Administração → Alocações de grade**, mantendo turma, disciplina e demanda compatíveis.

O `.env` local contém `SQLITE_NAME=db.automacao.sqlite3`. Toda a aplicação, inclusive admin e mobile, usa essa **cópia** durante os testes. As contas originais foram preservadas na cópia. O arquivo `db.sqlite3` não recebeu migrações nem dados de demonstração. Ambos os bancos e o `.env` estão excluídos do Git.

O cenário é fictício: 2 professores com vínculo de parentesco cadastrado em apenas um sentido, 2 escolas, 2 turmas, 8 horários oficiais, 4 demandas de 3 aulas semanais e disponibilidades pela manhã e à tarde nas cinco datas úteis. Reutiliza os horários da grade, sem criar horários exclusivos da demonstração. Não cria contas novas nem grava aulas automaticamente. Para reproduzir em outra cópia:

```powershell
docker compose exec web python manage.py migrate
docker compose exec web python manage.py preparar_demo_automacao --semana 2026-09-21
```

O comando de demonstração recusa qualquer banco cujo nome não seja `db.automacao.sqlite3` e não sobrescreve um cenário já criado.

## Cadastros necessários

- **Professor:** disciplinas em que pode lecionar, unidade oficial, outras unidades permitidas, limite diário e parente opcional. A unidade oficial também é permitida.
- **Horários:** início e fim no mesmo dia. Aulas com IDs diferentes também conflitam quando os intervalos se sobrepõem.
- **Turma:** escola, dias da semana e horários nos quais pode receber aulas.
- **Demanda semanal:** turma, disciplina, quantidade de aulas e professor opcional. Sem professor definido, o gerador escolhe entre os habilitados. A demanda ativa se repete a cada semana solicitada; não é uma reserva para uma única data.
- **Disponibilidade:** é específica de cada data. Sem cadastro, o professor é considerado indisponível. Manhã: 08:00–11:20; tarde: 12:20–15:40. A disponibilidade por horário, inclusive uma recusa, prevalece sobre o turno, mas não permite aulas durante o almoço.
- **Deslocamento:** minutos de cada trajeto entre escolas. Cadastre ida e volta, que podem ter valores diferentes. Não há consulta automática de quilômetros ou trânsito. O cadastro deve representar um tempo adequado ao transporte dos professores; esta versão usa uma matriz única para todos.

Inativar uma demanda impede novas aulas nessa demanda e preserva as que já existem. Aulas planejadas mantêm os três vínculos (turma, disciplina, demanda). Aulas legadas sem esses vínculos continuam como fixas, mas não são descontadas automaticamente de uma demanda: o coordenador precisa vinculá-las antes de gerar para que sejam contabilizadas.

## Regras e prioridades

O gerador primeiro maximiza a quantidade de aulas atendidas, sem exceder a demanda semanal. Somente quando comprova a melhor cobertura passa a melhorar as preferências, sem reduzir essa quantidade.

As regras obrigatórias são disponibilidade, habilitação na disciplina, escolas permitidas, calendário da turma, limite de aulas por dia, ausência de sobreposição e tempo suficiente para deslocamento. Veículo próprio não dispensa o tempo de trajeto. Um trajeto ausente impede o deslocamento, em vez de presumir um tempo arbitrário. Os antigos campos de exceção não autorizam violar essas regras.

**Parentesco vale para os dois:** basta A apontar para B ou B apontar para A. Nos dias em que ambos têm aulas, o cálculo favorece manter todas as escolas de ambos iguais ou próximas. Não obriga um parente a trabalhar se ele não tem demanda. Proximidade usa ida **e** volta dentro do limite escolhido; **15 minutos é apenas o valor inicial configurável**. Fora desse limite, ou sem trajeto cadastrado, aparece aviso, sem bloquear a grade. A preferência considera o dia inteiro e não exige que os dois tenham o mesmo turno.

A segunda etapa penaliza pares de aulas de parentes distantes com peso 10 e pares de aulas do mesmo professor em escolas diferentes com peso 1. É uma preferência ponderada, não uma garantia de que todo parentesco será atendido. Pode encerrar com uma solução válida antes de provar a melhor distribuição; a tela informa isso.

## Gravação e proteção do trabalho existente

- Gerar apenas cria uma prévia privada na sessão do coordenador. Só a confirmação adiciona aulas.
- Todas as aulas salvas da semana são fixas. O gerador não as troca nem apaga.
- A proposta expira em 30 minutos. Mudanças na semana ou nos cadastros exigem nova geração.
- Na confirmação, o servidor usa sua própria proposta, confere novamente todas as regras e grava em uma transação.
- Uma grade parcial informa quantas aulas faltam e exige confirmação específica. Tempo esgotado sem solução não é apresentado como prova de impossibilidade.
- A montagem manual valida o lote inteiro antes de gravar. Uma falha preserva os dados e mantém a tentativa na tela. As células mantidas conservam IDs, vínculos e auditoria.
- A tabela diária antiga não edita nem remove aulas vinculadas ao planejamento. A administração permite editar essas aulas com validação dos vínculos e da demanda semanal.
- Admin/API validam criação e edição de aulas; alterações de cadastros podem tornar aulas existentes incompatíveis com a nova realidade. A próxima geração/confirmação detecta essa situação e pede correção, sem substituir a grade.
- Aulas confirmadas aparecem no mobile e no PDF do professor vinculado, com disciplina e turma.

## Limites desta versão

O formato atual da grade comporta **uma aula por escola em cada intervalo**, mesmo que haja várias turmas. O motor preserva essa limitação para evitar aulas invisíveis na tabela existente. Aulas paralelas por turma exigirão uma mudança posterior na grade desktop.

O tempo de deslocamento é conferido de forma conservadora entre todos os pares de aulas do professor no dia. A matriz deve conter tempos diretos coerentes; o gerador não calcula rotas com escalas ou condições de trânsito.

### Horários e almoço

As aulas são consecutivas, com 50 minutos cada:

| Aula | Manhã | Tarde |
| --- | --- | --- |
| 1 | 08:00–08:50 | 12:20–13:10 |
| 2 | 08:50–09:40 | 13:10–14:00 |
| 3 | 09:40–10:30 | 14:00–14:50 |
| 4 | 10:30–11:20 | 14:50–15:40 |

Almoço: **11:20–12:20**. Nesse intervalo não são agendadas aulas. A hora de pausa conta no tempo disponível para deslocamento: entre a última aula da manhã e a primeira da tarde, trajetos de até 60 minutos cabem; trajetos de 61 minutos não. Não se soma outra hora ao deslocamento. Entre aulas seguidas não há intervalo para mudar de escola quando o trajeto exige tempo positivo.

A configuração `GRADE_AULAS_POR_TURNO = 4` considera 11:20 como o fim da manhã. O cálculo dos dois turnos e do almoço está centralizado em `grade/jornada.py`; caso a quantidade seja alterada, os cadastros e calendários devem ser revisados junto com a configuração. A geração usa os dias/horários e a disponibilidade efetivamente cadastrados, sem presumir que professores reais estejam disponíveis à tarde.

O comando `python manage.py normalizar_horarios` consolida duplicados e remapeia os três horários antigos da demonstração, preservando aulas, turmas e disponibilidades. Faz rollback se a correção causar conflitos e recusa horários desconhecidos para não descartá-los. Deve ser precedido de backup. Admin e API rejeitam novo cadastro com início e fim já existentes.

O cálculo na tela recebe cerca de 10 segundos, com limites de 200 demandas ativas, 300 professores, 100 horários, 500 aulas fixas, 1.500 candidatos e 200 mil comparações. Ao exceder esses limites, solicita reduzir as opções e não grava aulas. Crescimento para grandes redes exigirá tarefas em segundo plano e revisão desses limites, além de testes de carga. A proteção de confirmação concorrente foi implementada para o SQLite atual; migrar para outro banco exige revisar a estratégia de bloqueio.

## Validação e retorno ao ambiente anterior

```powershell
docker compose exec web python manage.py test grade
docker compose exec web python manage.py makemigrations --check --dry-run
```

A suíte usa um banco temporário do Django, separado dos arquivos de trabalho. Inclui casos positivos e negativos de disponibilidade, parentesco nos dois sentidos, deslocamento, sobreposições, demanda, rollback, API, confirmação, preview desatualizado e consulta mobile.

As alterações estão locais na branch `feat/automacao-semanal`, sem commit ou push nesta etapa. Para voltar ao código anterior, primeiro preserve o trabalho dessa branch em commit local ou stash, pare o servidor, retorne à branch anterior e remova `SQLITE_NAME` do `.env`. Recrie o serviço para recarregar a configuração. Não remova essa variável mantendo o código novo sem antes planejar a migração do banco original. Não é necessário apagar nenhum banco.

Referência do motor: [documentação oficial CP-SAT](https://developers.google.com/optimization/cp/cp_solver).
