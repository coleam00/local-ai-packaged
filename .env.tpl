# .env.tpl — 1Password secret references for Local AI Packaged
# Generate .env from this template: ./generate-env.sh
# Safe to commit — contains only 1Password references, no actual secrets.

############
# [required]
# n8n credentials
############

N8N_ENCRYPTION_KEY={{ op://Local AI Packaged/n8n/encryption_key }}
N8N_USER_MANAGEMENT_JWT_SECRET={{ op://Local AI Packaged/n8n/jwt_secret }}


############
# [required]
# Supabase Secrets
############

POSTGRES_PASSWORD={{ op://Local AI Packaged/Supabase/postgres_password }}
JWT_SECRET={{ op://Local AI Packaged/Supabase/jwt_secret }}
ANON_KEY={{ op://Local AI Packaged/Supabase/anon_key }}
SERVICE_ROLE_KEY={{ op://Local AI Packaged/Supabase/service_role_key }}
DASHBOARD_USERNAME={{ op://Local AI Packaged/Supabase/dashboard_username }}
DASHBOARD_PASSWORD={{ op://Local AI Packaged/Supabase/dashboard_password }}
POOLER_TENANT_ID={{ op://Local AI Packaged/Supabase/pooler_tenant_id }}

############
# [required]
# Neo4j
############

NEO4J_AUTH={{ op://Local AI Packaged/Neo4j/auth }}

############
# [required]
# Langfuse credentials
############

CLICKHOUSE_PASSWORD={{ op://Local AI Packaged/Langfuse/clickhouse_password }}
MINIO_ROOT_PASSWORD={{ op://Local AI Packaged/Langfuse/minio_root_password }}
LANGFUSE_SALT={{ op://Local AI Packaged/Langfuse/salt }}
NEXTAUTH_SECRET={{ op://Local AI Packaged/Langfuse/nextauth_secret }}
ENCRYPTION_KEY={{ op://Local AI Packaged/Langfuse/encryption_key }}
LANGFUSE_SECRET_KEY={{ op://Local AI Packaged/Langfuse/Secret Key }}
LANGFUSE_PUBLIC_KEY={{ op://Local AI Packaged/Langfuse/Public Key }}
LANGFUSE_BASE_URL={{ op://Local AI Packaged/Langfuse/LANGFUSE_BASE_URL }}

############
# [required for prod]
# Caddy Config
############

# WEBUI_HOSTNAME=openwebui.yourdomain.com
# FLOWISE_HOSTNAME=flowise.yourdomain.com
# SUPABASE_HOSTNAME=supabase.yourdomain.com
# LANGFUSE_HOSTNAME=langfuse.yourdomain.com
# OLLAMA_HOSTNAME=ollama.yourdomain.com
# SEARXNG_HOSTNAME=searxng.yourdomain.com
# NEO4J_HOSTNAME=neo4j.yourdomain.com
# LETSENCRYPT_EMAIL=internal


# Everything below this point is optional.
# Default values will suffice unless you need more features/customization.

############
# Optional Google Authentication for Supabase
############
# ENABLE_GOOGLE_SIGNUP=true
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=
# GOOGLE_REDIRECT_URI=

############
# Optional SearXNG Config
############
# SEARXNG_UWSGI_WORKERS=4
# SEARXNG_UWSGI_THREADS=4

############
# Database
############

POSTGRES_HOST=db
POSTGRES_DB=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres

############
# Supavisor
############
POOLER_PROXY_PORT_TRANSACTION=6543
POOLER_DEFAULT_POOL_SIZE=20
POOLER_MAX_CLIENT_CONN=100
SECRET_KEY_BASE={{ op://Local AI Packaged/Supabase/secret_key_base }}
VAULT_ENC_KEY={{ op://Local AI Packaged/Supabase/vault_enc_key }}
POOLER_DB_POOL_SIZE=5

############
# API Proxy - Kong
############

KONG_HTTP_PORT=8000
KONG_HTTPS_PORT=8443

############
# API - PostgREST
############

PGRST_DB_SCHEMAS=public,storage,graphql_public

############
# Flowise
############
#FLOWISE_USERNAME=your_username
#FLOWISE_PASSWORD=your_password

############
# Auth - GoTrue
############

## General
SITE_URL=https://supabase.tail0d6f8e.ts.net
ADDITIONAL_REDIRECT_URLS=
JWT_EXPIRY=3600
DISABLE_SIGNUP=false
API_EXTERNAL_URL=https://supabase.tail0d6f8e.ts.net

## Mailer Config
MAILER_URLPATHS_CONFIRMATION="/auth/v1/verify"
MAILER_URLPATHS_INVITE="/auth/v1/verify"
MAILER_URLPATHS_RECOVERY="/auth/v1/verify"
MAILER_URLPATHS_EMAIL_CHANGE="/auth/v1/verify"

## Email auth
ENABLE_EMAIL_SIGNUP=true
ENABLE_EMAIL_AUTOCONFIRM=true
SMTP_ADMIN_EMAIL=admin@example.com
SMTP_HOST=supabase-mail
SMTP_PORT=2500
SMTP_USER=fake_mail_user
SMTP_PASS=fake_mail_password
SMTP_SENDER_NAME=fake_sender
ENABLE_ANONYMOUS_USERS=false

## Phone auth
ENABLE_PHONE_SIGNUP=true
ENABLE_PHONE_AUTOCONFIRM=true

############
# Studio
############

STUDIO_DEFAULT_ORGANIZATION=Default Organization
STUDIO_DEFAULT_PROJECT=Default Project

STUDIO_PORT=3000
SUPABASE_PUBLIC_URL=https://supabase.tail0d6f8e.ts.net

IMGPROXY_ENABLE_WEBP_DETECTION=true

OPENAI_API_KEY=

############
# Functions
############
FUNCTIONS_VERIFY_JWT=false

############
# Logs - Analytics
############

LOGFLARE_PUBLIC_ACCESS_TOKEN={{ op://Local AI Packaged/Supabase/logflare_public_token }}
LOGFLARE_PRIVATE_ACCESS_TOKEN={{ op://Local AI Packaged/Supabase/logflare_private_token }}

DOCKER_SOCKET_LOCATION=/var/run/docker.sock

GOOGLE_PROJECT_ID=GOOGLE_PROJECT_ID
GOOGLE_PROJECT_NUMBER=GOOGLE_PROJECT_NUMBER

############
# Storage (Supabase storage-api v1.48+ requires REGION; file backend uses GLOBAL_S3_BUCKET as dir name)
############
REGION=local
GLOBAL_S3_BUCKET=stub
STORAGE_TENANT_ID=stub
S3_PROTOCOL_ACCESS_KEY_ID=stub
S3_PROTOCOL_ACCESS_KEY_SECRET=stub
IMGPROXY_AUTO_WEBP=true
PG_META_CRYPTO_KEY={{ op://Local AI Packaged/Supabase/pg_meta_crypto_key }}

############
# Ollama - Default local chat model
############
OLLAMA_MODEL=qwen3.5:9b

N8N_HOSTNAME=n8n.tail0d6f8e.ts.net
