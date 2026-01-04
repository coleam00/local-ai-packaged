# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Docker Compose-based self-hosted AI development environment combining n8n (low-code automation), Supabase (database/auth), Ollama (local LLMs), Open WebUI (chat interface), Flowise (AI agent builder), Qdrant (vector store), Neo4j (graph database), SearXNG (search), Langfuse (observability), and Caddy (reverse proxy).

## Commands

### Start Services
```bash
# GPU (Nvidia)
python start_services.py --profile gpu-nvidia

# GPU (AMD - Linux only)
python start_services.py --profile gpu-amd

# CPU only
python start_services.py --profile cpu

# No Ollama (when running locally on Mac)
python start_services.py --profile none

# Production deployment (closes non-essential ports)
python start_services.py --profile gpu-nvidia --environment public
```

### Stop Services
```bash
docker compose -p localai -f docker-compose.yml --profile <profile> down
```

### Upgrade Containers
```bash
docker compose -p localai -f docker-compose.yml --profile <profile> down
docker compose -p localai -f docker-compose.yml --profile <profile> pull
python start_services.py --profile <profile>
```

## Architecture

- **start_services.py**: Main entry point - clones Supabase repo, copies .env, generates SearXNG secret, starts Supabase first, waits 10s, then starts local AI services
- **docker-compose.yml**: Main compose file with all local AI services. Includes Supabase compose file. Uses YAML anchors for service templates (`x-n8n`, `x-ollama`, `x-init-ollama`)
- **docker-compose.override.*.yml**: Environment-specific overrides (private exposes ports, public closes them)
- **supabase/**: Sparse checkout of Supabase Docker config (cloned at runtime)

### Docker Compose Profiles
- `cpu`: Ollama without GPU
- `gpu-nvidia`: Ollama with NVIDIA GPU
- `gpu-amd`: Ollama with AMD GPU (ROCm)
- `none`: No Ollama container

### Service URLs (local/private)
- n8n: http://localhost:5678 (via Caddy :8001)
- Open WebUI: http://localhost:3000 (via Caddy :8002)
- Flowise: (via Caddy :8003)
- Ollama: (via Caddy :8004)
- Supabase: (via Caddy :8005)
- SearXNG: (via Caddy :8006)
- Langfuse: (via Caddy :8007)
- Neo4j: (via Caddy :8008)

### Key Configuration
- All services share project name `localai` for unified Docker Desktop view
- n8n connects to Supabase Postgres at host `db`
- Ollama available at `http://ollama:11434` inside Docker network
- Qdrant at `http://qdrant:6333`
- Shared folder mounted at `/data/shared` in n8n container

## Workflow Files
- `n8n/backup/workflows/`: n8n workflows for manual import (V1-V3 RAG agents)
- `flowise/`: Flowise chatflows and custom tools
- `n8n-tool-workflows/`: n8n tool workflows for Flowise integration
- `n8n_pipe.py`: Open WebUI function for n8n integration
