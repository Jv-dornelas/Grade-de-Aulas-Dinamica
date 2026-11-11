# Avisos de grade por e-mail

Uma nova aprovação semanal cria avisos individuais para professores cuja grade mudou desde a aprovação anterior. Prévia, descarte e salvar sem aprovar não enviam. Reaprovar a mesma versão não duplica avisos. Professores retirados da semana também recebem atualização. A mensagem traz somente as aulas daquele professor e o acesso mobile; o destinatário é o e-mail da ficha do professor, sem cópias coletivas.

Os avisos são gravados na mesma transação da aprovação e processados após commit. Uma falha de envio não desfaz a grade. Na revisão da aprovação, abra **Avisos por e-mail desta aprovação** para conferir `enviado`, `simulado`, `erro`, `sem_email`, `sem_alteracao` ou `desatualizado`. `enviado` significa aceitação pelo servidor SMTP, não confirmação de leitura ou entrega na caixa de entrada.

## Ambiente local

O padrão é o backend de arquivos: mensagens ficam em `tmp/emails/`, marcadas como `simulado`. Não são enviadas para destinatários reais. Esses arquivos contêm informações pessoais e devem permanecer locais. Aprovações antigas não geram disparos retroativos.

## Configurar envio real

Configure no ambiente do processo Django, sem versionar credenciais:

```text
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<servidor SMTP>
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=<usuário>
EMAIL_HOST_PASSWORD=<senha de aplicativo ou credencial SMTP>
DEFAULT_FROM_EMAIL=<remetente autorizado>
GRADE_URL_PUBLICA=<endereço acessível pelos professores>
```

O Compose atual já encaminha o `.env` por `env_file`. Recrie o serviço depois de configurar as variáveis (um simples restart não recarrega o ambiente). Não use `localhost` no link para acesso a partir de outro aparelho. Não habilitado nem testado SMTP real nesta implementação.

Para tentar novamente avisos pendentes/com erro, execute:

```powershell
docker compose exec web python manage.py enviar_avisos_grade
```

Só são enviadas versões cuja aprovação ainda está vigente. Depois de corrigir cadastros que invalidem a assinatura, revise e aprove a nova versão. Avisos já enviados ou simulados não são reenviados pelo comando. A troca do modo simulado para SMTP não dispara mensagens antigas automaticamente.

## Limitações operacionais

Envio síncrono após commit, com timeout SMTP de 10 segundos por mensagem; para muitos professores, migrar o processamento para um worker. Há reivindicação atômica contra dois processos concorrentes. Se o processo cair durante o envio, um aviso pode ficar em `enviando` e exige conferência técnica antes de liberar nova tentativa: SMTP não garante entrega exatamente uma vez quando há interrupção após aceitação. Não há rastreamento de leitura, tratamento de devoluções ou reenvio automático agendado.
