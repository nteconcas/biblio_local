# BiblioWeb

BiblioWeb e uma aplicacao web em Flask para gestao de bibliotecas, com catalogo, usuarios, emprestimos, relatorios e geracao de etiquetas.

## Stack

- Python 3.11
- Flask
- PostgreSQL
- Gunicorn
- Docker / Docker Compose

## O que foi preparado para deploy

- Aplicacao configuravel por variaveis de ambiente
- Compatibilidade com proxy reverso do Dokploy
- Suporte a HTTP ou HTTPS sem forcar TLS indevidamente
- Endpoint de saude em `/health`
- Imagem Docker pronta para producao com Gunicorn
- `docker-compose.yml` pronto para stack com app + PostgreSQL

## Variaveis de ambiente

Use o arquivo `.env.example` como base.

### Obrigatorias

- `SECRET_KEY`: chave secreta do Flask
- `POSTGRES_USER`: usuario do PostgreSQL
- `POSTGRES_PASSWORD`: senha do PostgreSQL
- `POSTGRES_DB`: nome do banco

### Opcionais

- `PREFERRED_URL_SCHEME`: `http` ou `https`
- `ENABLE_HTTPS_HEADERS`: `true` para habilitar HSTS e upgrade-insecure-requests
- `COOKIE_SECURE`: `true` quando publicar somente com HTTPS
- `TRUST_PROXY_COUNT`: quantidade de proxies confiaveis na frente da app
- `GUNICORN_WORKERS`: numero de workers do Gunicorn
- `GUNICORN_THREADS`: numero de threads por worker
- `GUNICORN_TIMEOUT`: timeout em segundos

## Deploy no Dokploy

### Opcao 1: Stack com `docker-compose.yml`

1. Crie um novo projeto do tipo compose no Dokploy.
2. Aponte para este repositorio.
3. Configure as variaveis de ambiente com base em `.env.example`.
4. Publique o servico `web`.
5. Configure o dominio interno ou externo no proxy do Dokploy.

Configuracao recomendada:

- Com acesso apenas por IP ou dominio interno sem TLS:
  - `PREFERRED_URL_SCHEME=http`
  - `ENABLE_HTTPS_HEADERS=false`
  - `COOKIE_SECURE=false`
- Com dominio e HTTPS terminado pelo Dokploy:
  - `PREFERRED_URL_SCHEME=https`
  - `ENABLE_HTTPS_HEADERS=true`
  - `COOKIE_SECURE=true`

### Opcao 2: App + banco separados

Se preferir criar o PostgreSQL fora do compose:

1. Crie um servico PostgreSQL no Dokploy.
2. Obtenha a connection string.
3. Configure `DATABASE_URL` diretamente no servico web.
4. Mantenha `SECRET_KEY` configurada manualmente.

Exemplo:

```env
DATABASE_URL=postgresql://usuario:senha@host:5432/biblio_db
SECRET_KEY=troque_esta_chave
PREFERRED_URL_SCHEME=https
ENABLE_HTTPS_HEADERS=true
COOKIE_SECURE=true
TRUST_PROXY_COUNT=1
```

## Execucao local com Docker Compose

1. Copie `.env.example` para `.env`.
2. Ajuste os valores sensiveis.
3. Suba os containers:

```bash
docker compose up --build
```

4. Em deploy no Dokploy, direcione o proxy para a porta interna `5000` do servico `web`.
5. Se quiser testar fora do Dokploy, adicione temporariamente um mapeamento de porta no servico `web`, por exemplo `5000:5000`.

## Credenciais iniciais

- Usuario: `admin`
- Senha: `admin123`

Altere essa senha apos o primeiro acesso.

## Observacoes operacionais

- A aplicacao executa `db.create_all()` na inicializacao.
- Existe uma migracao simples no startup para manter compatibilidade do schema atual.
- O banco e persistido no volume `postgres_data`.
- O endpoint `/health` pode ser usado pelo Dokploy para verificacao de integridade.
