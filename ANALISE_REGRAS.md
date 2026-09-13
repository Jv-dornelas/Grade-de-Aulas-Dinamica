# 📋 ANÁLISE DE CONFORMIDADE DAS REGRAS DE NEGÓCIO

## ✅ REGRAS IMPLEMENTADAS (Funcionando)

### 1. ✅ Professores relacionados por parentesco no mesmo turno/unidade
- **Status**: IMPLEMENTADO (Parcialmente)
- **Código**: `services.py` - método `verificar_parente_vinculado()` + template (detecção de "cônjuge")
- **Template**: Linha ~306-319 - Validação de cônjuges com alerta amarelo
- **Campo BD**: `Professor.parente_vinculado` (ForeignKey self)
- **Limitação**: Apenas 1 parente por vez; não trata múltiplas relações

---

### 2. ✅ Professor não pode estar em 2 unidades ao mesmo tempo
- **Status**: IMPLEMENTADO
- **Código**: `services.py` - método `verificar_conflito_horario()` (linhas 59-71)
- **Lógica**: Bloqueia se `AlocacaoGrade` existe com mesmo (professor, data, horario)
- **Feedback**: Mensagem de erro em vermelho no template

---

### 3. ✅ Imprimir a grade ao final
- **Status**: IMPLEMENTADO
- **Código**: Template `grade_tabela.html` (linhas 16-29 CSS `@media print`)
- **Ação**: Botão "🖨️ Gerar PDF / Imprimir" chama `window.print()`
- **Output**: Remove painéis laterais, mostra apenas tabela limpa para impressão/PDF

---

### 4. ✅ Mostrar horários na tabela
- **Status**: IMPLEMENTADO
- **Código**: Template (linhas 143-148)
- **Output**: 1ª coluna da tabela mostra `{{ horario.nome }}` (ex: "1ª aula", "2ª aula")
- **Campo BD**: `HorarioAula.hora_inicio` e `hora_fim` existem mas NÃO aparecem no template

---

### 5. ✅ Calcular distância entre escolas e validar transporte
- **Status**: IMPLEMENTADO (Mas com lógica simplificada no frontend)
- **Código BD**: `MatrizDistancia` (modelo completo com `tempo_minutos`)
- **Backend**: `services.py` - método `verificar_deslocamento_e_transporte()` (linhas 73-119)
- **Frontend**: Template (linhas 252-296) - lógica JavaScript que:
  - Detecta se professor muda de unidade entre aulas consecutivas
  - Verifica intervalo entre aulas (0 min, 15 min, ou mais)
  - Valida se o transporte permite (carro/moto = OK; público/a pé = mais restritivo)
  - Pinta vermelho (crítico) ou amarelo (aviso)
- **Limitação**: 
  - Intervalo de tempo é *hardcoded* no JS (não usa MatrizDistancia do BD)
  - Apenas detecta mudanças entre aulas consecutivas (não calcula rotas complexas)

---

## ⚠️ REGRAS PARCIALMENTE IMPLEMENTADAS

### 6. ⚠️ Professor definir quantas aulas pode dar no dia
- **Status**: IMPLEMENTADO no backend, mas **NÃO VALIDADO no frontend**
- **Campo BD**: `Professor.limite_aulas` (default=5)
- **Backend**: `services.py` (linhas 153-157) valida antes de salvar
- **Frontend**: 
  - Exibe contador de aulas por professor nas estatísticas (linha ~397)
  - **MAS**: Não impede o usuário de selecionar antes de salvar
  - Validação só ocorre ao clicar "Salvar Tudo"
- **UX Problem**: Usuário preenche a grade, clica salvar, vê erro. Poderia ser bloqueado em tempo real.

---

### 7. ⚠️ Não acumular aulas de mesma área no mesmo período
- **Status**: IMPLEMENTADO (Detecção, mas sem bloqueio)
- **Campo BD**: `Disciplina.area` (EXATAS, HUMANAS, BIOLOGICAS)
- **Backend**: **NÃO TEM VALIDAÇÃO** (serviço não verifica áreas)
- **Frontend**: Template (linhas ~397-416) - Estatísticas mostram contagem por área/unidade
  - Exibe tabela: "Aulas por Unidade (Área)" com contagem de Exatas, Humanas, Bio
  - **MAS**: É apenas informativo, não bloqueia acúmulo
- **UX Problem**: 
  - Sem limite explícito, usuário pode colocar 5 aulas de Exatas na mesma unidade pela manhã
  - Aviso visual seria melhor (ou bloqueio com limite configurável)

---

### 8. ⚠️ Avisar qual critério tá sendo sinalizado
- **Status**: IMPLEMENTADO (Parcialmente)
- **Implementação**:
  - Vermelho = Conflito crítico (impossível geograficamente ou duplicação)
  - Amarelo = Aviso (requer cuidado, mas não é bloqueante)
- **Critérios com cores**:
  - ✅ Mesmo professor em 2 horários = Vermelho
  - ✅ Deslocamento sem intervalo entre unidades distantes = Vermelho
  - ✅ Deslocamento com tempo insuficiente + sem carro = Amarelo
  - ✅ Cônjuges em unidades/turnos diferentes = Amarelo
  - ✅ Acúmulo de aulas (sem intervalo) = Amarelo
- **Limitação**: 
  - Cores são visuais mas **nenhuma mensagem textual** diz qual regra foi violada
  - Usuário vê "vermelho" mas não sabe exatamente por quê
  - Falta tooltip/legenda explicando cada cor

---

### 9. ⚠️ Sistema gera escala para coordenador aceitar/atualizar
- **Status**: NÃO IMPLEMENTADO
- **O que existe**:
  - App permite preenchimento manual da grade pelo coordenador
  - Backend valida regras de negócio
- **O que NÃO existe**:
  - ❌ Algoritmo de geração automática (por agora é manual)
  - ❌ Workflow de aceitar/rejeitar (não há versão de "proposta" vs "final")
  - ❌ Histórico de alterações
  - ❌ Assinatura digital/aprovação formal
- **Necessário para completar**:
  - Criar um serviço de "geração de sugestões" via algoritmo genético ou constraint satisfaction
  - Implementar status de grade (RASCUNHO, PROPOSTA, APROVADA, ARQUIVADA)
  - Criar view para comparação antes/depois

---

## ❌ REGRAS NÃO IMPLEMENTADAS

### 10. ❌ Horários/disponibilidade atualizados semanalmente (Automação)
- **Status**: NÃO IMPLEMENTADO
- **O que seria necessário**:
  - ❌ Task scheduler (Celery, APScheduler ou cron)
  - ❌ Email notificando professores para atualizar disponibilidade
  - ❌ Persistência de disponibilidades semanais padrão (se houver padrão)
  - ❌ Interface para replicar semana anterior
- **Arquivo sugerido**: `grade/tasks.py` (ainda não existe)

---

### 11. ❌ CRUDs limpadores de cadastros (Admin Panel)
- **Status**: PARCIALMENTE IMPLEMENTADO (Django admin padrão existe, mas é bruto)
- **O que existe**:
  - Django admin nativo (não customizado)
  - Acesso em `/admin`
- **O que falta**:
  - ❌ Interface customizada para deletar alocações por data/intervalo
  - ❌ Confirmação com preview antes de deletar
  - ❌ Logs de remoção
  - ❌ Filtros avançados no admin
- **Arquivo sugerido**: `grade/admin.py` (customizar classe AdminSite)

---

### 12. ❌ Pasta de validações organizada (Arquitetura)
- **Status**: NÃO IMPLEMENTADO
- **O que existe**:
  - Validações espalhadas: `services.py` (backend) + `grade_tabela.html` (frontend)
- **O que falta**:
  - ❌ Pasta `grade/validadores/` com classes específicas:
    - `HorarioValidator`
    - `DeslocamentoValidator`
    - `DisponibilidadeValidator`
    - `ParentescoValidator`
    - `AreaAcumuloValidator`
  - ❌ Interface comum (base class)
  - ❌ Testes unitários para cada validador
- **Arquivo sugerido**: `grade/validadores/__init__.py` (novo)

---

### 13. ❌ Documentação técnica
- **Status**: NÃO IMPLEMENTADO
- **O que falta**:
  - ❌ README.md com guia de setup
  - ❌ Diagramas de arquitetura (Mermaid/Draw.io)
  - ❌ Dicionário de dados (models)
  - ❌ Guia de regras de negócio (fluxograma)
  - ❌ API docs (DRF documentação)
  - ❌ Guia do usuário (coordenador)
- **Arquivo sugerido**: `docs/` (pasta nova)

---

### 14. ❌ Automatização - Email
- **Status**: NÃO IMPLEMENTADO
- **O que seria necessário**:
  - ❌ Configurar SMTP (settings.EMAIL_*)
  - ❌ Template de emails (templates/emails/)
  - ❌ Função para enviar grade final ao coordenador
  - ❌ Notificação de conflitos pendentes
  - ❌ Relatório semanal por professor
- **Arquivo sugerido**: `grade/email_service.py` (novo)

---

### 15. ❌ Integrações (Google Maps, APIs externas)
- **Status**: NÃO IMPLEMENTADO
- **Sugestões**:
  - ❌ Google Maps API para calcular distância real entre unidades
  - ❌ Google Calendar para sincronizar grade com calendários pessoais
  - ❌ Twilio/WhatsApp para notificações de última hora
  - ❌ Integração com sistema de payroll (folha)
- **Arquivo sugerido**: `grade/integracoes/` (pasta nova)

---

## 📊 RESUMO

| Regra | Status | Prioridade | Esforço |
|-------|--------|-----------|---------|
| Parentesco (turno/unidade) | ✅ Sim | Média | Baixo |
| Sem 2 unidades simultâneas | ✅ Sim | Alta | Baixo |
| Imprimir grade | ✅ Sim | Média | Baixo |
| Mostrar horários | ✅ Sim | Baixa | Baixo |
| Distância/transporte | ✅ Sim (JS simples) | Alta | Médio |
| Limite aulas/dia | ⚠️ Parcial | Alta | Médio |
| Sem acúmulo mesma área | ⚠️ Aviso visual | Média | Médio |
| Avisar critério | ⚠️ Cores/Visual | Média | Baixo |
| Geração automática | ❌ Não | Alta | Alto |
| Automação semanal | ❌ Não | Média | Alto |
| Admin CRUDs | ❌ Bruto | Baixa | Médio |
| Pasta validadores | ❌ Não | Média | Médio |
| Documentação | ❌ Não | Baixa | Médio |
| Email automático | ❌ Não | Média | Médio |
| Integrações Maps/APIs | ❌ Não | Baixa | Alto |

---

## 🎯 PRÓXIMAS PRIORIDADES (Recomendadas)

1. **Bloqueio em tempo real**: Validar limite de aulas e acúmulo de áreas NO TEMPLATE (antes de salvar)
2. **Legenda de cores**: Adicionar tooltip explicando cada critério de validação
3. **Geração automática**: Criar algoritmo básico de sugestão (constraint satisfaction)
4. **Admin customizado**: Criar interface de limpeza/backup de grades
5. **Pastas de validadores**: Refatorar código para ficar testável e manutenível

---

## 🛠️ Arquivos a criar/modificar

### Criar
- `grade/validadores/__init__.py`
- `grade/validadores/horario.py`
- `grade/validadores/deslocamento.py`
- `grade/validadores/area.py`
- `grade/email_service.py`
- `grade/tasks.py` (Celery)
- `grade/admin.py` (customizado)
- `docs/README.md`
- `docs/REGRAS_NEGOCIO.md`

### Modificar
- `grade/templates/grade/grade_tabela.html` (adicionar tooltips, legenda)
- `grade/services.py` (validações em tempo real)
- `grade/views.py` (logging, auditoria)
- `settings.py` (SMTP, Celery, logging)

---

**Gerado em**: 2024
**Projeto**: Grade de Aulas Dinâmica CCM
