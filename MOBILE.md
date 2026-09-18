# Minha Grade: primeira versão mobile

Endereço local: http://127.0.0.1:8000/mobile/

## Preparar o ambiente

```powershell
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Use `createsuperuser` somente se ainda não tiver uma conta administrativa.

## Dar acesso a um professor

1. Entre em `/admin/` com sua conta administrativa.
2. Em **Usuários**, crie uma conta individual com usuário e senha.
3. Para uma conta de consulta, mantenha **Membro da equipe** e **Superusuário** desmarcados.
4. Em **Professores**, edite o professor existente e selecione essa conta no campo **Usuário**.
5. Entre em `/mobile/` com a conta do professor.

Cada conta vê somente suas próprias alocações. A associação é feita no banco, não pelo nome ou e-mail. A conta sem vínculo recebe uma orientação, sem acesso a horários de terceiros. Não criamos senhas padrão.

A tela de montagem em `/` agora exige uma conta administrativa (membro da equipe). A senha compartilhada antiga foi retirada desse fluxo. A API de gestão também exige uma conta administrativa. Cadastros existentes continuam preservados.

## O que testar

- Entrar e sair com uma conta de professor.
- Conferir semana atual, semanas anteriores e próximas, inclusive sem aulas.
- Cadastrar uma alocação pelo painel ou pela montagem e conferir na semana correspondente no mobile.
- Baixar PDF e imprimir; conferir texto longo, acentos e quebra de página.
- Entrar com outro professor e confirmar que as grades não se misturam.
- Abrir a tela em um Android real e conferir instalação, PDF e impressão.

O banco pode estar sem alocações: nesse caso a tela vazia é esperada. Não inserimos aulas fictícias no banco real.

## Instalação no celular

Para distribuição, hospede a aplicação com HTTPS e configure os hosts, os arquivos estáticos, o servidor de produção e os segredos. O servidor `runserver` é destinado ao desenvolvimento. A publicação ainda precisa ser preparada.

`127.0.0.1` no celular aponta para o próprio celular, não para o computador. Um endereço HTTP da rede local pode servir para testes de layout, com configuração de host e rede, mas não substitui HTTPS para a instalação da PWA.

No Android/Chrome, abra o endereço HTTPS e use **Instalar aplicativo** ou **Adicionar à tela inicial**. Quando o navegador oferecer instalação programática, a própria tela também exibirá um botão. No iPhone, use **Compartilhar → Adicionar à Tela de Início**.

A grade exige conexão. O aplicativo não guarda horários privados em cache. O PDF baixado é uma cópia e não se atualiza quando a coordenação muda os horários.

## Aprender pelo código

1. `grade/urls.py`: conecta os endereços às funções.
2. `grade/models.py`: o campo `Professor.usuario` vincula a conta ao professor.
3. `grade/mobile.py`: identifica o professor, consulta sete dias e produz HTML ou PDF.
4. `grade/templates/grade/mobile/`: estrutura das telas com os dados do Django.
5. `grade/static/grade/mobile/mobile.css`: aparência, adaptação ao celular e impressão.
6. `grade/static/grade/mobile/mobile.js`: instalação e botão de impressão.
7. `grade/tests.py`: testes de acesso, isolamento e exportação.

Para executar os testes (usam um banco separado):

```powershell
docker compose exec web python manage.py test grade
```

O modelo atual não relaciona uma disciplina específica a cada alocação. A consulta mostra horário e unidade; não tenta deduzir a disciplina pelas habilitações do professor.
