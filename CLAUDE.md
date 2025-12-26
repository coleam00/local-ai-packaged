# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Self-hosted AI Package - A Docker Compose template that bootstraps a local AI and low-code development environment. Combines Ollama (local LLMs), Open WebUI (chat interface), n8n (workflow automation), Supabase (database/auth), and supporting services.

## Starting Services

```bash
# GPU options: cpu, gpu-nvidia, gpu-amd, none
# Environment options: private (default, exposes ports locally), public (only ports 80/443)
python start_services.py --profile gpu-nvidia --environment private
```

The `start_services.py` script:
1. Clones/updates Supabase repo via sparse checkout
2. Copies root `.env` to `supabase/docker/.env`
3. Generates SearXNG secret key
4. Starts Supabase services first, waits 10 seconds, then starts local AI services
5. All services run under Docker Compose project name `localai`

## Upgrading Containers

```bash
docker compose -p localai -f docker-compose.yml --profile <profile> down
docker compose -p localai -f docker-compose.yml --profile <profile> pull
python start_services.py --profile <profile>
```

## Architecture

### Docker Compose Structure
- `docker-compose.yml` - Main services (n8n, Ollama, Open WebUI, Flowise, Qdrant, Neo4j, Caddy, Langfuse, SearXNG, Redis, ClickHouse, MinIO, Postgres)
- `supabase/docker/docker-compose.yml` - Supabase services (included via `include:` directive)
- `docker-compose.override.private.yml` - Exposes ports to localhost (127.0.0.1)
- `docker-compose.override.public.yml` - Closes ports for public deployment
- `docker-compose.override.public.supabase.yml` - Closes Supabase ports for public deployment

### Service Profiles
- `cpu` - Ollama without GPU
- `gpu-nvidia` - Ollama with NVIDIA GPU
- `gpu-amd` - Ollama with AMD GPU (ROCm)
- `none` - No Ollama (use external Ollama instance)

### Key Services and Internal URLs
| Service | Internal URL | Local Port (private) |
|---------|--------------|---------------------|
| n8n | http://n8n:5678 | 5678 |
| Ollama | http://ollama:11434 | 11434 |
| Open WebUI | http://open-webui:8080 | 8080 |
| Flowise | http://flowise:3001 | 3001 |
| Qdrant | http://qdrant:6333 | 6333 |
| Neo4j | bolt://neo4j:7687 | 7474 (browser), 7687 (bolt) |
| Supabase (Kong) | http://kong:8000 | via Caddy |
| Supabase DB | postgresql://postgres:password@db:5432/postgres | 5433 |
| Langfuse | http://langfuse-web:3000 | 3000 |
| SearXNG | http://searxng:8080 | 8081 |

### Caddy Reverse Proxy
- `Caddyfile` configures reverse proxy for all services
- Uses environment variables for hostnames (e.g., `N8N_HOSTNAME`)
- Localhost deployment uses port-based routing (`:8001`, `:8002`, etc.)
- Production uses domain-based routing with automatic Let's Encrypt TLS
- Custom Caddy config can be added in `caddy-addon/*.conf`

### n8n Integration
- `n8n/backup/workflows/` - Pre-loaded workflow templates
- `n8n-tool-workflows/` - Additional workflow examples (Google Docs, Slack, Postgres)
- `n8n_pipe.py` - Open WebUI function to call n8n workflows via webhook
- Shared folder mounted at `/data/shared` inside n8n container

## n8n Workflow Management

After starting services, import the pre-configured RAG workflows:

```bash
python scripts/n8n_import.py import
```

### Available Commands

```bash
# Import workflows from ./n8n/backup/workflows/
python scripts/n8n_import.py import

# Export/backup workflows to ./n8n/backup/workflows/
python scripts/n8n_import.py export

# List workflows in n8n
python scripts/n8n_import.py list

# Import specific workflow file
python scripts/n8n_import.py import --file ./n8n/backup/workflows/V1_Local_RAG_AI_Agent.json

# Custom n8n URL (for remote instances)
python scripts/n8n_import.py import --url http://n8n.example.com:5678
```

Note: After importing workflows, configure credentials (Postgres, Ollama) manually in the n8n UI.

## Environment Configuration

Copy `.env.example` to `.env` and configure:

**Required secrets:**
- `N8N_ENCRYPTION_KEY`, `N8N_USER_MANAGEMENT_JWT_SECRET` - n8n auth
- `POSTGRES_PASSWORD`, `JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY` - Supabase
- `NEO4J_AUTH` - Format: `username/password`
- `CLICKHOUSE_PASSWORD`, `MINIO_ROOT_PASSWORD`, `LANGFUSE_SALT`, `NEXTAUTH_SECRET`, `ENCRYPTION_KEY` - Langfuse

**Production hostnames (uncomment for public deployment):**
- `N8N_HOSTNAME`, `WEBUI_HOSTNAME`, `FLOWISE_HOSTNAME`, `SUPABASE_HOSTNAME`, etc.
- `LETSENCRYPT_EMAIL` - Required for TLS certificates

## Troubleshooting

- **Supabase Pooler restarting**: Check `POOLER_DB_POOL_SIZE=5` in `.env`
- **SearXNG restarting**: Run `chmod 755 searxng` for uwsgi.ini creation
- **Supabase connection issues**: Avoid `@` character in `POSTGRES_PASSWORD`
- **Supabase files missing**: Delete `supabase/` folder and re-run `start_services.py`
- **GPU not detected**: Ensure Docker Desktop has WSL 2 backend (Windows) or NVIDIA Container Toolkit (Linux)
