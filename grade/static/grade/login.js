const botaoSenha = document.getElementById('mostrar-senha');
const campoSenha = document.getElementById('id_password');
if (botaoSenha && campoSenha) {
    botaoSenha.hidden = false;
    botaoSenha.addEventListener('click', () => {
        const mostrar = campoSenha.type === 'password';
        campoSenha.type = mostrar ? 'text' : 'password';
        botaoSenha.textContent = mostrar ? 'Ocultar' : 'Mostrar';
        botaoSenha.setAttribute('aria-pressed', String(mostrar));
    });
}
