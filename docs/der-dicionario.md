# Dicionário do DER

As cinco vistas de `diagrama-entidade-relacionamento.puml` formam um único modelo. Os campos de cada entidade são apresentados integralmente em pelo menos uma vista. Entidades em cinza são referências à mesma tabela. Tipos são lógicos, não tipos físicos do SQLite.

## Entidades e campos

`*` significa NOT NULL; sem `*`, o campo aceita NULL. `blank=True` permite omissão na validação de formulário e não implica NULL no banco.

### Usuário `auth_user`

```text
  * id : INTEGER <<PK>>
  --
  * username : VARCHAR(150) <<UK>>
  * password : VARCHAR(128)
  * first_name : VARCHAR(150)
  * last_name : VARCHAR(150)
  * email : VARCHAR(254)
  * is_active : BOOLEAN
  * is_staff : BOOLEAN
  * is_superuser : BOOLEAN
  last_login : DATETIME
  * date_joined : DATETIME
```

### Unidade `grade_unidade`

```text
  * id : INTEGER <<PK>>
  --
  * nome : VARCHAR(50)
  * responsavel : VARCHAR(100)
  endereco : VARCHAR(200)
  cidade : VARCHAR(100)
  cep : VARCHAR(15)
```

### Disciplina `grade_disciplina`

```text
  * id : INTEGER <<PK>>
  --
  * nome : VARCHAR(100)
  * area : VARCHAR(20)
```

### Professor `grade_professor`

```text
  * id : INTEGER <<PK>>
  --
  usuario_id : INTEGER <<FK, UK>>
  unidade_oficial_id : INTEGER <<FK>>
  parente_vinculado_id : INTEGER <<FK>>
  * nome : VARCHAR(100)
  telefone : VARCHAR(20)
  email : VARCHAR(254)
  * meio_de_transporte : VARCHAR(20) = PARTICULAR
  * limite_aulas : INTEGER >= 0 = 5
  observacao : TEXT
```

### ProfessorDisciplina `grade_professor_disciplinas`

```text
  * id : INTEGER <<PK>>
  --
  * professor_id : INTEGER <<FK>>
  * disciplina_id : INTEGER <<FK>>
```

### ProfessorUnidadePermitida `grade_professor_unidades_permitidas`

```text
  * id : INTEGER <<PK>>
  --
  * professor_id : INTEGER <<FK>>
  * unidade_id : INTEGER <<FK>>
```

### MatrizDistancia `grade_matrizdistancia`

```text
  * id : INTEGER <<PK>>
  --
  * origem_id : INTEGER <<FK>>
  * destino_id : INTEGER <<FK>>
  * tempo_minutos : INTEGER >= 0
```

### HorarioAula `grade_horarioaula`

```text
  * id : INTEGER <<PK>>
  --
  * nome : VARCHAR(20)
  * hora_inicio : TIME
  * hora_fim : TIME
```

### Turma `grade_turma`

```text
  * id : INTEGER <<PK>>
  --
  * unidade_id : INTEGER <<FK>>
  * nome : VARCHAR(80)
  * dias_semana : JSON = [0,1,2,3,4]
```

### TurmaHorario `grade_turma_horarios`

```text
  * id : INTEGER <<PK>>
  --
  * turma_id : INTEGER <<FK>>
  * horarioaula_id : INTEGER <<FK>>
```

### DemandaAula `grade_demandaaula`

```text
  * id : INTEGER <<PK>>
  --
  * turma_id : INTEGER <<FK>>
  * disciplina_id : INTEGER <<FK>>
  professor_id : INTEGER <<FK>>
  * quantidade_semana : INTEGER = 1
  * ativa : BOOLEAN = true
```

### Disponibilidade `grade_disponibilidade`

```text
  * id : INTEGER <<PK>>
  --
  * professor_id : INTEGER <<FK>>
  * data : DATE
  * disponivel_manha : BOOLEAN = false
  * disponivel_tarde : BOOLEAN = false
```

### DisponibilidadeHorario `grade_disponibilidadehorario`

```text
  * id : INTEGER <<PK>>
  --
  * professor_id : INTEGER <<FK>>
  * horario_id : INTEGER <<FK>>
  * data : DATE
  * disponivel : BOOLEAN = true
```

### AlocacaoGrade `grade_alocacaograde`

```text
  * id : INTEGER <<PK>>
  --
  * horario_id : INTEGER <<FK>>
  * unidade_id : INTEGER <<FK>>
  * professor_id : INTEGER <<FK>>
  turma_id : INTEGER <<FK>>
  disciplina_id : INTEGER <<FK>>
  demanda_id : INTEGER <<FK>>
  autorizado_por_id : INTEGER <<FK>>
  * data : DATE
  * eh_excecao_limite_aulas : BOOLEAN = false
  motivo_excecao_limite : VARCHAR(200)
  * eh_excecao_horario : BOOLEAN = false
  motivo_excecao_horario : VARCHAR(200)
  * eh_excecao_deslocamento : BOOLEAN = false
  motivo_excecao_deslocamento : VARCHAR(200)
  * eh_excecao_area_acumulo : BOOLEAN = false
  motivo_excecao_area_acumulo : VARCHAR(200)
  criado_em : DATETIME
  atualizado_em : DATETIME
```

## Exclusão via ORM Django

As regras abaixo descrevem `on_delete`, não cardinalidades. CASCADE exclui os registros dependentes; PROTECT impede excluir o registro referenciado enquanto houver dependentes; SET_NULL limpa a referência.

| Campo ou associação | Regra |
|---|---|
| `Professor.usuario` | SET_NULL |
| `Professor.disciplinas` (duas FKs da tabela associativa) | CASCADE nos registros associativos |
| `Professor.unidade_oficial` | SET_NULL |
| `Professor.unidades_permitidas` (duas FKs da tabela associativa) | CASCADE nos registros associativos |
| `Professor.parente_vinculado` | SET_NULL |
| `MatrizDistancia.origem` | CASCADE |
| `MatrizDistancia.destino` | CASCADE |
| `Turma.unidade` | PROTECT |
| `Turma.horarios` (duas FKs da tabela associativa) | CASCADE nos registros associativos |
| `DemandaAula.turma` | PROTECT |
| `DemandaAula.disciplina` | PROTECT |
| `DemandaAula.professor` | PROTECT |
| `DisponibilidadeHorario.professor` | CASCADE |
| `DisponibilidadeHorario.horario` | CASCADE |
| `Disponibilidade.professor` | CASCADE |
| `AlocacaoGrade.horario` | CASCADE |
| `AlocacaoGrade.unidade` | CASCADE |
| `AlocacaoGrade.professor` | CASCADE |
| `AlocacaoGrade.turma` | PROTECT |
| `AlocacaoGrade.disciplina` | PROTECT |
| `AlocacaoGrade.demanda` | PROTECT |
| `AlocacaoGrade.autorizado_por` | SET_NULL |

## Restrições e regras

**ProfessorDisciplina**

UNIQUE(professor_id, disciplina_id) Associação N:N criada pelo Django.

**ProfessorUnidade**

UNIQUE(professor_id, unidade_id) Associação N:N criada pelo Django.

**TurmaHorario**

UNIQUE(turma_id, horarioaula_id) Associação N:N criada pelo Django.

**Turma**

UNIQUE(unidade_id, nome) dias_semana: lista não vazia de dias únicos. 0 = segunda-feira; 6 = domingo. Validação dos dias na aplicação.

**DemandaAula**

UNIQUE(turma_id, disciplina_id) Validações na aplicação: quantidade_semana entre 1 e 100; professor fixado deve lecionar a disciplina. Professor nulo permite escolha pelo gerador.

**DisponibilidadeHorario**

UNIQUE(professor_id, data, horario_id) Tem prioridade sobre a disponibilidade por turno.

**HorarioAula**

Validações em clean(), sem UNIQUE no banco: hora_fim > hora_inicio; não repetir o par (hora_inicio, hora_fim).

**Professor**

Transporte: PARTICULAR, PUBLICO ou OUTRO. limite_aulas representa o limite diário. Não pode vincular a si mesmo como parente. A FK de parentesco é direcional no banco; a preferência é considerada nos dois sentidos.

**Disciplina**

Área: EXATAS, HUMANAS ou BIOLOGICAS.

**AlocacaoGrade**

Turma, disciplina e demanda são opcionais no modelo. Conflitos e exceções são validados pela aplicação. Não há UNIQUE de professor/data/horário no modelo.

Disponibilidade não tem UNIQUE(professor, data). MatrizDistancia não tem UNIQUE(origem, destino).

As tabelas internas de grupos, permissões, sessões e logs do Django estão fora do escopo.
