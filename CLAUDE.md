# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

This is a self-hosted AI development environment combining n8n, Supabase, Ollama, Open WebUI, Flowise, Qdrant, Neo4j, SearXNG, Langfuse, Caddy, and supporting services. All services share the Docker Compose project name `localai`.

The repository starts services in stages: Supabase is prepared and started first, then the AI services are started after a short initialization delay. Use `start_services.py` for normal startup so the Supabase checkout, environment files, and first-run SearXNG setup are handled consistently.

## Commands

### Initial Setup

```bash
cp .env.example .env
```

Replace placeholder values in `.env` with secure secrets. For local development, the repository's example values are sufficient for non-production-only settings; never use them for a public deployment.

### Start Services

```bash
# CPU, local development
python start_services.py --profile cpu --environment private

# NVIDIA GPU
python start_services.py --profile gpu-nvidia

# AMD GPU (Linux only)
python start_services.py --profile gpu-amd

# Use Ollama installed on the host, such as macOS
python start_services.py --profile none

# Production mode: only expose the Caddy entry points
python start_services.py --profile gpu-nvidia --environment public
```

### Stop and Upgrade Services

```bash
# Stop all services
docker compose -p localai -f docker-compose.yml --profile <profile> down

# Pull newer container images, then start again
docker compose -p localai -f docker-compose.yml --profile <profile> pull
python start_services.py --profile <profile>
```

## Architecture

- `start_services.py` is the main entry point. It checks out the root-pinned Supabase revision, copies `.env` into the Supabase checkout, generates the SearXNG secret, applies first-run handling, starts Supabase, waits, and starts the AI services.
- `docker-compose.yml` defines the main services and includes the Supabase Compose file.
- `docker-compose.override.private.yml` exposes services for local development; the public overrides close non-essential ports and route traffic through Caddy.
- `supabase/` is a sparse checkout created at runtime and must remain at the revision recorded by the root repository.

### Docker Compose Profiles

- `cpu`: CPU-only Ollama
- `gpu-nvidia`: NVIDIA GPU acceleration
- `gpu-amd`: AMD GPU acceleration on Linux
- `none`: no Ollama container; use a host Ollama installation

### Service Connectivity

Services communicate over the Docker network using service names, not `localhost`. For example, n8n connects to `ollama:11434`, Postgres through Supabase is `db`, and Qdrant is `qdrant:6333`. On macOS with host Ollama, use `host.docker.internal:11434` in the n8n configuration.

## Service Endpoints (Private Environment)

| Service | Port | Internal hostname |
|---------|------|-------------------|
| n8n | 5678 | `n8n` |
| Open WebUI | 8080 | `open-webui` |
| Flowise | 3001 | `flowise` |
| Ollama | 11434 | `ollama` |
| Qdrant | 6333 | `qdrant` |
| Neo4j | 7474/7687 | `neo4j` |
| SearXNG | 8080 | `searxng` |
| Supabase API | 8000 | `kong` |
| PostgreSQL | 5432 | `db` |
| Langfuse | 3000 | `langfuse-web` |

## Configuration and Secrets

The recommended local workflow uses the 1Password template:

```bash
./generate-env.sh
./generate-env.sh --check
```

- `.env.tpl` contains the committed `op://...` references.
- `.env` is generated at runtime, is gitignored, and should have mode `600`.
- Manual setup can copy `.env.example` to `.env` and replace placeholders.
- Avoid `@` in `POSTGRES_PASSWORD`, because it can break connection-string parsing.

## Workflows and Tools

- `n8n/backup/workflows/` contains the starter workflows for manual import, including the V1 local RAG workflow, V2 Supabase RAG workflow, and V3 agentic RAG workflow.
- `n8n/backup/credentials/` contains exported credential templates where present.
- `n8n-tool-workflows/` contains reusable Google Docs, Postgres, and Slack tool workflows.
- `flowise/` contains Flowise chatflows and custom tools.
- `n8n_pipe.py` connects Open WebUI to n8n workflows.

The current Compose configuration does not auto-import workflows at container startup. Import the required JSON files from `n8n/backup/workflows/` through the n8n UI.

## Caddy and SearXNG

`Caddyfile` uses environment-variable hostnames such as `N8N_HOSTNAME` and `WEBUI_HOSTNAME` for production routing. Public mode should expose only the intended Caddy entry points; do not expose Ollama or SearXNG publicly without an explicit security review.

On the first run, `start_services.py` temporarily comments out SearXNG's `cap_drop: - ALL` so its configuration can initialize, then restores the security setting on later runs. A commented directive during first-run setup is intentional.

## Troubleshooting Notes

- If Supabase files are missing, remove the runtime `supabase/` checkout and rerun `start_services.py`; it will recreate the pinned revision.
- If local file triggers or Execute Command nodes are needed with n8n v2+, uncomment `NODES_EXCLUDE=[]` in the `x-n8n` environment and restart n8n.
- For container failures, inspect `docker compose -p localai logs <service>` and confirm `.env` contains all required secrets and Supabase storage variables.
