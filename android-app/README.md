# Minha Grade para Android — demonstração acadêmica

## Estado atual — 18/09/2026

**Experimental: ainda não validado para apresentação.** No teste em aparelho físico, o usuário relatou que o APK continua com a tela em branco e não exibe a interface que funciona pelo navegador mobile. Os ajustes da versão 1.1 não resolveram esse comportamento no dispositivo.

A compilação, a assinatura, a análise estática e os testes unitários passaram, mas isso não comprova o funcionamento do WebView no aparelho. A causa da tela em branco ainda não foi determinada. A investigação foi adiada a pedido do usuário.

O estado foi preservado na branch `wip/android-tela-branca`. Não considerar o problema corrigido nem integrar novos ajustes ao código principal sem validar login, carregamento, PDF e impressão em um Android real. Até essa validação, a alternativa de demonstração é a versão web em `/mobile/`.

Próxima investigação: comparar o mesmo endereço no Chrome e no APK do aparelho, confirmar o servidor salvo no app e coletar os erros de rede e do WebView. Não há alteração adicional no código de execução nesta atualização de status.

Este projeto gera um **APK híbrido**: a interface e os dados vêm do Django, enquanto o Android oferece a janela do aplicativo, a configuração do servidor, o armazenamento de PDF, o compartilhamento e a impressão. É uma implementação WebView, sem Capacitor, Flutter ou React Native.

## Compilar

Requisito no computador: Docker Desktop em execução. Não é necessário instalar Android Studio ou Node.js. O primeiro build baixa o JDK, o Gradle e o SDK Android em um ambiente Docker separado e pode consumir alguns GB e vários minutos.

As ferramentas Android têm uma licença própria. Leia os [termos oficiais do SDK](https://developer.android.com/studio#terms-and-conditions). **Somente se concordar**, execute na raiz do repositório:

```powershell
.\android-app\compilar.ps1 -AceitarLicencaSdk
```

Se a política do Windows bloquear arquivos `.ps1`, execute apenas essa chamada com:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\android-app\compilar.ps1 -AceitarLicencaSdk
```

Isso não altera permanentemente a política de execução do Windows.

O script compila, testa a validação do endereço do servidor, executa o Android Lint e verifica a assinatura. Só depois copia o resultado para:

```text
dist/MinhaGrade-demo.apk
```

O APK é assinado para demonstração/debug, não é uma publicação na Play Store. Os volumes Docker `minha-grade-gradle-cache` e `minha-grade-android-keys` guardam dependências e a chave de assinatura de testes. Apagar a chave pode exigir desinstalar a versão anterior para instalar uma nova. APKs, chaves e arquivos de build não entram no Git.

## Instalar no celular

1. Copie `MinhaGrade-demo.apk` ao celular, por exemplo por USB.
2. Abra o arquivo no gerenciador de arquivos.
3. Se o Android solicitar, permita que esse gerenciador instale o aplicativo e confirme a instalação.
4. Abra **Minha Grade** pelo ícone.
5. Na primeira abertura, informe o endereço do computador: `http://192.168.15.37:8000` (sem `/mobile/`).
6. Entre com a conta de professor cadastrada no Django.

O script também copia o APK para a pasta de arquivos estáticos de desenvolvimento. Com o Django rodando, você pode baixar no próprio celular por `http://192.168.15.37:8000/static/grade/mobile/MinhaGrade-demo.apk` (ajuste o IP, se necessário). Esse arquivo gerado é ignorado pelo Git.

Compatibilidade mínima: Android 8.0 (API 26), com Android System WebView atualizado. A instalação, a renderização e os diálogos nativos ainda devem ser validados em um aparelho físico.

## Apresentar

- Ligue o Docker e execute `docker compose up -d` no projeto Django.
- Conecte computador e celular à mesma rede.
- Se o IP mudar, inclua o novo IP em `ALLOWED_HOSTS` no `.env`, recrie o serviço com `docker compose up -d --force-recreate web` e use **Opções → Trocar servidor** no aplicativo.
- Demonstre login, navegação semanal, **Baixar PDF**, **Salvar nos arquivos do celular**, **Compartilhar PDF** e **Imprimir**.
- O menu Android **Opções** também oferece PDF e impressão.
- Para testar sem impressora, use o destino de impressão **Salvar como PDF**, se disponível no aparelho.
- Antes da apresentação, cadastre aulas para o professor na semana que será demonstrada. O APK não cria dados fictícios.

O computador continua sendo o servidor e precisa permanecer ligado. A conexão HTTP é aceita pelo seletor somente para IPs privados (10.*, 172.16–31.* e 192.168.*), destinada à demonstração em rede de confiança. Servidores públicos exigem HTTPS. O APK não ignora certificados inválidos.

## Como funciona

- `MainActivity.java`: carrega `/mobile/` do servidor escolhido. Mantém os cookies de login no WebView; os downloads usam a mesma sessão, sem redirecionar cookies para outro servidor.
- `PdfProvider.java`: disponibiliza somente PDFs temporários para o aplicativo que o usuário escolher no compartilhamento, com permissão temporária de leitura.
- O seletor de arquivos do Android permite salvar o PDF sem pedir acesso amplo ao armazenamento.
- `mobile.js` reconhece a identificação `MinhaGradeAndroid/1.0`, esconde as dicas de instalação da PWA e encaminha a impressão ao Android.
- Nenhum `JavascriptInterface` com acesso genérico ao sistema é exposto às páginas.
- Trocar de servidor remove os cookies. PDFs salvos ou compartilhados são cópias e não se atualizam automaticamente.

## Validação antes da entrega

1. Compilação e Lint sem erros; assinatura do APK válida.
2. Instalação em Android real e primeiro acesso.
3. Login correto/incorreto e logout.
4. Semana com aulas e semana vazia.
5. Salvar e compartilhar PDF verificando o professor e as datas.
6. Impressão em A4.
7. Servidor desligado, IP inválido e troca de servidor.
8. Voltar do Android, girar a tela e reabrir o app.

O código pode ser aberto no Android Studio no futuro. A camada WebView aqui criada é específica para Android; a interface Django permanece reaproveitável para um futuro contêiner iOS.
