# SECRET_KEY: como gerar e configurar

A `SECRET_KEY` é a chave que a API usa para assinar os tokens de login (JWT). Quem tem a chave consegue criar um token válido para qualquer usuário, inclusive admin. Por isso cada pessoa precisa ter a sua, e ela nunca vai para o Git.

## Por que isso mudou

Até a `release/1.0.0.0`, a chave usada na prática era a do `.env.example`, que é público no GitHub. Qualquer pessoa conseguia gerar um token de admin. A partir da `release/1.0.0.2`, a chave é **obrigatória** e a API **não sobe** se ela:

- estiver vazia ou ausente;
- tiver menos de 32 caracteres;
- for igual ao valor de exemplo do `.env.example` ou ao antigo valor padrão do código.

Nesses casos o startup falha com uma mensagem explicando como gerar a chave.

## Passo a passo

### 1. Gerar a chave

No terminal, dentro da pasta do projeto:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

O comando imprime uma sequência aleatória de 64 caracteres.

### 2. Colocar no `.env`

Se você ainda não tem o arquivo `.env`, crie a partir do exemplo:

```powershell
copy .env.example .env
```

Abra o `.env` na raiz do projeto e troque a linha da chave pelo valor gerado:

```env
SECRET_KEY=cole-aqui-o-valor-gerado
```

### 3. Reiniciar a API

```powershell
python -m uvicorn app.main:app --reload
```

## Atalho: gerar e gravar de uma vez

No PowerShell, na pasta do projeto e com o `.venv` ativado:

```powershell
$k = python -c "import secrets;print(secrets.token_urlsafe(48))"; (Get-Content .env) -replace '^SECRET_KEY=.*', "SECRET_KEY=$k" | Set-Content .env -Encoding utf8
```

## Cuidados

- **Não commite o `.env`.** Ele já está no `.gitignore`.
- **Não reaproveite a chave de outra pessoa** nem mande a sua por chat ou e-mail.
- **Trocar a chave desloga todo mundo:** os tokens antigos deixam de valer, e é só fazer login de novo.
- **Testes:** a suíte `pytest` define uma chave própria em `tests/conftest.py` e não depende do seu `.env`.

## Erros comuns

| Mensagem no startup | O que fazer |
|---|---|
| `SECRET_KEY ainda é o valor de exemplo` | Gere uma chave nova (passo 1) e coloque no `.env` |
| `SECRET_KEY deve ter pelo menos 32 caracteres` | A chave está curta; gere uma nova com o comando acima |
| `Field required` em `secret_key` | Falta a linha `SECRET_KEY=` no `.env`, ou o arquivo `.env` não existe na raiz do projeto |
