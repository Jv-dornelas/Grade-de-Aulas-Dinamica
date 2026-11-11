# Entradas utilizadas pela automação

Auditoria de 11/11/2026. A tabela distingue campos de cadastro, informações calculadas e regras fixas; não basta existir uma coluna no banco para considerá-la configurável.

| Informação | Onde preencher | Uso efetivo |
|---|---|---|
| Nome, telefone e e-mail do professor | Professor → Cadastrar/Atualizar | Identificação e contato; telefone/e-mail não alteram a distribuição |
| Disciplinas habilitadas | Ficha do professor | Restrição obrigatória para atribuir docentes |
| Limite diário de aulas | Ficha do professor | Restrição obrigatória por professor/data |
| Unidade oficial e unidades adicionais permitidas | Ficha do professor | Determinam em quais unidades pode lecionar |
| Vínculo familiar/conjugal | Ficha do professor | Preferência simétrica de proximidade; um dos lados basta |
| Proximidade familiar, em minutos | Professor → Critérios da automação, `/configuracoes/` | Limite administrativo consumido pelo motor; distância maior gera aviso, sem bloquear por si só |
| Meio de transporte | Ficha do professor | Informativo; não estima velocidade nem muda automaticamente o tempo do trajeto |
| Observações do professor | Ficha do professor | Consulta humana; texto livre não é interpretado como regra pelo gerador |
| Conta mobile existente | Ficha do professor | Vincula a identidade para consulta individual; não participa do cálculo |
| Endereço, cidade e CEP | Unidade → Cadastrar/Atualizar | Entrada para consulta dos trajetos pelos endereços |
| Tempo de ida/volta e distância em km | Ficha da unidade → Trajetos | O motor usa os **minutos dirigidos** para deslocamento; km são informação complementar |
| Consulta por mapas e aplicação da rota | Ficha da unidade | Consulta com conferência e confirmação; os pontos precisam identificar a unidade corretamente |
| Salas e situação ativa | Unidade → Salas, `/salas/` | Capacidade física; sala/turma/professor não podem sobrepor |
| Disciplina e área | Disciplina → Cadastrar/Atualizar | A disciplina é usada na habilitação/matriz; a área organiza o catálogo |
| Curso, componentes e carga semanal | Curso → Cursos e matriz | Origem das quantidades semanais; a carga conta aulas, não horas de 60 minutos |
| Unidade/curso da turma, dias, turno e contraturno | Turma → Cadastrar/Atualizar | Define o calendário possível de cada oferta |
| Restrição pontual por turno | Grade → Disponibilidade dos professores | Exceção explícita por data; ausente significa disponível |
| Restrição pontual por horário | Professor → Restrições por horário, `/professores/restricoes/` | Tem prioridade sobre a regra do turno; permite bloquear ou liberar um intervalo |
| Horários fixos opcionais de matérias | Link na turma em modo fixo, `/turmas/<id>/materias/` | Compatibilidade opcional; no fluxo principal a ordem é livre |
| Professor/sala de uma aula específica | Editor da própria grade | Ajuste manual ou opção Sem professor; mesmas regras de validação |
| Semana de geração e período de replicação | Própria grade | Seleciona o período; cópia exige prévia e confirmação |

## O que não deve exigir digitação independente

- `DemandaAula` é a projeção sincronizada da matriz do curso. Não foi reaberto um CRUD individual de cargas.
- Datas de criação/alteração, assinatura de prévia, token, aprovação, fonte da rota, coordenadas/cache e assinatura de endereço são internos ou calculados.
- A jornada aprovada de quatro aulas de 50 minutos por turno é fixa nesta versão. A tela de critérios mostra os horários, mas não permite alterá-los para cinco aulas.
- Limites técnicos de cálculo e as regras obrigatórias de conflito não são cadastros operacionais. Não há botão para desativar a validação de professor/turma/sala.
- Criação de contas, senhas e permissões continua na administração técnica Django; a ficha permite vincular uma conta mobile existente. Não é um requisito para gerar a grade.

## Proteção dos dados já salvos

A ficha de professor é transacional: valida tipos, vínculos, concorrência e as semanas já alocadas. Remover uma habilitação/unidade ou reduzir o limite de maneira incompatível é recusado sem gravar parcialmente. Contas privilegiadas de outros usuários não são oferecidas como novas contas de professor.

Exceções por horário também validam as semanas afetadas antes de confirmar. Um bloqueio que torne inválida uma aula existente é recusado; remover uma liberação também é validado, pois pode fazer voltar um bloqueio por turno.

Alterar o critério de proximidade muda a assinatura usada pela prévia. O valor enviado no campo oculto da geração não substitui a configuração administrativa.

## Verificação

`grade/tests/test_cadastros_criterios.py` verifica todos os campos editáveis da ficha, gravação dos vínculos, leitura do parâmetro pelo motor, restrições por horário, rollback, concorrência, CSRF e permissões. Os testes de cursos, mapas, salas e restrições cobrem as demais entradas da tabela.
