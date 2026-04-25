# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Self-hosted AI platform combining 15+ Docker services into a single stack. Fork/enhancement of n8n's self-hosted-ai-starter-kit by Cole Medin. All services run under the unified Docker Compose project name `localai`.

## Starting and Stopping Services

```bash
# Start (CPU, local dev)
python start_services.py --profile cpu --environment private

# Start with NVIDIA GPU
python start_services.py --profile gpu-nvidia

# Mac with local Ollama (no Docker Ollama)
python start_services.py --profile none

# Production (only exposes ports 80/443 through Caddy)
python start_services.py --profile gpu-nvidia --environment public

# Stop everything
docker compose -p localai -f docker-compose.yml down
```

`start_services.py` handles: Supabase repo cloning (sparse checkout), .env propagation, SearXNG secret key generation, cap_drop workaround for first run, and ordered startup (Supabase first, 10s wait, then AI stack).

## Architecture

Two Docker Compose stacks unified under project `localai`:

**Main stack** (`docker-compose.yml`): n8n, Open WebUI, Flowise, Ollama, Qdrant, Neo4j, SearXNG, Caddy, Langfuse (+ ClickHouse, MinIO, Redis, PostgreSQL)

**Supabase stack** (`supabase/docker/docker-compose.yml`): PostgreSQL, Kong, PostgREST, GoTrue, Studio. Included via `include:` directive. The `supabase/` directory is auto-cloned on first run.

**Override files** control port exposure:
- `docker-compose.override.private.yml` - exposes all ports to localhost (dev)
- `docker-compose.override.public.yml` / `public.supabase.yml` - restricts to Caddy only (prod)

**Ollama profiles**: `cpu`, `gpu-nvidia`, `gpu-amd`, `none` (host Ollama on Mac via `host.docker.internal:11434`)

## Service Endpoints (Local Dev)

| Service | Port | Internal hostname |
|---------|------|-------------------|
| n8n | 5678 | `n8n` |
| Open WebUI | 8080 | `open-webui` |
| Flowise | 3001 | `flowise` |
| Ollama | 11434 | `ollama` |
| Qdrant | 6333 | `qdrant` |
| Neo4j | 7474/7687 | `neo4j` |
| SearXNG | 8080 | `searxng` |
| Supabase API (Kong) | 8000 | `kong` |
| PostgreSQL | 5432 | `db` |
| Langfuse | 3000 | `langfuse-web` |

Service-to-service communication uses internal hostnames (e.g., n8n connects to `ollama:11434`, not `localhost`).

## Configuration & Secrets

Two methods for populating `.env`:

### Method A: 1Password CLI (recommended)

Secrets are stored in the 1Password vault "Local AI Packaged". The `.env.tpl` template contains `{{ op://... }}` references that `generate-env.sh` resolves via `op inject` (Touch ID).

```bash
# Generate .env from 1Password (Touch ID required)
./generate-env.sh

# Verify all op:// references resolve without writing .env
./generate-env.sh --check
```

- `.env.tpl` — committed template with `{{ op://vault/item/field }}` references (safe to share)
- `.env` — generated at runtime, gitignored, permissions 600
- Vault items: `n8n`, `Supabase`, `Neo4j`, `Langfuse` (infrastructure secrets), `Langfuse (Local)` (user account)
- Langfuse API keys (`LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`) and `LANGFUSE_BASE_URL` are included

### Method B: Manual (no 1Password)

Copy `.env.example` to `.env` and replace placeholders manually, or use the inline Python secret generator in the setup guide.

Gotcha: avoid `@` in `POSTGRES_PASSWORD` - causes connection string parsing issues.

## Pre-built Workflows and Tools

- `n8n/backup/workflows/` and `n8n/backup/credentials/` - auto-imported by n8n on startup
- `n8n-tool-workflows/` - reusable n8n tool workflows (Google Docs, Postgres, Slack)
- `flowise/` - custom tools and chatflows for Flowise
- `n8n_pipe.py` - Python pipe connecting Open WebUI to n8n workflows
- `Local_RAG_AI_Agent_n8n_Workflow.json` - main RAG workflow (Ollama + Postgres chat memory + Qdrant)

## Caddy (Reverse Proxy)

`Caddyfile` uses env var templates (`{$N8N_HOSTNAME}`, etc.) for domain routing. Production hostnames configured in `.env`. Custom configs imported from `caddy-addon/*.conf`.

## SearXNG First-Run Behavior

`start_services.py` temporarily comments out `cap_drop: - ALL` in `docker-compose.yml` on first run so uwsgi can initialize. It re-enables the directive on subsequent runs. If the docker-compose.yml shows a commented-out cap_drop line, this is intentional.
