# Documentação do projeto

## Para usar e testar

- [Início e comandos locais](../README.md)
- [Mobile e acesso dos professores](guias/MOBILE.md)
- [Mapa de campos e critérios da automação](guias/CADASTROS_AUTOMACAO.md)
- [Retomada do desenvolvimento](RETOMADA_LOCAL.md)
- [Regras e histórico da automação](../AUTOMACAO.md)
- [Cenários reproduzíveis e roteiro do MVP](testes/CENARIOS.md)

## Para desenvolver

- [Estrutura e responsabilidades](arquitetura/ESTRUTURA.md)
- [Análise original das regras](arquitetura/ANALISE_REGRAS.md)
- [Modelo de dados e diagramas](der-leia-me.md)
- [Dicionário de dados](der-dicionario.md)

Os diagramas são um registro da etapa em que foram produzidos. Confira `grade/models.py` e as migrações para o modelo efetivo atual.

## Processos

- [Checklist histórico do GitHub](processos/CHECKLIST_GITHUB.md)

O checklist não autoriza publicar esta cópia. A orientação atual é manter todo o trabalho local, sem push, PR ou deploy.

## Arquivos locais

Backups estão em `backups/`. Relatórios, HTMLs e PDFs de validação ficam em `output/`; arquivos temporários em `tmp/`; compilações em `dist/`. Esses diretórios não são código-fonte da aplicação e não são enviados ao contexto de construção Docker.
