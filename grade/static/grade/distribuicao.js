function alterarData(data) {
    if (!data) return;
    const url = new URL(window.location.href);
    url.searchParams.set('data', data);
    ['semana', 'editar', 'proposta', 'nova', 'horario', 'data_aula'].forEach(c => url.searchParams.delete(c));
    url.hash = '';
    window.location.href = url.toString();
}

(() => {
    const editor = document.getElementById('form-aula');
    const gerar = document.getElementById('gerar-integrado');
    const botao = document.getElementById('gerar-grade-btn');
    let alterado = false;
    editor?.querySelector('[name="demanda"]')?.addEventListener('change', event => {
        const unidade = event.target.selectedOptions[0]?.dataset.unidade;
        if (unidade) editor.querySelector('[name="unidade"]').value = unidade;
    });
    editor?.addEventListener('change', () => { alterado = true; });
    editor?.addEventListener('submit', () => { alterado = false; });
    window.addEventListener('beforeunload', event => {
        if (alterado) { event.preventDefault(); event.returnValue = ''; }
    });
    gerar.addEventListener('submit', event => {
        const aviso = document.getElementById('geracao-andamento');
        if (alterado) {
            event.preventDefault();
            aviso.textContent = 'Salve ou cancele o ajuste aberto antes de gerar novamente.';
            aviso.hidden = false;
            editor.querySelector('button[type="submit"]').focus();
            return;
        }
        botao.disabled = true;
        botao.textContent = 'Gerando…';
        aviso.hidden = false;
    });
})();
