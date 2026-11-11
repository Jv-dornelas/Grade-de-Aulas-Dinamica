# Proposta de hospedagem gratuita do MVP

Verificação em 11/11/2026. Esta proposta não é um deploy: o sistema permanece local. Publicar código no GitHub não publica bancos ou credenciais. Os planos podem mudar.

## Arquitetura proposta para avaliação

- Django web e portal mobile no mesmo serviço HTTPS do Render Free; o portal `/mobile/` não exige um segundo servidor.
- PostgreSQL externo no Neon Free para persistência. Não usar SQLite no filesystem efêmero do Render nem o banco gratuito Render Postgres com expiração de 30 dias.
- E-mail por API HTTPS de um provedor com plano gratuito, a selecionar e validar. O SMTP Gmail atual funciona localmente, mas as portas SMTP são bloqueadas no Render Free. Avaliar verificação do remetente e entregabilidade antes de escolher o provedor; não prometer envio com a conta Gmail via SMTP nesse plano.
- Usar o subdomínio HTTPS gratuito do serviço, sem comprar domínio nesta etapa.

O Render Free suspende o processo depois de 15 minutos ocioso, tem inicialização a frio e recursos limitados (512 MB de memória). Precisamos medir o gerador OR-Tools nesse ambiente. O Neon Free oferece cotas e suspensão por inatividade; não equivale a capacidade ilimitada. Não cadastrar cartão nem habilitar upgrades automáticos para este experimento.

## Trabalho necessário antes de publicar o sistema

1. Configurar ambiente de produção com `DEBUG=False`, segredo próprio, hosts/CSRF explícitos, cookies seguros, HTTPS e execução WSGI adequada. Hoje o Docker local utiliza runserver; não deve ser exposto diretamente.
2. Adicionar configuração PostgreSQL e validar transações/concorrência da confirmação, replicação e aprovação nesse banco. Os testes atuais utilizam SQLite: não declarar compatibilidade concorrente validada para PostgreSQL sem executá-los e revisar os bloqueios.
3. Configurar coleta/serviço de arquivos estáticos e testar formulários, login, mobile e PDF sob HTTPS.
4. Implementar/testar o backend de e-mail HTTPS e adaptar os estados de envio, que atualmente reconhecem SMTP como entrega real.
5. Criar banco remoto separado, com backup/restauração testados. Não carregar automaticamente o banco local ou a fixture histórica. Se dados forem transferidos, revisar informações pessoais e destinatários para evitar avisos indevidos.
6. Criar conta administrativa remota com credencial própria e cadastrar os demais usuários pelo fluxo administrativo.
7. Validar tempo/memória do gerador com cenários reais, navegação por celular e link público nos avisos. Se houver uso do APK experimental, configurar seu endereço separadamente; hospedar o portal não recompila o aplicativo.

Não foi criada infraestrutura externa nesta etapa. Contas dos serviços e acesso aos painéis serão necessários para executar o deploy. O plano gratuito serve para demonstração e testes; não oferece as mesmas garantias de disponibilidade de hospedagem paga.

## Fontes oficiais

- Render Free e limites: https://render.com/docs/free
- Recursos de computação: https://render.com/docs/compute-plans
- Neon Free: https://neon.com/pricing
- PythonAnywhere Free, alternativa com outras restrições: https://help.pythonanywhere.com/pages/FreeAccountsFeatures/

PythonAnywhere não foi escolhido automaticamente: contas gratuitas novas têm restrições de saída para a internet e recursos limitados, que precisam ser avaliados para mapas, e-mail e o otimizador.
