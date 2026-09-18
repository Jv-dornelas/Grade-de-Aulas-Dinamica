// Somente uma mensagem offline. Não guardar páginas autenticadas ou PDFs em cache.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  if (event.request.mode !== 'navigate' || event.request.method !== 'GET') return;
  event.respondWith(fetch(event.request).catch(() => new Response(
    '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sem conexão · Minha Grade</title><body style="font-family:system-ui;padding:32px;background:#f4f7f5;color:#164e47"><h1>Você está sem conexão</h1><p>Conecte-se à internet para consultar a grade atualizada. Se você já baixou um PDF, ele continua disponível nos arquivos do celular.</p><a href="/mobile/">Tentar novamente</a></body></html>',
    {status: 503, headers: {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}}
  )));
});
