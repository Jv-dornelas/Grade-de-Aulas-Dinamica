# Portal mobile em túnel temporário

Autorizado pelo responsável em 11/11/2026, incluindo uso de Cloudflare para tráfego do portal. Não é hospedagem permanente. Computador, Docker e conexão precisam permanecer ativos. O endereço aleatório muda ao recriar o túnel; compartilhe-o somente com os participantes do teste.

```powershell
docker compose -p grade-mobile -f docker-compose.mobile.yml up -d --build
docker compose -p grade-mobile -f docker-compose.mobile.yml logs tunnel
```

Copie o endereço HTTPS `trycloudflare.com` dos logs. No navegador, acrescente `/mobile/`. No APK, configure apenas a origem HTTPS, sem `/mobile/`. Não é necessário estar na mesma rede Wi-Fi.

Para encerrar o acesso público:

```powershell
docker compose -p grade-mobile -f docker-compose.mobile.yml down
```

Esse comando encerra apenas a demonstração mobile; o Compose principal permanece local. Não remove o banco.

O serviço isolado usa o mesmo banco definido no `.env`, sem migração nem cópia automática. Somente as rotas mobile e quatro arquivos estáticos explicitamente permitidos estão disponíveis. Sem Admin, API ou gestão, DEBUG desativado, cookies públicos separados dos locais e enviados somente por HTTPS. Sessões de professores continuam sendo autenticadas pelo Django. Não publicar senhas de teste ou contas compartilhadas; o túnel é um acesso público com login, não uma rede privada.

Não há envio automático de e-mails por abrir o túnel. O link dos avisos continua sendo definido por `GRADE_URL_PUBLICA`; como o túnel é temporário, ele não é alterado automaticamente. O servidor de demonstração utiliza runserver e não deve ser tratado como produção permanente. Não há bloqueio de tentativas de login específico ou monitoramento permanente nesta configuração; desligue o túnel após o teste.

Referência: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
