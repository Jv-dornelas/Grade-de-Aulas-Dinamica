/* A grade privada nunca é armazenada pelo service worker. */
const isAndroidApp = navigator.userAgent.includes('MinhaGradeAndroid/');
if (!isAndroidApp && 'serviceWorker' in navigator && window.isSecureContext) {
  navigator.serviceWorker.register('/mobile/sw.js', {scope: '/mobile/'}).catch(() => {});
}
document.getElementById('imprimir')?.addEventListener('click', () => {
  if (isAndroidApp) window.location.href = 'minhagrade://print';
  else window.print();
});
if (isAndroidApp) {
  // O APK já tem seu cabeçalho; mantém somente a ação de sair da sessão web.
  const webHeader = document.querySelector('.topbar');
  if (webHeader) {
    if (webHeader.querySelector('form')) {
      const brand = webHeader.querySelector('.brand');
      if (brand) brand.hidden = true;
      webHeader.style.justifyContent = 'flex-end';
      webHeader.style.paddingTop = '0';
      webHeader.style.paddingBottom = '8px';
    } else webHeader.hidden = true;
  }
  const installHint = document.querySelector('.install');
  if (installHint) installHint.hidden = true;
}
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
