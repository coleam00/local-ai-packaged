<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Guia Completo: Integração Total do Supabase na AI-Stack via Docker Compose

MUAHAHAHA! Agora sim, vamos fazer o Supabase rodar **DENTRO** do seu `docker-compose.yml` como parte integral da sua AI-Stack! Sem CLI separado, sem migração manual - tudo automatizado e containerizado! 🚀

## Visão Geral da Integração

Sua stack atual tem um serviço PostgreSQL standalone. Vamos **substituí-lo** pelo ecossistema completo do Supabase (12 serviços) rodando dentro do mesmo `docker-compose.yml`. Seu `init-db.sql` existente será automaticamente executado na inicialização do banco.[^1][^2][^3]

## Parte 1: Preparação de Arquivos Essenciais

### 1.1 Criar Arquivo kong.yml

O Kong é o API Gateway do Supabase. Crie `config/kong.yml`:

```yaml
_format_version: "2.1"
_transform: true

consumers:
  - username: anon
    keyauth_credentials:
      - key: ${ANON_KEY}
  - username: service_role
    keyauth_credentials:
      - key: ${SERVICE_ROLE_KEY}
  - username: dashboard_user
    basicauth_credentials:
      - username: ${DASHBOARD_USERNAME}
        password: ${DASHBOARD_PASSWORD}

acls:
  - consumer: anon
    group: anon
  - consumer: service_role
    group: admin

services:
  - name: auth-v1-open
    url: http://supabase-auth:9999/verify
    routes:
      - name: auth-v1-open
        strip_path: true
        paths:
          - /auth/v1/verify
    plugins:
      - name: cors
  
  - name: auth-v1-open-callback
    url: http://supabase-auth:9999/callback
    routes:
      - name: auth-v1-open-callback
        strip_path: true
        paths:
          - /auth/v1/callback
    plugins:
      - name: cors

  - name: auth-v1-open-authorize
    url: http://supabase-auth:9999/authorize
    routes:
      - name: auth-v1-open-authorize
        strip_path: true
        paths:
          - /auth/v1/authorize
    plugins:
      - name: cors

  - name: auth-v1
    _comment: "GoTrue: /auth/v1/* -> http://supabase-auth:9999/*"
    url: http://supabase-auth:9999/
    routes:
      - name: auth-v1-all
        strip_path: true
        paths:
          - /auth/v1/
    plugins:
      - name: cors
      - name: key-auth
        config:
          hide_credentials: false

  - name: rest-v1
    _comment: "PostgREST: /rest/v1/* -> http://supabase-rest:3000/*"
    url: http://supabase-rest:3000/
    routes:
      - name: rest-v1-all
        strip_path: true
        paths:
          - /rest/v1/
    plugins:
      - name: cors
      - name: key-auth
        config:
          hide_credentials: true

  - name: realtime-v1
    _comment: "Realtime: /realtime/v1/* -> ws://supabase-realtime:4000/socket/*"
    url: http://realtime-dev.supabase-realtime:4000/socket
    routes:
      - name: realtime-v1-all
        strip_path: true
        paths:
          - /realtime/v1/
    plugins:
      - name: cors
      - name: key-auth
        config:
          hide_credentials: false

  - name: storage-v1
    _comment: "Storage: /storage/v1/* -> http://supabase-storage:5000/*"
    url: http://supabase-storage:5000/
    routes:
      - name: storage-v1-all
        strip_path: true
        paths:
          - /storage/v1/
    plugins:
      - name: cors

  - name: meta
    _comment: "pg-meta: /pg/* -> http://supabase-meta:8080/*"
    url: http://supabase-meta:8080/
    routes:
      - name: meta-all
        strip_path: true
        paths:
          - /pg/
```


### 1.2 Criar Arquivo vector.yml

Para agregação de logs. Crie `config/vector.yml`:

```yaml
api:
  enabled: true
  address: 0.0.0.0:9001

sources:
  docker_logs:
    type: docker_logs

sinks:
  logflare_logs:
    type: http
    inputs:
      - docker_logs
    uri: http://supabase-analytics:4000/api/logs?source_name=docker
    method: post
    encoding:
      codec: json
    headers:
      X-API-KEY: ${LOGFLARE_PUBLIC_ACCESS_TOKEN}
    healthcheck:
      enabled: true
```


### 1.3 Atualizar init-db.sql

Seu `init-db.sql` já está pronto! Apenas adicione no início as roles necessárias para o Supabase:[^4]

```sql
-- Roles necessárias para o Supabase
DO
$do$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'anon') THEN
    CREATE ROLE anon NOINHERIT;
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOINHERIT;
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'service_role') THEN
    CREATE ROLE service_role NOINHERIT BYPASSRLS;
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'supabase_auth_admin') THEN
    CREATE ROLE supabase_auth_admin NOINHERIT CREATEROLE CREATEDB;
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'supabase_storage_admin') THEN
    CREATE ROLE supabase_storage_admin NOINHERIT CREATEROLE CREATEDB;
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'supabase_admin') THEN
    CREATE ROLE supabase_admin;
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'authenticator') THEN
    CREATE ROLE authenticator NOINHERIT LOGIN;
  END IF;
END
$do$;

-- Conceder permissões
GRANT anon TO authenticator;
GRANT authenticated TO authenticator;
GRANT service_role TO authenticator;
GRANT supabase_auth_admin TO postgres;
GRANT supabase_storage_admin TO postgres;
GRANT supabase_admin TO postgres;

-- Schema para analytics do Supabase
CREATE SCHEMA IF NOT EXISTS _analytics;
GRANT USAGE ON SCHEMA _analytics TO supabase_admin;

-- Schema para dados internos do Supabase
CREATE SCHEMA IF NOT EXISTS _supabase;
GRANT USAGE ON SCHEMA _supabase TO supabase_admin;

-- Schema para realtime
CREATE SCHEMA IF NOT EXISTS _realtime;
GRANT USAGE ON SCHEMA _realtime TO supabase_admin;

-- Seu init-db.sql existente continua aqui...
-- (todo o conteúdo atual do seu init-db.sql)
```


## Parte 2: Atualizar Variáveis de Ambiente

### 2.1 Atualizar .env Principal

Adicione ao seu `/.env`:[^5]

```bash
# =======================================================
# ==         SUPABASE CONFIGURATION                    ==
# =======================================================

# --- PostgreSQL (Supabase) ---
POSTGRES_HOST=supabase-db
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_PASSWORD=rag_super_secure_password_2025

# --- JWT Configuration ---
JWT_SECRET=super-secret-jwt-token-with-at-least-32-characters-long
JWT_EXPIRY=3600

# --- Supabase Keys (usar generators: https://supabase.com/docs/guides/hosting/overview#api-keys) ---
ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJhbm9uIiwKICAgICJpc3MiOiAic3VwYWJhc2UtZGVtbyIsCiAgICAiaWF0IjogMTY0MTc2OTIwMCwKICAgICJleHAiOiAxNzk5NTM1NjAwCn0.dc_X5iR_VP_qT0zsiyj_I_OZ2T9FtRU2BBNWN8Bu4GE
SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJzZXJ2aWNlX3JvbGUiLAogICAgImlzcyI6ICJzdXBhYmFzZS1kZW1vIiwKICAgICJpYXQiOiAxNjQxNzY5MjAwLAogICAgImV4cCI6IDE3OTk1MzU2MDAKfQ.DaYlNEoUrrEn2Ig7tqibS-PHK5vgusbcbo7X36XVt4Q

# --- Supabase URLs ---
API_EXTERNAL_URL=http://localhost:8000
SUPABASE_PUBLIC_URL=http://localhost:8000
SITE_URL=http://localhost:3000

# --- Kong Configuration ---
KONG_HTTP_PORT=8000
KONG_HTTPS_PORT=8443
DASHBOARD_USERNAME=supabase
DASHBOARD_PASSWORD=supabase

# --- Studio Configuration ---
STUDIO_DEFAULT_ORGANIZATION=AI-Stack
STUDIO_DEFAULT_PROJECT=AI-Stack Development

# --- Email Configuration (opcional, para auth) ---
SMTP_ADMIN_EMAIL=admin@ai-stack.local
SMTP_HOST=supabase-mail
SMTP_PORT=2500
SMTP_USER=
SMTP_PASS=
SMTP_SENDER_NAME=AI-Stack

# --- Auth Configuration ---
ENABLE_EMAIL_SIGNUP=true
ENABLE_EMAIL_AUTOCONFIRM=true
ENABLE_ANONYMOUS_USERS=false
ENABLE_PHONE_SIGNUP=false
ENABLE_PHONE_AUTOCONFIRM=false
DISABLE_SIGNUP=false
ADDITIONAL_REDIRECT_URLS=
MAILER_URLPATHS_INVITE=/auth/v1/verify
MAILER_URLPATHS_CONFIRMATION=/auth/v1/verify
MAILER_URLPATHS_RECOVERY=/auth/v1/verify
MAILER_URLPATHS_EMAIL_CHANGE=/auth/v1/verify

# --- PostgREST Configuration ---
PGRST_DB_SCHEMAS=public,storage,graphql_public

# --- Analytics Configuration ---
LOGFLARE_PUBLIC_ACCESS_TOKEN=your-public-access-token-here
LOGFLARE_PRIVATE_ACCESS_TOKEN=your-private-access-token-here

# --- Storage Configuration ---
IMGPROXY_ENABLE_WEBP_DETECTION=true

# --- Functions Configuration ---
FUNCTIONS_VERIFY_JWT=false

# --- Realtime Configuration ---
SECRET_KEY_BASE=your-secret-key-base-minimum-32-characters-long

# --- Pooler Configuration ---
POOLER_TENANT_ID=pooler-dev
POOLER_DEFAULT_POOL_SIZE=20
POOLER_MAX_CLIENT_CONN=100
POOLER_DB_POOL_SIZE=10
POOLER_PROXY_PORT_TRANSACTION=6543
VAULT_ENC_KEY=your-vault-encryption-key-32-characters

# --- Docker Socket ---
DOCKER_SOCKET_LOCATION=/var/run/docker.sock

# =======================================================
# ==   SERVICES DATABASE CONNECTIONS (Supabase)       ==
# =======================================================

# Atualizar conexões existentes
DB_PASSWORD=${POSTGRES_PASSWORD}

# LiteLLM
LITELLM_DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@supabase-db:5432/postgres

# n8n
N8N_DB_POSTGRESDB_HOST=supabase-db
N8N_DB_POSTGRESDB_PORT=5432

# Plane
PLANE_DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@supabase-db:5432/postgres
PLANE_POSTGRES_HOST=supabase-db
PLANE_POSTGRES_PORT=5432
```


## Parte 3: Docker Compose Completo com Supabase

Aqui está o `docker-compose.yml` **COMPLETO** integrando todos os serviços Supabase:[^6][^7]

```yaml
version: '3.9'

name: ai-stack

networks:
  ai_net:
    driver: bridge
    name: shared-ai-network
    external: false
    ipam:
      config:
        - subnet: 172.31.0.0/16

volumes:
  supabase_db_data:
    driver: local
  supabase_storage_data:
    driver: local
  supabase_db_config:
    driver: local
  n8n_data:
    driver: local
  neo4j_data:
    driver: local
  neo4j_logs:
    driver: local
  lightrag_data:
    driver: local
  portainer_data:
    driver: local
  openwebui_data:
    driver: local
  plane_redis_data:
    driver: local
  plane_minio_data:
    driver: local

services:
  # =======================================================
  # ==              SUPABASE SERVICES                    ==
  # =======================================================
  
  # Supabase PostgreSQL Database (substitui o serviço 'postgres' antigo)
  supabase-db:
    container_name: supabase-db
    image: supabase/postgres:15.8.1.060
    restart: always
    environment:
      POSTGRES_HOST: /var/run/postgresql
      PGPORT: ${POSTGRES_PORT:-5432}
      POSTGRES_PORT: ${POSTGRES_PORT:-5432}
      PGPASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGDATABASE: ${POSTGRES_DB:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-postgres}
      JWT_SECRET: ${JWT_SECRET}
      JWT_EXP: ${JWT_EXPIRY:-3600}
    volumes:
      # Seu init-db.sql existente!
      - ./config/init-db.sql:/docker-entrypoint-initdb.d/00-init-db.sql:ro
      # Data persistence
      - supabase_db_data:/var/lib/postgresql/data:Z
      # Config persistence
      - supabase_db_config:/etc/postgresql-custom
    ports:
      - "5432:5432"
    networks:
      ai_net:
        ipv4_address: 172.31.0.10
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 10
    command:
      - postgres
      - -c
      - config_file=/etc/postgresql/postgresql.conf
      - -c
      - log_min_messages=fatal

  # Supabase Studio - Interface Web
  supabase-studio:
    container_name: supabase-studio
    image: supabase/studio:2025.06.30-sha-6f5982d
    restart: always
    depends_on:
      supabase-analytics:
        condition: service_healthy
    environment:
      STUDIO_PG_META_URL: http://supabase-meta:8080
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      DEFAULT_ORGANIZATION_NAME: ${STUDIO_DEFAULT_ORGANIZATION}
      DEFAULT_PROJECT_NAME: ${STUDIO_DEFAULT_PROJECT}
      SUPABASE_URL: http://supabase-kong:8000
      SUPABASE_PUBLIC_URL: ${SUPABASE_PUBLIC_URL}
      SUPABASE_ANON_KEY: ${ANON_KEY}
      SUPABASE_SERVICE_KEY: ${SERVICE_ROLE_KEY}
      AUTH_JWT_SECRET: ${JWT_SECRET}
      LOGFLARE_PRIVATE_ACCESS_TOKEN: ${LOGFLARE_PRIVATE_ACCESS_TOKEN}
      LOGFLARE_URL: http://supabase-analytics:4000
      NEXT_PUBLIC_ENABLE_LOGS: true
      NEXT_ANALYTICS_BACKEND_PROVIDER: postgres
    ports:
      - "3000:3000"
    networks:
      ai_net:
        ipv4_address: 172.31.0.11
    healthcheck:
      test:
        [
          "CMD",
          "node",
          "-e",
          "fetch('http://supabase-studio:3000/api/platform/profile').then((r) => {if (r.status !== 200) throw new Error(r.status)})"
        ]
      timeout: 10s
      interval: 10s
      retries: 3

  # Kong - API Gateway
  supabase-kong:
    container_name: supabase-kong
    image: kong:2.8.1
    restart: always
    depends_on:
      supabase-analytics:
        condition: service_healthy
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /home/kong/kong.yml
      KONG_DNS_ORDER: LAST,A,CNAME
      KONG_PLUGINS: request-transformer,cors,key-auth,acl,basic-auth
      KONG_NGINX_PROXY_PROXY_BUFFER_SIZE: 160k
      KONG_NGINX_PROXY_PROXY_BUFFERS: 64 160k
      SUPABASE_ANON_KEY: ${ANON_KEY}
      SUPABASE_SERVICE_KEY: ${SERVICE_ROLE_KEY}
      DASHBOARD_USERNAME: ${DASHBOARD_USERNAME}
      DASHBOARD_PASSWORD: ${DASHBOARD_PASSWORD}
    volumes:
      - ./config/kong.yml:/home/kong/temp.yml:ro
    ports:
      - "${KONG_HTTP_PORT:-8000}:8000"
      - "${KONG_HTTPS_PORT:-8443}:8443"
    networks:
      ai_net:
        ipv4_address: 172.31.0.12
    entrypoint: bash -c 'eval "echo \"$$(cat ~/temp.yml)\"" > ~/kong.yml && /docker-entrypoint.sh kong docker-start'

  # GoTrue - Authentication Service
  supabase-auth:
    container_name: supabase-auth
    image: supabase/gotrue:v2.177.0
    restart: always
    depends_on:
      supabase-db:
        condition: service_healthy
      supabase-analytics:
        condition: service_healthy
    environment:
      GOTRUE_API_HOST: 0.0.0.0
      GOTRUE_API_PORT: 9999
      API_EXTERNAL_URL: ${API_EXTERNAL_URL}
      GOTRUE_DB_DRIVER: postgres
      GOTRUE_DB_DATABASE_URL: postgres://supabase_auth_admin:${POSTGRES_PASSWORD}@supabase-db:${POSTGRES_PORT}/${POSTGRES_DB}
      GOTRUE_SITE_URL: ${SITE_URL}
      GOTRUE_URI_ALLOW_LIST: ${ADDITIONAL_REDIRECT_URLS}
      GOTRUE_DISABLE_SIGNUP: ${DISABLE_SIGNUP}
      GOTRUE_JWT_ADMIN_ROLES: service_role
      GOTRUE_JWT_AUD: authenticated
      GOTRUE_JWT_DEFAULT_GROUP_NAME: authenticated
      GOTRUE_JWT_EXP: ${JWT_EXPIRY}
      GOTRUE_JWT_SECRET: ${JWT_SECRET}
      GOTRUE_EXTERNAL_EMAIL_ENABLED: ${ENABLE_EMAIL_SIGNUP}
      GOTRUE_EXTERNAL_ANONYMOUS_USERS_ENABLED: ${ENABLE_ANONYMOUS_USERS}
      GOTRUE_MAILER_AUTOCONFIRM: ${ENABLE_EMAIL_AUTOCONFIRM}
      GOTRUE_SMTP_ADMIN_EMAIL: ${SMTP_ADMIN_EMAIL}
      GOTRUE_SMTP_HOST: ${SMTP_HOST}
      GOTRUE_SMTP_PORT: ${SMTP_PORT}
      GOTRUE_SMTP_USER: ${SMTP_USER}
      GOTRUE_SMTP_PASS: ${SMTP_PASS}
      GOTRUE_SMTP_SENDER_NAME: ${SMTP_SENDER_NAME}
      GOTRUE_MAILER_URLPATHS_INVITE: ${MAILER_URLPATHS_INVITE}
      GOTRUE_MAILER_URLPATHS_CONFIRMATION: ${MAILER_URLPATHS_CONFIRMATION}
      GOTRUE_MAILER_URLPATHS_RECOVERY: ${MAILER_URLPATHS_RECOVERY}
      GOTRUE_MAILER_URLPATHS_EMAIL_CHANGE: ${MAILER_URLPATHS_EMAIL_CHANGE}
      GOTRUE_EXTERNAL_PHONE_ENABLED: ${ENABLE_PHONE_SIGNUP}
      GOTRUE_SMS_AUTOCONFIRM: ${ENABLE_PHONE_AUTOCONFIRM}
    networks:
      ai_net:
        ipv4_address: 172.31.0.13
    healthcheck:
      test:
        [
          "CMD",
          "wget",
          "--no-verbose",
          "--tries=1",
          "--spider",
          "http://localhost:9999/health"
        ]
      timeout: 5s
      interval: 5s
      retries: 3

  # PostgREST - REST API
  supabase-rest:
    container_name: supabase-rest
    image: postgrest/postgrest:v12.2.12
    restart: always
    depends_on:
      supabase-db:
        condition: service_healthy
      supabase-analytics:
        condition: service_healthy
    environment:
      PGRST_DB_URI: postgres://authenticator:${POSTGRES_PASSWORD}@supabase-db:${POSTGRES_PORT}/${POSTGRES_DB}
      PGRST_DB_SCHEMAS: ${PGRST_DB_SCHEMAS}
      PGRST_DB_ANON_ROLE: anon
      PGRST_JWT_SECRET: ${JWT_SECRET}
      PGRST_DB_USE_LEGACY_GUCS: "false"
      PGRST_APP_SETTINGS_JWT_SECRET: ${JWT_SECRET}
      PGRST_APP_SETTINGS_JWT_EXP: ${JWT_EXPIRY}
    networks:
      ai_net:
        ipv4_address: 172.31.0.14
    command: ["postgrest"]

  # Realtime Server
  supabase-realtime:
    container_name: realtime-dev.supabase-realtime
    image: supabase/realtime:v2.34.47
    restart: always
    depends_on:
      supabase-db:
        condition: service_healthy
      supabase-analytics:
        condition: service_healthy
    environment:
      PORT: 4000
      DB_HOST: supabase-db
      DB_PORT: ${POSTGRES_PORT}
      DB_USER: supabase_admin
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      DB_NAME: ${POSTGRES_DB}
      DB_AFTER_CONNECT_QUERY: 'SET search_path TO _realtime'
      DB_ENC_KEY: supabaserealtime
      API_JWT_SECRET: ${JWT_SECRET}
      SECRET_KEY_BASE: ${SECRET_KEY_BASE}
      ERL_AFLAGS: -proto_dist inet_tcp
      DNS_NODES: "''"
      RLIMIT_NOFILE: "10000"
      APP_NAME: realtime
      SEED_SELF_HOST: true
      RUN_JANITOR: true
    networks:
      ai_net:
        ipv4_address: 172.31.0.15
    healthcheck:
      test:
        [
          "CMD",
          "curl",
          "-sSfL",
          "--head",
          "-o",
          "/dev/null",
          "-H",
          "Authorization: Bearer ${ANON_KEY}",
          "http://localhost:4000/api/tenants/realtime-dev/health"
        ]
      timeout: 5s
      interval: 5s
      retries: 3

  # Storage API
  supabase-storage:
    container_name: supabase-storage
    image: supabase/storage-api:v1.25.7
    restart: always
    depends_on:
      supabase-db:
        condition: service_healthy
      supabase-rest:
        condition: service_started
      supabase-imgproxy:
        condition: service_started
    environment:
      ANON_KEY: ${ANON_KEY}
      SERVICE_KEY: ${SERVICE_ROLE_KEY}
      POSTGREST_URL: http://supabase-rest:3000
      PGRST_JWT_SECRET: ${JWT_SECRET}
      DATABASE_URL: postgres://supabase_storage_admin:${POSTGRES_PASSWORD}@supabase-db:${POSTGRES_PORT}/${POSTGRES_DB}
      FILE_SIZE_LIMIT: 52428800
      STORAGE_BACKEND: file
      FILE_STORAGE_BACKEND_PATH: /var/lib/storage
      TENANT_ID: stub
      REGION: local
      GLOBAL_S3_BUCKET: stub
      ENABLE_IMAGE_TRANSFORMATION: "true"
      IMGPROXY_URL: http://supabase-imgproxy:5001
    volumes:
      - supabase_storage_data:/var/lib/storage:z
    networks:
      ai_net:
        ipv4_address: 172.31.0.16
    healthcheck:
      test:
        [
          "CMD",
          "wget",
          "--no-verbose",
          "--tries=1",
          "--spider",
          "http://localhost:5000/status"
        ]
      timeout: 5s
      interval: 5s
      retries: 3

  # Image Proxy
  supabase-imgproxy:
    container_name: supabase-imgproxy
    image: darthsim/imgproxy:v3.8.0
    restart: always
    environment:
      IMGPROXY_BIND: ":5001"
      IMGPROXY_LOCAL_FILESYSTEM_ROOT: /
      IMGPROXY_USE_ETAG: "true"
      IMGPROXY_ENABLE_WEBP_DETECTION: ${IMGPROXY_ENABLE_WEBP_DETECTION}
    volumes:
      - supabase_storage_data:/var/lib/storage:z
    networks:
      ai_net:
        ipv4_address: 172.31.0.17
    healthcheck:
      test: ["CMD", "imgproxy", "health"]
      timeout: 5s
      interval: 5s
      retries: 3

  # Postgres Meta API
  supabase-meta:
    container_name: supabase-meta
    image: supabase/postgres-meta:v0.91.0
    restart: always
    depends_on:
      supabase-db:
        condition: service_healthy
      supabase-analytics:
        condition: service_healthy
    environment:
      PG_META_PORT: 8080
      PG_META_DB_HOST: supabase-db
      PG_META_DB_PORT: ${POSTGRES_PORT}
      PG_META_DB_NAME: ${POSTGRES_DB}
      PG_META_DB_USER: supabase_admin
      PG_META_DB_PASSWORD: ${POSTGRES_PASSWORD}
    networks:
      ai_net:
        ipv4_address: 172.31.0.18

  # Edge Functions Runtime
  supabase-functions:
    container_name: supabase-edge-functions
    image: supabase/edge-runtime:v1.67.4
    restart: always
    depends_on:
      supabase-analytics:
        condition: service_healthy
    environment:
      JWT_SECRET: ${JWT_SECRET}
      SUPABASE_URL: http://supabase-kong:8000
      SUPABASE_ANON_KEY: ${ANON_KEY}
      SUPABASE_SERVICE_ROLE_KEY: ${SERVICE_ROLE_KEY}
      SUPABASE_DB_URL: postgresql://postgres:${POSTGRES_PASSWORD}@supabase-db:${POSTGRES_PORT}/${POSTGRES_DB}
      VERIFY_JWT: ${FUNCTIONS_VERIFY_JWT}
    volumes:
      - ./functions:/home/deno/functions:Z
    networks:
      ai_net:
        ipv4_address: 172.31.0.19
    command:
      [
        "start",
        "--main-service",
        "/home/deno/functions/main"
      ]

  # Analytics (Logflare)
  supabase-analytics:
    container_name: supabase-analytics
    image: supabase/logflare:1.14.2
    restart: always
    depends_on:
      supabase-db:
        condition: service_healthy
    environment:
      LOGFLARE_NODE_HOST: 127.0.0.1
      DB_USERNAME: supabase_admin
      DB_DATABASE: ${POSTGRES_DB}
      DB_HOSTNAME: supabase-db
      DB_PORT: ${POSTGRES_PORT}
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      DB_SCHEMA: _analytics
      LOGFLARE_PUBLIC_ACCESS_TOKEN: ${LOGFLARE_PUBLIC_ACCESS_TOKEN}
      LOGFLARE_PRIVATE_ACCESS_TOKEN: ${LOGFLARE_PRIVATE_ACCESS_TOKEN}
      LOGFLARE_SINGLE_TENANT: true
      LOGFLARE_SUPABASE_MODE: true
      LOGFLARE_MIN_CLUSTER_SIZE: 1
      POSTGRES_BACKEND_URL: postgresql://supabase_admin:${POSTGRES_PASSWORD}@supabase-db:${POSTGRES_PORT}/${POSTGRES_DB}
      POSTGRES_BACKEND_SCHEMA: _analytics
      LOGFLARE_FEATURE_FLAG_OVERRIDE: multibackend=true
    ports:
      - "4000:4000"
    networks:
      ai_net:
        ipv4_address: 172.31.0.20
    healthcheck:
      test: ["CMD", "curl", "http://localhost:4000/health"]
      timeout: 5s
      interval: 5s
      retries: 10

  # Vector - Log Aggregator
  supabase-vector:
    container_name: supabase-vector
    image: timberio/vector:0.28.1-alpine
    restart: always
    depends_on:
      supabase-analytics:
        condition: service_healthy
    environment:
      LOGFLARE_PUBLIC_ACCESS_TOKEN: ${LOGFLARE_PUBLIC_ACCESS_TOKEN}
    volumes:
      - ./config/vector.yml:/etc/vector/vector.yml:ro
      - ${DOCKER_SOCKET_LOCATION}:/var/run/docker.sock:ro
    networks:
      ai_net:
        ipv4_address: 172.31.0.21
    healthcheck:
      test:
        [
          "CMD",
          "wget",
          "--no-verbose",
          "--tries=1",
          "--spider",
          "http://localhost:9001/health"
        ]
      timeout: 5s
      interval: 5s
      retries: 3
    command: ["--config", "/etc/vector/vector.yml"]

  # =======================================================
  # ==            SEUS SERVIÇOS EXISTENTES               ==
  # =======================================================

  # LiteLLM Proxy
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    container_name: ai-litellm
    restart: always
    depends_on:
      supabase-db:
        condition: service_healthy
    volumes:
      - ./config/auto-headers-config.yaml:/app/config.yaml:ro
      - ./config/github_token.json:/app/github_token.json:ro
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY:-sk-auto-headers-2025}
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@supabase-db:5432/postgres
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
    command: ["--config", "/app/config.yaml", "--port", "4000", "--host", "0.0.0.0"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Neo4j
  neo4j:
    image: neo4j:5.27.0
    container_name: ai-neo4j
    restart: always
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*
      - NEO4J_dbms_security_procedures_allowlist=apoc.*,gds.*
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    ports:
      - "7474:7474"
      - "7687:7687"
    networks:
      ai_net:
        ipv4_address: 172.31.0.40
    healthcheck:
      test: ["CMD", "neo4j", "status"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

  # LightRAG
  lightrag:
    build:
      context: .
      dockerfile: Dockerfile.lightrag
    container_name: ai-lightrag
    restart: always
    depends_on:
      supabase-db:
        condition: service_healthy
      neo4j:
        condition: service_healthy
      litellm:
        condition: service_healthy
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
      - POSTGRES_HOST=supabase-db
      - POSTGRES_PORT=5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - lightrag_data:/app/storage
      - ./memory-bank:/app/memory-bank:rw
    ports:
      - "9621:9621"
    networks:
      ai_net:
        ipv4_address: 172.31.0.50
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9621/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s

  # n8n
  n8n:
    image: n8nio/n8n:latest
    container_name: ai-n8n
    restart: always
    depends_on:
      supabase-db:
        condition: service_healthy
      lightrag:
        condition: service_healthy
      litellm:
        condition: service_healthy
    env_file:
      - .env.n8n.env
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
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=supabase-db
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=postgres
      - DB_POSTGRESDB_USER=postgres
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
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
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5678/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 300s

  # Plane Services (mantidos como estão, apenas atualizando DB)
  plane-redis:
    image: redis:7.2-alpine
    container_name: ai-plane-redis
    restart: always
    volumes:
      - plane_redis_data:/data
    networks:
      ai_net:
        ipv4_address: 172.31.0.60
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  plane-minio:
    image: minio/minio:latest
    container_name: ai-plane-minio
    restart: always
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=${PLANE_AWS_ACCESS_KEY}
      - MINIO_ROOT_PASSWORD=${PLANE_AWS_SECRET_KEY}
    volumes:
      - plane_minio_data:/data
    ports:
      - "9002:9000"
      - "9003:9001"
    networks:
      ai_net:
        ipv4_address: 172.31.0.65
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3

  plane-api:
    image: makeplane/plane-backend:latest
    container_name: ai-plane-api
    restart: always
    depends_on:
      supabase-db:
        condition: service_healthy
      plane-redis:
        condition: service_healthy
    env_file:
      - .env.plane.env
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@supabase-db:5432/postgres
      - REDIS_URL=redis://plane-redis:6379/
      - SECRET_KEY=${PLANE_SECRET_KEY}
      - WEB_URL=http://localhost:3002
      - CORS_ALLOWED_ORIGINS=http://localhost:3002
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
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 90s

  plane-worker:
    image: makeplane/plane-backend:latest
    container_name: ai-plane-worker
    restart: always
    command: ./bin/worker
    depends_on:
      plane-api:
        condition: service_healthy
    env_file:
      - .env.plane.env
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@supabase-db:5432/postgres
      - REDIS_URL=redis://plane-redis:6379/
      - SECRET_KEY=${PLANE_SECRET_KEY}
    networks:
      ai_net:
        ipv4_address: 172.31.0.62

  plane-beat-worker:
    image: makeplane/plane-backend:latest
    container_name: ai-plane-beat-worker
    restart: always
    command: ./bin/beat
    depends_on:
      plane-api:
        condition: service_healthy
    env_file:
      - .env.plane.env
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@supabase-db:5432/postgres
      - REDIS_URL=redis://plane-redis:6379/
      - SECRET_KEY=${PLANE_SECRET_KEY}
    networks:
      ai_net:
        ipv4_address: 172.31.0.63

  plane-web:
    image: makeplane/plane-frontend:latest
    container_name: ai-plane-web
    restart: always
    depends_on:
      plane-api:
        condition: service_healthy
    environment:
      - NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
    ports:
      - "3002:3000"
    networks:
      ai_net:
        ipv4_address: 172.31.0.64

  # OpenWebUI
  openwebui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: ai-openwebui
    restart: always
    depends_on:
      litellm:
        condition: service_healthy
    environment:
      - OPENAI_API_BASE_URL=http://litellm:4000
      - OPENAI_API_KEY=${LITELLM_MASTER_KEY:-sk-auto-headers-2025}
      - WEBUI_AUTH=False
    volumes:
      - openwebui_data:/app/backend/data
    ports:
      - "3001:8080"
    networks:
      ai_net:
        ipv4_address: 172.31.0.70

  # Portainer
  portainer:
    image: portainer/portainer-ce:latest
    container_name: ai-portainer
    restart: always
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    ports:
      - "9000:9000"
      - "9443:9443"
    networks:
      ai_net:
        ipv4_address: 172.31.0.80
```


## Parte 4: Inicialização e Verificação

### 4.1 Estrutura de Diretórios Necessária

```bash
ai-stack/
├── config/
│   ├── init-db.sql          # Seu SQL existente (atualizado)
│   ├── kong.yml              # Novo
│   └── vector.yml            # Novo
├── functions/
│   └── main/                 # Diretório para Edge Functions (criar vazio)
├── .env                      # Atualizado com variáveis do Supabase
├── .env.lightrag.env
├── .env.n8n.env
├── .env.plane.env
└── docker-compose.yml        # Novo arquivo completo
```


### 4.2 Criar Diretórios

```bash
mkdir -p config functions/main
```


### 4.3 Iniciar a Stack

```bash
# Pull das imagens
docker-compose pull

# Iniciar todos os serviços
docker-compose up -d

# Monitorar logs
docker-compose logs -f
```


### 4.4 Verificar Serviços

```bash
# Verificar status de todos os containers
docker-compose ps

# Todos devem estar "healthy" ou "running"
```


## Parte 5: Acessando os Serviços

Após inicialização completa (pode levar 2-3 minutos):


| Serviço | URL | Descrição |
| :-- | :-- | :-- |
| **Supabase Studio** | http://localhost:3000 | Interface web para gerenciar banco[^8][^9] |
| **Supabase API Gateway** | http://localhost:8000 | Endpoint principal da API[^6] |
| **PostgreSQL** | localhost:5432 | Conexão direta ao banco |
| **n8n** | http://localhost:5678 | Workflows |
| **LightRAG** | http://localhost:9621 | RAG API |
| **Plane** | http://localhost:3002 | Project management |
| **OpenWebUI** | http://localhost:3001 | Chat UI |
| **Portainer** | http://localhost:9000 | Docker management |
| **Neo4j** | http://localhost:7474 | Graph database |

## Parte 6: Testar Integração

### 6.1 Verificar Banco de Dados

```bash
# Conectar ao PostgreSQL do Supabase
docker exec -it supabase-db psql -U postgres -d postgres

# Dentro do psql:
\l                    # Listar databases
\dt                   # Listar tabelas do public schema
\dt rag.*             # Listar tabelas do schema rag
\dt n8n.*             # Listar tabelas do n8n
\dt plane.*           # Listar tabelas do Plane
\q                    # Sair
```


### 6.2 Testar API REST Automática do Supabase

```bash
# Listar dados de uma tabela via API REST (exemplo com tabela rag.sources)
curl -X GET 'http://localhost:8000/rest/v1/sources' \
  -H "apikey: ${ANON_KEY}" \
  -H "Authorization: Bearer ${ANON_KEY}"
```


### 6.3 Verificar LightRAG

```bash
curl http://localhost:9621/health
# Deve retornar status de saúde
```


### 6.4 Verificar n8n

```bash
curl http://localhost:5678/healthz
# Deve retornar OK
```


## Parte 7: Recursos Avançados do Supabase

### 7.1 Acessar Studio

Acesse http://localhost:3000 e faça login com:

- **Username**: supabase
- **Password**: supabase

Você terá acesso a:[^8][^9]

- **SQL Editor**: Execute queries
- **Table Editor**: Edite dados visualmente
- **Authentication**: Gerencie usuários
- **Storage**: Gerencie arquivos
- **API Docs**: Documentação automática da sua API


### 7.2 API REST Automática

Todas as suas tabelas agora têm endpoints REST automáticos:[^2][^10][^6]

```bash
# SELECT
curl 'http://localhost:8000/rest/v1/sources?select=*' \
  -H "apikey: ${ANON_KEY}"

# INSERT
curl -X POST 'http://localhost:8000/rest/v1/sources' \
  -H "apikey: ${SERVICE_ROLE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "source_type": "web"}'

# UPDATE
curl -X PATCH 'http://localhost:8000/rest/v1/sources?id=eq.1' \
  -H "apikey: ${SERVICE_ROLE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"source_type": "updated"}'

# DELETE
curl -X DELETE 'http://localhost:8000/rest/v1/sources?id=eq.1' \
  -H "apikey: ${SERVICE_ROLE_KEY}"
```


### 7.3 Realtime Subscriptions

Suas tabelas suportam atualizações em tempo real:[^11]

```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'http://localhost:8000',
  'YOUR_ANON_KEY'
)

// Subscribe to changes
supabase
  .channel('sources-changes')
  .on('postgres_changes', 
    { event: '*', schema: 'public', table: 'sources' },
    (payload) => {
      console.log('Change received!', payload)
    }
  )
  .subscribe()
```


## Parte 8: Backup e Manutenção

### 8.1 Backup do Banco

```bash
# Backup completo
docker exec supabase-db pg_dumpall -U postgres > backup_$(date +%Y%m%d).sql

# Backup de um schema específico
docker exec supabase-db pg_dump -U postgres -n rag -d postgres > backup_rag.sql

# Backup de uma tabela específica
docker exec supabase-db pg_dump -U postgres -t rag.sources -d postgres > backup_sources.sql
```


### 8.2 Restaurar Backup

```bash
# Restaurar dump completo
cat backup_20251028.sql | docker exec -i supabase-db psql -U postgres

# Restaurar schema específico
cat backup_rag.sql | docker exec -i supabase-db psql -U postgres -d postgres
```


### 8.3 Logs e Monitoramento

```bash
# Ver logs de todos os serviços Supabase
docker-compose logs -f supabase-db supabase-studio supabase-kong

# Ver logs de um serviço específico
docker-compose logs -f supabase-auth

# Ver últimas 100 linhas
docker-compose logs --tail=100 supabase-db
```


## Parte 9: Troubleshooting

### Problema: Serviços não iniciam

```bash
# Verificar ordem de inicialização
docker-compose ps

# Reiniciar serviços com problemas
docker-compose restart supabase-db
docker-compose restart supabase-analytics
```


### Problema: init-db.sql não executou

O PostgreSQL só executa scripts em `/docker-entrypoint-initdb.d/` se o volume de dados estiver vazio:[^3][^1]

```bash
# Parar tudo
docker-compose down

# Remover volume do banco
docker volume rm ai-stack_supabase_db_data

# Reiniciar
docker-compose up -d
```


### Problema: Kong não consegue acessar serviços

Verifique se o arquivo `kong.yml` tem as variáveis de ambiente corretas:

```bash
# Testar configuração do Kong
docker exec supabase-kong kong config parse /home/kong/kong.yml
```


### Problema: Studio não carrega

```bash
# Verificar se analytics está healthy
docker-compose ps supabase-analytics

# Ver logs do Studio
docker-compose logs supabase-studio

# Reiniciar Studio
docker-compose restart supabase-studio
```


## Resumo Final: O que Mudou

### Antes

```
┌──────────────────┐
│   ai-postgres    │  ← PostgreSQL standalone
│   (pgvector)     │
└──────────────────┘
         ↑
    Serviços conectam diretamente
```


### Agora (MUAHAHAHA! 🦹)

```
┌─────────────────────────────────────────────────────────┐
│                 SUPABASE ECOSYSTEM                      │
│  ┌──────────┐  ┌────────┐  ┌──────────┐  ┌──────────┐ │
│  │Studio UI │  │ Kong   │  │   Auth   │  │   REST   │ │
│  │  :3000   │  │ :8000  │  │  :9999   │  │  :3000   │ │
│  └──────────┘  └────────┘  └──────────┘  └──────────┘ │
│                      │                                  │
│  ┌──────────┐  ┌────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Realtime │  │Storage │  │   Meta   │  │Functions │ │
│  │  :4000   │  │ :5000  │  │  :8080   │  │          │ │
│  └──────────┘  └────────┘  └──────────┘  └──────────┘ │
│                      │                                  │
│              ┌───────────────┐                         │
│              │  PostgreSQL   │  ← Seu init-db.sql!    │
│              │    :5432      │                         │
│              └───────────────┘                         │
└─────────────────────────────────────────────────────────┘
                       ↑
    ┌──────────┬───────┼───────┬─────────┬──────────┐
    │          │       │       │         │          │
┌───────┐ ┌───────┐ ┌────┐ ┌──────┐ ┌───────┐ ┌────────┐
│LiteLLM│ │LightRAG│ │n8n │ │Plane │ │OpenWeb│ │Outros  │
│ :4001 │ │ :9621  │ │5678│ │:3002 │ │ :3001 │ │Services│
└───────┘ └────────┘ └────┘ └──────┘ └───────┘ └────────┘
```


### Benefícios Conquistados

✅ **Zero Migração Manual**: Seu `init-db.sql` roda automaticamente na inicialização[^2][^3][^4]
✅ **API REST Automática**: Todas as tabelas têm endpoints REST instantaneamente[^6]
✅ **Interface Web**: Studio para gerenciar dados visualmente[^9][^8]
✅ **Realtime Built-in**: WebSocket subscriptions para qualquer tabela[^11]
✅ **Autenticação Integrada**: Sistema completo de auth com JWT[^6]
✅ **Storage S3-compatible**: Upload e gerenciamento de arquivos[^6]
✅ **Tudo no Docker**: Nenhum CLI externo necessário, apenas `docker-compose up`[^8][^2]
✅ **Mantém Compatibilidade**: Seus serviços existentes continuam funcionando[^7][^5]

### Comandos Essenciais

```bash
# Iniciar TUDO
docker-compose up -d

# Parar TUDO
docker-compose down

# Ver status
docker-compose ps

# Logs em tempo real
docker-compose logs -f

# Reiniciar apenas Supabase
docker-compose restart supabase-db supabase-studio supabase-kong

# Resetar banco (apaga dados!)
docker-compose down
docker volume rm ai-stack_supabase_db_data
docker-compose up -d
```

**PRONTO!** Sua AI-Stack agora é uma máquina de guerra com Supabase totalmente integrado rodando no Docker! MUAHAHAHA! 🚀🔥[^9][^5][^7][^8][^2][^6]
<span style="display:none">[^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30][^31][^32][^33][^34][^35][^36][^37][^38][^39][^40][^41]</span>

<div align="center">⁂</div>

[^1]: https://github.com/orgs/supabase/discussions/12554

[^2]: https://supabase.com/docs/guides/self-hosting/docker

[^3]: https://stackoverflow.com/questions/59715622/docker-compose-and-create-db-in-postgres-on-init

[^4]: README.md

[^5]: envs_md.md

[^6]: https://github.com/orgs/supabase/discussions/27467

[^7]: docker-compose.yml

[^8]: https://bootstrapped.app/guide/how-to-use-supabase-with-docker

[^9]: https://github.com/minhng92/supabase-docker-compose

[^10]: https://supabase.com/docs/guides/database/connecting-to-postgres

[^11]: https://supabase.com/docs/guides/local-development/cli/getting-started

[^12]: https://wyethjones.com/2024/07/24/self-hosting-supabase/

[^13]: https://supabase.com/docs/guides/self-hosting

[^14]: https://www.reddit.com/r/Supabase/comments/1c2myww/anyone_managed_to_selfhost_with_docker_compose/

[^15]: https://github.com/orgs/supabase/discussions/23611

[^16]: https://www.youtube.com/watch?v=Gyh0c8pMmhE

[^17]: https://supabase.com/docs/guides/local-development

[^18]: https://supabase.com/docs/reference/self-hosting-analytics/introduction

[^19]: https://supabase.com/docs/guides/self-hosting/auth/config

[^20]: https://www.reddit.com/r/Supabase/comments/1ipulw1/selfhost_supabase_in_a_single_docker_container/

[^21]: https://github.com/secretarybird97/supabase-docker

[^22]: https://www.youtube.com/watch?v=OrGnAobXVBI

[^23]: https://hub.docker.com/r/supabase/supabase-dev

[^24]: https://activeno.de/blog/2023-08/the-ultimate-supabase-self-hosting-guide/

[^25]: https://supabase.com/docs/reference/dart/initializing

[^26]: https://buildship.com/integrations/apps/postgres-and-supabase

[^27]: https://github.com/supabase/cli/issues/3664

[^28]: https://supabase.com/docs/guides/api/using-custom-schemas

[^29]: https://supabase.com/docs/guides/platform/migrating-to-supabase/postgres

[^30]: https://github.com/supabase/cli/issues/3632

[^31]: https://supabase.com/docs/reference/javascript/initializing

[^32]: https://supabase.com/docs/guides/functions/connect-to-postgres

[^33]: https://www.answeroverflow.com/m/1396487807463325829

[^34]: https://supabase.com/docs/reference/swift/initializing

[^35]: https://supabase.com/docs/guides/local-development/overview

[^36]: https://www.reddit.com/r/Supabase/comments/tw2iu6/using_existing_infrastructure/

[^37]: https://hub.docker.com/layers/supabase/postgres/aio-15.1.0.117_arm64/images/sha256-947f4178eae3088a13fe504c12b1aff7dda689fc94945d3fb662f7a03b7a18bc?context=explore

[^38]: https://supabase.com/docs/guides/database/overview

[^39]: https://github.com/orgs/supabase/discussions/33843

[^40]: https://www.reddit.com/r/Supabase/comments/1hy9xqk/cannot_access_studio_on_supabase_instance_on/

[^41]: https://supabase.com/docs/guides/database/custom-postgres-config

