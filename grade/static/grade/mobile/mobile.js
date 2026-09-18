/* A grade privada nunca é armazenada pelo service worker. */
if ('serviceWorker' in navigator && window.isSecureContext) {
  navigator.serviceWorker.register('/mobile/sw.js', {scope: '/mobile/'}).catch(() => {});
}
document.getElementById('imprimir')?.addEventListener('click', () => window.print());
let installPrompt;
const installButton = document.getElementById('instalar');
window.addEventListener('beforeinstallprompt', event => {
  if (!installButton) return;
  event.preventDefault();
  installPrompt = event;
  installButton.hidden = false;
});
installButton?.addEventListener('click', async () => {
  if (!installPrompt) return;
  await installPrompt.prompt();
  installPrompt = null;
  installButton.hidden = true;
});
window.addEventListener('appinstalled', () => { if (installButton) installButton.hidden = true; });
window.addEventListener('pageshow', event => { if (event.persisted) window.location.reload(); });
