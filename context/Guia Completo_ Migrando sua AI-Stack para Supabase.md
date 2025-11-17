<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Guia Completo: Migrando sua AI-Stack para Supabase Local

Este guia detalha o processo de migração da sua pilha atual para usar uma instância local do Supabase, substituindo o serviço PostgreSQL standalone pelo PostgreSQL gerenciado pelo Supabase, mantendo todos os serviços existentes funcionais.

## Visão Geral da Migração

Sua stack atual usa um PostgreSQL standalone (`ai-postgres`) que hospeda dois bancos de dados (`ai_rag` e `plane_db`) e atende múltiplos serviços. A migração para Supabase local adiciona recursos adicionais como autenticação integrada, API REST automática, Realtime e uma interface administrativa (Studio), enquanto mantém compatibilidade total com suas configurações atuais.[^1][^2][^3]

## Parte 1: Preparação do Ambiente Supabase

### 1.1 Instalação do Supabase CLI

O Supabase CLI gerencia a instância local via Docker:[^2][^3]

```bash
# Instalação via npm (recomendado para seu ambiente)
npm install -g supabase

# Verificar instalação
supabase --version
```


### 1.2 Inicialização do Projeto Supabase

Dentro do diretório `ai-stack`:

```bash
# Criar estrutura de configuração do Supabase
supabase init

# Isso cria o diretório supabase/ com:
# - config.toml (configuração principal)
# - migrations/ (para versionamento de schema)
# - seed.sql (dados iniciais)
```


### 1.3 Configuração do config.toml

Edite `supabase/config.toml` para ajustar às suas necessidades:[^4][^5]

```toml
# Configuração da porta do PostgreSQL (para evitar conflito com porta 5432 atual)
[db]
port = 54322
major_version = 16

# Configurar usuário e senha
[db.pooler]
enabled = true
port = 54329
pool_mode = "transaction"
default_pool_size = 20

# Configuração do Studio (UI administrativa)
[studio]
enabled = true
port = 54323
api_url = "http://localhost:54321"

# API Gateway
[api]
enabled = true
port = 54321
```


## Parte 2: Migração dos Dados Existentes

### 2.1 Exportar Schemas e Dados do PostgreSQL Atual

Antes de desligar o serviço atual, exporte todos os dados:[^6]

```bash
# Exportar schema do banco ai_rag
docker exec ai-postgres pg_dump \
  -U rag_user \
  -d ai_rag \
  --schema-only \
  --no-owner \
  --no-acl \
  > ./supabase/migrations/20250101000000_ai_rag_schema.sql

# Exportar dados do ai_rag
docker exec ai-postgres pg_dump \
  -U rag_user \
  -d ai_rag \
  --data-only \
  --no-owner \
  --no-acl \
  --column-inserts \
  > ./supabase/seed_ai_rag.sql

# Repetir para plane_db
docker exec ai-postgres pg_dump \
  -U rag_user \
  -d plane_db \
  --schema-only \
  --no-owner \
  --no-acl \
  > ./supabase/migrations/20250101000001_plane_db_schema.sql

docker exec ai-postgres pg_dump \
  -U rag_user \
  -d plane_db \
  --data-only \
  --no-owner \
  --no-acl \
  --column-inserts \
  > ./supabase/seed_plane_db.sql
```


### 2.2 Ajustar Scripts de Migração

O Supabase usa um único banco de dados PostgreSQL com schemas separados. Ajuste os scripts exportados:

**Arquivo: `supabase/migrations/20250101000000_ai_rag_schema.sql`**

```sql
-- Criar schema dedicado para ai_rag (se ainda não existir)
CREATE SCHEMA IF NOT EXISTS ai_rag;

-- Mover todas as definições de tabelas para o schema ai_rag
-- Adicionar "ai_rag." antes de cada CREATE TABLE

-- Exemplo (baseado no seu init-db.sql):
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Suas tabelas RAG (adaptar do init-db.sql)
-- Substituir "rag." por "ai_rag."
CREATE TABLE ai_rag.sources (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  url TEXT UNIQUE NOT NULL,
  source_type VARCHAR(50) NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ... (continuar com todas as tabelas do seu init-db.sql)
```

**Arquivo: `supabase/migrations/20250101000001_plane_db_schema.sql`**

```sql
-- Criar schema dedicado para Plane
CREATE SCHEMA IF NOT EXISTS plane;

-- Mover tabelas do Plane para o schema plane
-- (O Plane geralmente cria suas próprias tabelas via migrations)
```


### 2.3 Iniciar Supabase e Aplicar Migrações

```bash
# Iniciar instância local do Supabase
supabase start

# Isso iniciará todos os serviços e exibirá:
# API URL: http://localhost:54321
# DB URL: postgresql://postgres:postgres@localhost:54322/postgres
# Studio URL: http://localhost:54323
# anon key: eyJh...
# service_role key: eyJh...
```

Anote as credenciais exibidas, especialmente:

- **DB URL**: para conectar serviços externos
- **anon key** e **service_role key**: para autenticação na API[^3][^7][^2]


### 2.4 Importar Dados

```bash
# Aplicar seeds manualmente (o Supabase CLI já aplicou as migrations)
supabase db reset

# Ou importar dados diretamente via psql
PGPASSWORD=postgres psql \
  -h localhost \
  -p 54322 \
  -U postgres \
  -d postgres \
  -f ./supabase/seed_ai_rag.sql

PGPASSWORD=postgres psql \
  -h localhost \
  -p 54322 \
  -U postgres \
  -d postgres \
  -f ./supabase/seed_plane_db.sql
```


## Parte 3: Configuração de Variáveis de Ambiente

### 3.1 Atualizar `.env` Principal

Edite `/ai-stack/.env` para apontar para o Supabase:[^1]

```bash
# --- Configuração do Supabase Local ---
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=eyJh... # (copiar do output do supabase start)
SUPABASE_SERVICE_ROLE_KEY=eyJh... # (copiar do output)

# --- Database Configuration (Supabase PostgreSQL) ---
# Conexão direta ao PostgreSQL do Supabase
SUPABASE_DB_HOST=localhost
SUPABASE_DB_PORT=54322
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=postgres  # Senha padrão do Supabase local
SUPABASE_DB_NAME=postgres

# Manter por compatibilidade (alguns serviços usam esta variável)
DB_PASSWORD=postgres

# --- LiteLLM Database ---
# Formato: postgresql://usuario:senha@host:porta/database
LITELLM_DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:54322/postgres

# --- n8n Database ---
N8N_DB_POSTGRESDB_HOST=host.docker.internal
N8N_DB_POSTGRESDB_PORT=54322
N8N_DB_POSTGRESDB_DATABASE=postgres
N8N_DB_POSTGRESDB_USER=postgres
N8N_DB_POSTGRESDB_PASSWORD=postgres
N8N_DB_POSTGRESDB_SCHEMA=n8n

# --- Plane Database ---
PLANE_DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:54322/postgres
PLANE_POSTGRES_HOST=host.docker.internal
PLANE_POSTGRES_PORT=54322
PLANE_POSTGRES_DB=postgres
PLANE_POSTGRES_USER=postgres
PLANE_POSTGRES_PASSWORD=postgres
```

**Nota Importante**: Usamos `host.docker.internal` porque o Supabase roda fora do docker-compose da sua stack, mas na mesma máquina.[^8][^9]

### 3.2 Atualizar `.env.lightrag.env`

```bash
# --- PostgreSQL Configuration (Supabase) ---
POSTGRES_HOST=host.docker.internal
POSTGRES_PORT=54322
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASE=postgres
POSTGRES_MAX_CONNECTIONS=20
```


### 3.3 Atualizar `.env.n8n.env`

```bash
# Database Configuration (Supabase)
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=host.docker.internal
DB_POSTGRESDB_PORT=54322
DB_POSTGRESDB_DATABASE=postgres
DB_POSTGRESDB_USER=postgres
DB_POSTGRESDB_PASSWORD=postgres
DB_POSTGRESDB_SCHEMA=n8n
```


### 3.4 Atualizar `.env.plane.env`

```bash
# --- Database Configuration (Supabase PostgreSQL) ---
DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:54322/postgres?schema=plane
POSTGRES_HOST=host.docker.internal
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_PORT=54322
```


## Parte 4: Modificar docker-compose.yml

### 4.1 Remover o Serviço postgres

Comente ou remova o serviço `postgres` do `docker-compose.yml`:[^10]

```yaml
# Comentar todo o serviço postgres
# postgres:
#   image: pgvector/pgvector:pg16
#   container_name: ai-postgres
#   ...
```


### 4.2 Atualizar Serviços Dependentes

Remova as dependências do serviço `postgres` antigo e ajuste as conexões:

```yaml
services:
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    container_name: ai-litellm
    restart: always
    volumes:
      - ./config/auto-headers-config.yaml:/app/config.yaml:ro
      - ./config/github_token.json:/app/github_token.json:ro
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY:-sk-auto-headers-2025}
      # Atualizar para apontar para Supabase
      - DATABASE_URL=${LITELLM_DATABASE_URL}
      - LITELLM_LOG=INFO
      - STORE_MODEL_IN_DB=True
      - GITHUB_API_KEY=${GITHUB_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    ports:
      - "4001:4000"
    networks:
      ai_net:
        ipv4_address: 172.31.0.25
    # Remover depends_on do postgres
    extra_hosts:
      - "host.docker.internal:host-gateway"
    command: ["--config", "/app/config.yaml", "--port", "4000", "--host", "0.0.0.0"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  lightrag:
    build:
      context: .
      dockerfile: Dockerfile.lightrag
    container_name: ai-lightrag
    restart: always
    env_file:
      - .env.lightrag.env
    environment:
      - DB_PASSWORD=${DB_PASSWORD}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - LIGHTRAG_API_KEY=${LIGHTRAG_API_KEY}
      - LLM_BINDING_HOST=http://litellm:4000
      - LLM_BINDING_API_KEY=${LITELLM_MASTER_KEY:-sk-auto-headers-2025}
      - EMBEDDING_BINDING_HOST=http://litellm:4000
      - EMBEDDING_BINDING_API_KEY=${LITELLM_MASTER_KEY:-sk-auto-headers-2025}
      # Atualizar conexão PostgreSQL
      - POSTGRES_HOST=host.docker.internal
      - POSTGRES_PORT=54322
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - lightrag_data:/app/storage
      - ./memory-bank:/app/memory-bank:rw
    ports:
      - "9621:9621"
    networks:
      ai_net:
        ipv4_address: 172.31.0.20
    depends_on:
      neo4j:
        condition: service_healthy
      litellm:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9621/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s

  n8n:
    image: n8nio/n8n:latest
    env_file:
      - .env.n8n.env
    container_name: ai-n8n
    restart: always
    environment:
      - N8N_PROTOCOL=http
      - N8N_HOST=localhost
      - N8N_PORT=5678
      - WEBHOOK_URL=http://localhost:5678/
      - GENERIC_TIMEZONE=America/Sao_Paulo
      - N8N_SECURE_COOKIE=false
      - N8N_LOG_LEVEL=info
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - DB_PASSWORD=${DB_PASSWORD}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - LIGHTRAG_API_KEY=${LIGHTRAG_API_KEY}
      # Database Configuration (Supabase)
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=host.docker.internal
      - DB_POSTGRESDB_PORT=54322
      - DB_POSTGRESDB_DATABASE=postgres
      - DB_POSTGRESDB_USER=postgres
      - DB_POSTGRESDB_PASSWORD=postgres
      - DB_POSTGRESDB_SCHEMA=n8n
      - LITELLM_API_BASE=http://litellm:4000
      - LITELLM_API_KEY=${LITELLM_MASTER_KEY:-sk-auto-headers-2025}
      - N8N_ENCRYPTION_KEY=n8n_ultra_secure_encryption_key_2025_advanced
    volumes:
      - n8n_data:/home/node/.n8n
      - ./scripts:/app/scripts:ro
    ports:
      - "5678:5678"
    networks:
      ai_net:
        ipv4_address: 172.31.0.30
    depends_on:
      lightrag:
        condition: service_healthy
      litellm:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5678/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 300s

  # Plane API Backend
  plane-api:
    image: makeplane/plane-backend:latest
    container_name: ai-plane-api
    restart: always
    env_file:
      - .env.plane.env
    environment:
      # Database - Supabase PostgreSQL
      - DATABASE_URL=${PLANE_DATABASE_URL}
      - POSTGRES_HOST=host.docker.internal
      - POSTGRES_DB=postgres
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_PORT=54322
      # Redis
      - REDIS_URL=redis://plane-redis:6379/
      # Application Settings
      - SECRET_KEY=${PLANE_SECRET_KEY}
      - WEB_URL=http://localhost:3002
      - CORS_ALLOWED_ORIGINS=http://localhost:3002
      # Storage (MinIO)
      - USE_MINIO=1
      - AWS_REGION=us-east-1
      - AWS_ACCESS_KEY_ID=${PLANE_AWS_ACCESS_KEY}
      - AWS_SECRET_ACCESS_KEY=${PLANE_AWS_SECRET_KEY}
      - AWS_S3_ENDPOINT_URL=http://plane-minio:9000
      - AWS_S3_BUCKET_NAME=plane-uploads
    volumes:
      - ./plane-logs:/code/plane/logs
    networks:
      ai_net:
        ipv4_address: 172.31.0.61
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      plane-redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 90s

  # Plane Worker e Beat Worker - Similar updates
  plane-worker:
    image: makeplane/plane-backend:latest
    container_name: ai-plane-worker
    restart: always
    command: ./bin/worker
    env_file:
      - .env.plane.env
    environment:
      - DATABASE_URL=${PLANE_DATABASE_URL}
      - REDIS_URL=redis://plane-redis:6379/
      - SECRET_KEY=${PLANE_SECRET_KEY}
    networks:
      ai_net:
        ipv4_address: 172.31.0.62
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      plane-api:
        condition: service_healthy

  plane-beat-worker:
    image: makeplane/plane-backend:latest
    container_name: ai-plane-beat-worker
    restart: always
    command: ./bin/beat
    env_file:
      - .env.plane.env
    environment:
      - DATABASE_URL=${PLANE_DATABASE_URL}
      - REDIS_URL=redis://plane-redis:6379/
      - SECRET_KEY=${PLANE_SECRET_KEY}
    networks:
      ai_net:
        ipv4_address: 172.31.0.63
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      plane-api:
        condition: service_healthy
```


## Parte 5: Gerenciamento de Schemas no Supabase

Como o Supabase usa um único banco de dados PostgreSQL, você precisa organizar seus dados em schemas separados:[^6][^4]

### 5.1 Criar Schemas via Supabase Studio

Acesse `http://localhost:54323` e use o SQL Editor:

```sql
-- Schema para LightRAG (já existe do init-db.sql adaptado)
CREATE SCHEMA IF NOT EXISTS ai_rag;
GRANT ALL ON SCHEMA ai_rag TO postgres;

-- Schema para n8n
CREATE SCHEMA IF NOT EXISTS n8n;
GRANT ALL ON SCHEMA n8n TO postgres;

-- Schema para Plane
CREATE SCHEMA IF NOT EXISTS plane;
GRANT ALL ON SCHEMA plane TO postgres;

-- Verificar schemas
SELECT schema_name FROM information_schema.schemata;
```


### 5.2 Configurar Search Path

Para que os serviços encontrem suas tabelas automaticamente:

```sql
-- Configurar search_path padrão para cada usuário/schema
ALTER DATABASE postgres SET search_path TO public, ai_rag, n8n, plane;
```


## Parte 6: Teste e Validação

### 6.1 Iniciar o Supabase

```bash
# Parar stack atual
cd /path/to/ai-stack
docker-compose down

# Iniciar Supabase
supabase start

# Aguardar todos os serviços ficarem prontos
# Anote as credenciais exibidas
```


### 6.2 Verificar Conectividade do Banco

```bash
# Testar conexão direta
PGPASSWORD=postgres psql \
  -h localhost \
  -p 54322 \
  -U postgres \
  -d postgres \
  -c "SELECT current_database(), current_schema();"

# Verificar extensões instaladas
PGPASSWORD=postgres psql \
  -h localhost \
  -p 54322 \
  -U postgres \
  -d postgres \
  -c "SELECT * FROM pg_extension;"
```


### 6.3 Testar Serviços Individualmente

```bash
# Iniciar apenas um serviço por vez para debug
docker-compose up litellm

# Verificar logs
docker logs -f ai-litellm

# Se bem-sucedido, testar próximo serviço
docker-compose up n8n
docker logs -f ai-n8n
```


### 6.4 Iniciar Stack Completo

```bash
# Após validar cada serviço
docker-compose up -d

# Monitorar logs
docker-compose logs -f
```


### 6.5 Validar Funcionalidades

**LightRAG**:

```bash
curl http://localhost:9621/health
```

**n8n**:

```bash
curl http://localhost:5678/healthz
```

**Plane**:

```bash
curl http://localhost:3002
```

**Supabase Studio**:
Acesse `http://localhost:54323` e navegue pelas tabelas para confirmar que os dados foram importados corretamente.[^11][^7][^2]

## Parte 7: Recursos Adicionais do Supabase

Agora que sua stack usa Supabase, você tem acesso a recursos extras:

### 7.1 API REST Automática

O PostgREST gera automaticamente endpoints REST para suas tabelas:[^9][^2]

```bash
# Exemplo: Listar dados da tabela ai_rag.sources
curl -X GET 'http://localhost:54321/rest/v1/sources' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```


### 7.2 Realtime Subscriptions

Adicione funcionalidade de tempo real às suas tabelas:[^2]

```sql
-- Habilitar realtime para a tabela sources
ALTER PUBLICATION supabase_realtime ADD TABLE ai_rag.sources;
```


### 7.3 Row Level Security (RLS)

Adicione segurança em nível de linha:[^12][^2]

```sql
-- Habilitar RLS
ALTER TABLE ai_rag.sources ENABLE ROW LEVEL SECURITY;

-- Criar política de acesso
CREATE POLICY "Allow all access" ON ai_rag.sources
  FOR ALL USING (true);
```


## Parte 8: Backup e Manutenção

### 8.1 Backup via Supabase CLI

```bash
# Backup completo do banco
supabase db dump -f backup_$(date +%Y%m%d).sql

# Backup apenas de um schema
supabase db dump -f backup_ai_rag.sql --schema ai_rag
```


### 8.2 Gerenciamento de Migrações

```bash
# Criar nova migração
supabase migration new add_new_table

# Aplicar migrações pendentes
supabase db reset

# Ver status das migrações
supabase migration list
```


### 8.3 Parar e Reiniciar Supabase

```bash
# Parar Supabase (mantém dados)
supabase stop

# Parar e remover todos os dados
supabase stop --no-backup

# Reiniciar
supabase start
```


## Parte 9: Troubleshooting

### Problema: Serviços não conseguem conectar ao Supabase

**Solução**: Verifique se `host.docker.internal` está acessível:

```bash
# Testar de dentro de um container
docker exec ai-n8n ping host.docker.internal
```

Se não funcionar, use o IP da máquina host:

```bash
# Descobrir IP do host
ip addr show docker0 | grep inet

# Atualizar .env com o IP
SUPABASE_DB_HOST=172.17.0.1  # Exemplo
```


### Problema: Extensão pgvector não disponível

**Solução**: O Supabase local já inclui pgvector. Verifique:[^2]

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

Se não estiver instalado:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```


### Problema: Plane não cria tabelas automaticamente

**Solução**: O Plane precisa rodar migrations na primeira inicialização. Execute:

```bash
# Conectar ao container do Plane API
docker exec -it ai-plane-api /bin/bash

# Rodar migrations manualmente
python manage.py migrate
```


### Problema: Performance degradada

**Solução**: Ajuste configurações do PostgreSQL no `config.toml`:[^13]

```toml
[db]
shared_preload_libraries = 'pg_stat_statements, pgvector'
shared_buffers = '256MB'
effective_cache_size = '1GB'
maintenance_work_mem = '128MB'
```

Depois reinicie:

```bash
supabase stop
supabase start
```


## Resumo Final

Após completar este guia, sua arquitetura ficará assim:

```
┌─────────────────────────────────────────────────────────┐
│                    Supabase Local                       │
│  ┌─────────────┐  ┌──────────┐  ┌─────────────────┐   │
│  │ PostgreSQL  │  │  Studio  │  │  API Gateway    │   │
│  │  (54322)    │  │ (54323)  │  │    (54321)      │   │
│  │             │  │          │  │                 │   │
│  │ • ai_rag    │  └──────────┘  └─────────────────┘   │
│  │ • n8n       │       ▲               ▲               │
│  │ • plane     │       │               │               │
│  └─────────────┘       │               │               │
└────────┬───────────────┴───────────────┴───────────────┘
         │ (host.docker.internal:54322)
         ▼
┌─────────────────────────────────────────────────────────┐
│            Docker Compose (ai-stack)                    │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐ │
│  │ LiteLLM  │  │ LightRAG │  │   n8n   │  │  Plane  │ │
│  │  (4001)  │  │  (9621)  │  │ (5678)  │  │ (3002)  │ │
│  └──────────┘  └──────────┘  └─────────┘  └─────────┘ │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐              │
│  │  Neo4j   │  │OpenWebUI │  │Portainer│              │
│  │  (7474)  │  │  (3001)  │  │ (9000)  │              │
│  └──────────┘  └──────────┘  └─────────┘              │
└─────────────────────────────────────────────────────────┘
```

**Benefícios da migração**:

- **API REST automática** para todas as tabelas[^9][^2]
- **Interface administrativa** (Studio) para gerenciar dados[^11][^2]
- **Realtime subscriptions** para atualizações em tempo real[^2]
- **Row Level Security** para controle granular de acesso[^2]
- **Migrações versionadas** via CLI[^7][^3]
- **Backup simplificado** com comandos integrados[^3]

**Comandos essenciais**:

```bash
# Gerenciamento do Supabase
supabase start          # Iniciar instância local
supabase stop           # Parar instância
supabase status         # Ver status dos serviços
supabase db reset       # Resetar banco e aplicar migrations

# Gerenciamento da Stack
docker-compose up -d    # Iniciar todos os serviços
docker-compose down     # Parar todos os serviços
docker-compose logs -f  # Ver logs em tempo real
```

Sua stack agora está usando uma instância local completa do Supabase, mantendo toda a funcionalidade existente enquanto ganha acesso a recursos adicionais de gerenciamento e API.[^10][^1][^3][^2]
<span style="display:none">[^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30][^31][^32][^33][^34][^35][^36][^37][^38][^39][^40][^41][^42][^43][^44][^45][^46][^47][^48][^49][^50][^51][^52][^53][^54][^55][^56]</span>

<div align="center">⁂</div>

[^1]: envs_md.md

[^2]: https://supabase.com/docs/guides/local-development/cli/getting-started

[^3]: https://dev.to/jamescroissant/setting-up-of-supabase-cli-and-local-environment-388f

[^4]: https://supabase.com/docs/guides/local-development/managing-config

[^5]: https://supabase.com/docs/guides/deployment/branching/configuration

[^6]: init-db.sql

[^7]: https://dev.to/sreejinsreenivasan/supabase-a-guide-to-setting-up-your-local-environment-4cgf

[^8]: https://www.reddit.com/r/docker/comments/v4oqmp/external_postgresql_database_instead_of_a_db/

[^9]: https://supabase.com/docs/guides/database/connecting-to-postgres

[^10]: docker-compose.yml

[^11]: https://usenextbase.com/docs/v2/installation/setting-up-supabase-locally

[^12]: https://supabase.com/docs/guides/functions/connect-to-postgres

[^13]: postgres.conf

[^14]: README.md

[^15]: https://www.reddit.com/r/Supabase/comments/1j6zqge/how_to_self_host_in_under_20_minutes/

[^16]: https://pigsty.io/blog/db/supabase/

[^17]: https://mydevpa.ge/blog/setup-supabase-studio-mcp-locally

[^18]: https://supabase.com/docs/guides/self-hosting/docker

[^19]: https://dev.to/arthurkay/self-hosted-supabase-with-external-postgresql-apd

[^20]: https://www.youtube.com/watch?v=i1STOfZ-_R0

[^21]: https://github.com/orgs/supabase/discussions/33843

[^22]: https://github.com/orgs/supabase/discussions/18376

[^23]: https://supabase.com/docs/guides/local-development

[^24]: https://supabase.com/docs/guides/self-hosting/storage/config

[^25]: https://www.reddit.com/r/Supabase/comments/1m87gqb/how_to_configure_supabases_local_development/

[^26]: https://supabase.com/docs/guides/self-hosting/realtime/config

[^27]: https://www.youtube.com/watch?v=BceVcpiOlKM

[^28]: https://supabase.com/docs/guides/database/postgres/configuration

[^29]: https://supabase.com/docs/guides/self-hosting

[^30]: https://activeno.de/blog/2023-08/the-ultimate-supabase-self-hosting-guide/

[^31]: https://buildship.com/integrations/apps/supabase-and-postgres

[^32]: https://supabase.com/docs/guides/platform/migrating-to-supabase/postgres

[^33]: https://github.com/supabase/cli/issues/3327

[^34]: https://www.tencentcloud.com/document/product/409/73395

[^35]: https://www.reddit.com/r/Supabase/comments/zl1rmo/can_supabase_work_with_an_existing_pgsql_database/

[^36]: https://www.reddit.com/r/Supabase/comments/1ic7lqv/how_do_you_push_configtoml_file_to_the_remote_db/

[^37]: https://www.youtube.com/watch?v=oGV5YXBX5JI

[^38]: https://supabase.com/docs/guides/cli/config

[^39]: https://www.prisma.io/docs/orm/overview/databases/supabase

[^40]: https://supabase.com/docs/reference/cli/introduction

[^41]: https://gist.github.com/PLyn/8d2a8b24b4d058d08445cff14cb0271a

[^42]: https://supabase.com/docs/guides/functions/secrets

[^43]: https://www.youtube.com/watch?v=_bv9d9tPXz4

[^44]: https://ceiapoa.com.br/blog/supercharge-your-supabase-setup-with

[^45]: https://docs.shipped.club/features/supabase

[^46]: https://github.com/BerriAI/litellm/issues/8064

[^47]: https://stackoverflow.com/questions/59715622/docker-compose-and-create-db-in-postgres-on-init

[^48]: https://www.youtube.com/watch?v=ti43gv1_f3E

[^49]: https://github.com/orgs/supabase/discussions/3218

[^50]: https://dev.to/ayothedoc3/how-to-self-host-n8n-on-render-with-postgresql-persistence-4m7k

[^51]: https://github.com/orgs/supabase/discussions/12554

[^52]: https://stackoverflow.com/questions/75048097/cannot-access-env-variables-react-supabase

[^53]: https://n8n.io/integrations/postgres/

[^54]: https://www.reddit.com/r/Supabase/comments/12ehsx3/supabase_and_nextjs_environment_variables/

[^55]: https://www.cdata.com/kb/tech/postgresql-cloud-n8n.rst

[^56]: https://www.youtube.com/watch?v=OrGnAobXVBI

