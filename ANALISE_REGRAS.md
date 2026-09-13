# 📋 ANÁLISE DE CONFORMIDADE DAS REGRAS DE NEGÓCIO

## ✅ REGRAS IMPLEMENTADAS (Funcionando)

### 1. ✅ Professores relacionados por parentesco no mesmo turno/unidade
- **Status**: IMPLEMENTADO (Parcialmente)
- **Código**: `services.py` - método `verificar_parente_vinculado()` + template (detecção de "cônjuge")
- **Template**: Linha ~306-319 - Validação de cônjuges com alerta amarelo
- **Campo BD**: `Professor.parente_vinculado` (ForeignKey self)
- **Flexibilidade**: ⚠️ **SEM EXCEÇÃO** - Apenas aviso visual (amarelo), não bloqueia
- **Limitação**: Apenas 1 parente por vez; não trata múltiplas relações

---

### 2. ✅ Professor não pode estar em 2 unidades ao mesmo tempo
- **Status**: IMPLEMENTADO
- **Código**: `services.py` - método `verificar_conflito_horario()` (linhas 59-71)
- **Lógica**: Bloqueia se `AlocacaoGrade` existe com mesmo (professor, data, horario)
- **Feedback**: Mensagem de erro em vermelho no template
- **Flexibilidade**: ✅ **COM EXCEÇÃO** - Campo `AlocacaoGrade.eh_excecao_horario` (proposto)
  - Permite sobrescrever com justificativa
  - Requer confirmação do coordenador

---

### 3. ✅ Imprimir a grade ao final
- **Status**: IMPLEMENTADO
- **Código**: Template `grade_tabela.html` (linhas 16-29 CSS `@media print`)
- **Ação**: Botão "🖨️ Gerar PDF / Imprimir" chama `window.print()`
- **Output**: Remove painéis laterais, mostra apenas tabela limpa para impressão/PDF
- **Flexibilidade**: N/A

---

### 4. ✅ Mostrar horários na tabela
- **Status**: IMPLEMENTADO
- **Código**: Template (linhas 143-148)
- **Output**: 1ª coluna da tabela mostra `{{ horario.nome }}` (ex: "1ª aula", "2ª aula")
- **Campo BD**: `HorarioAula.hora_inicio` e `hora_fim` existem mas NÃO aparecem no template
- **Flexibilidade**: N/A

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
- **Flexibilidade**: ✅ **COM EXCEÇÃO** - Campo `AlocacaoGrade.eh_excecao_deslocamento` (proposto)
  - Permite sobrescrever com justificativa
  - Registra meio de transporte alternativo usado
- **Limitação**: 
  - Intervalo de tempo é *hardcoded* no JS (não usa MatrizDistancia do BD)
  - Apenas detecta mudanças entre aulas consecutivas (não calcula rotas complexas)

---

## ⚠️ REGRAS PARCIALMENTE IMPLEMENTADAS (COM FLEXIBILIDADE)

### 6. ⚠️ Professor definir quantas aulas pode dar no dia
- **Status**: IMPLEMENTADO no backend, mas **NÃO VALIDADO em tempo real**
- **Campo BD**: `Professor.limite_aulas` (default=5)
- **Backend**: `services.py` (linhas 153-157) valida antes de salvar
- **Frontend**: 
  - Exibe contador de aulas por professor nas estatísticas (linha ~397)
  - **MAS**: Não impede o usuário de selecionar antes de salvar
  - Validação só ocorre ao clicar "Salvar Tudo"
- **Flexibilidade**: ✅ **NECESSÁRIA - COM EXCEÇÃO** 
  - Campo `AlocacaoGrade.eh_excecao_limite_aulas` (proposto)
  - Permitir exceder limite configurável (ex: até +2 aulas extras)
  - Exigir justificativa (motivo da exceção)
  - Aviso visual em tempo real: "⚠️ Professor X já tem 5 aulas (limite), adicionar 6ª?"
  - Checkbox "Autorizar exceção de limite"
- **UX Improvement**: 
  - Bloquear visualmente em tempo real (desabilitar select após limite)
  - Mostrar aviso com opção de "Permitir exceção com justificativa"

---

### 7. ⚠️ Não acumular aulas de mesma área no mesmo período
- **Status**: IMPLEMENTADO (Detecção, mas sem bloqueio)
- **Campo BD**: `Disciplina.area` (EXATAS, HUMANAS, BIOLOGICAS)
- **Backend**: **NÃO TEM VALIDAÇÃO** (serviço não verifica áreas)
- **Frontend**: Template (linhas ~397-416) - Estatísticas mostram contagem por área/unidade
  - Exibe tabela: "Aulas por Unidade (Área)" com contagem de Exatas, Humanas, Bio
  - **MAS**: É apenas informativo, não bloqueia acúmulo
- **Flexibilidade**: ✅ **NECESSÁRIA - COM EXCEÇÃO**
  - Campo `AlocacaoGrade.eh_excecao_area_acumulo` (proposto)
  - Limite configurável por unidade/período (ex: máx 2 aulas de Exatas pela manhã)
  - Permitir exceção com justificativa
  - Aviso visual em tempo real quando atingir limite
  - Checkbox "Autorizar acúmulo de área"
- **UX Problem Atual**: 
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
- **Flexibilidade**: N/A - apenas informativo
- **Limitação**: 
  - Cores são visuais mas **nenhuma mensagem textual** diz qual regra foi violada
  - Usuário vê "vermelho" mas não sabe exatamente por quê
  - Falta tooltip/legenda explicando cada cor

---

### 9. ⚠️ Sistema gera escala para coordenador aceitar/atualizar
- **Status**: NÃO IMPLEMENTADO (Apenas preenchimento manual)
- **O que existe**:
  - App permite preenchimento manual da grade pelo coordenador
  - Backend valida regras de negócio
- **O que NÃO existe**:
  - ❌ Algoritmo de geração automática (por agora é manual)
  - ❌ Workflow de aceitar/rejeitar (não há versão de "proposta" vs "final")
  - ❌ Histórico de alterações
  - ❌ Assinatura digital/aprovação formal
- **Flexibilidade**: N/A - não é prioritário por hora
- **Necessário para completar** (futuro):
  - Criar um serviço de "geração de sugestões" via algoritmo genético ou constraint satisfaction
  - Implementar status de grade (RASCUNHO, PROPOSTA, APROVADA, ARQUIVADA)
  - Criar view para comparação antes/depois

---

## 🔧 SISTEMA DE EXCEÇÕES (NOVO)

### Conceito Geral
Permitir que o coordenador **autorize exceções justificadas** para regras críticas, sem quebrar a integridade do sistema. Cada exceção é registrada e auditada.

### Campos a Adicionar ao Modelo `AlocacaoGrade`

```python
class AlocacaoGrade(models.Model):
    # ... campos existentes ...
    
    # Exceções autorizadas
    eh_excecao_limite_aulas = models.BooleanField(default=False, help_text="Autorizar exceção de limite de aulas/dia")
    motivo_excecao_limite = models.CharField(max_length=200, blank=True, null=True)
    
    eh_excecao_horario = models.BooleanField(default=False, help_text="Permitir duplicação de horário (raro)")
    motivo_excecao_horario = models.CharField(max_length=200, blank=True, null=True)
    
    eh_excecao_deslocamento = models.BooleanField(default=False, help_text="Autorizar deslocamento com tempo insuficiente")
    motivo_excecao_deslocamento = models.CharField(max_length=200, blank=True, null=True)
    
    eh_excecao_area_acumulo = models.BooleanField(default=False, help_text="Permitir acúmulo de aulas da mesma área")
    motivo_excecao_area_acumulo = models.CharField(max_length=200, blank=True, null=True)
    
    # Auditoria
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    autorizado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
```

### Fluxo de Exceção no Template

1. **Validação Inicial**: Sistema detecta violação de regra
2. **Bloqueio Visual**: Select fica avermelhado, com mensagem de erro
3. **Opção de Exceção**: Botão/checkbox "Autorizar exceção" aparece
4. **Modal de Justificativa**: Coordenador insere motivo (ex: "Professor afastado, precisa compensar")
5. **Salvamento com Flag**: Alocação é salva com `eh_excecao_*=True` e motivo registrado
6. **Auditoria**: Log registra quem autorizou e quando

### Exemplo de Uso

```javascript
// No template, ao validar limite de aulas:
if (aulas_por_prof > professor.limite_aulas) {
    select.classList.add('conflito-vermelho');
    select.title = "Limite de aulas atingido. Marque a checkbox abaixo para autorizar exceção.";
    
    // Exibe checkbox de exceção
    const checkboxExcecao = document.createElement('input');
    checkboxExcecao.type = 'checkbox';
    checkboxExcecao.name = `excecao_limite_${campo_name}`;
    checkboxExcecao.addEventListener('change', function() {
        if (this.checked) {
            const motivo = prompt("Motivo da exceção?", "");
            if (motivo) {
                select.classList.remove('conflito-vermelho');
                select.classList.add('conflito-amarelo'); // Aviso, mas permitido
            } else {
                this.checked = false;
            }
        }
    });
}
```

---

## 📊 RESUMO ATUAL (Atualizado)

| Regra | Status | Flexibilidade | Prioridade |
|-------|--------|---------------|-----------|
| Parentesco (turno/unidade) | ✅ Sim | ⚠️ Apenas aviso | Média |
| Sem 2 unidades simultâneas | ✅ Sim | ✅ Com exceção | Alta |
| Imprimir grade | ✅ Sim | N/A | Média |
| Mostrar horários | ✅ Sim | N/A | Baixa |
| Distância/transporte | ✅ Sim (JS simples) | ✅ Com exceção | Alta |
| Limite aulas/dia | ⚠️ Parcial | ✅ **URGENTE** Com exceção | Alta |
| Sem acúmulo mesma área | ⚠️ Aviso visual | ✅ **URGENTE** Com exceção | Média |
| Avisar critério | ⚠️ Cores/Visual | N/A (só info) | Média |
| Geração automática | ❌ Não | N/A | Baixa |

---

## 🎯 PRÓXIMAS PRIORIDADES (Recomendadas)

### URGENTE (Implementar AGORA)
1. **Sistema de exceções**: Adicionar campos ao modelo + lógica de autorização
2. **Bloqueio em tempo real**: Validar limite de aulas e acúmulo de áreas NO TEMPLATE (antes de salvar)
3. **Legenda de cores**: Adicionar tooltip/legenda explicando cada critério de validação
4. **Modal de justificativa**: Interface para autorizar exceções com motivo registrado

### MÉDIO PRAZO
5. **Auditoria completa**: Log de todas as exceções autorizadas
6. **Relatório de exceções**: Dashboard mostrando padrões (qual regra é mais quebrada, etc)
7. **Configuração de limites**: Admin customizado para ajustar limites por período/unidade

---

## 📁 Arquivos a Criar/Modificar

### Modificar (URGENTE)
- `grade/models.py` - Adicionar campos de exceção em `AlocacaoGrade`
- `grade/services.py` - Lógica que permite exceções após autorização
- `grade/views.py` - Processar flags de exceção do formulário
- `grade/templates/grade/grade_tabela.html` - Adicionar checkboxes de exceção + modal
- `grade/migrations/` - Criar migration para novos campos

### Criar (MÉDIO PRAZO)
- `grade/admin_customizado.py` - Interface para revisar exceções
- `grade/relatorios.py` - Análise de padrões de exceção

---

## 📝 Notas Importantes

- **Exceções não removem a regra**: Apenas permitem desvios justificados
- **Auditoria obrigatória**: Todo desvio deve ser registrado para futuras análises
- **Validação em 2 níveis**: 
  - Backend: rejeita exceções sem autorização
  - Frontend: avisa e oferece opção de autorizar
- **Flexibilidade controlada**: Coordenador tem poder, mas cada ação é rastreada

---

**Última atualização**: 2024
**Projeto**: Grade de Aulas Dinâmica CCM
**Status**: Pronto para implementação de exceções
