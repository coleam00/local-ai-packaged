# RAG Stack Runbook (Local AI Packaged)

This runbook consolidates the final, working instructions to launch the complete stack with advanced RAG services, perform ingestion, and verify functionality.

Contents:
- Prerequisites
- Environment file
- Start order and profiles (CPU/GPU)
- Ingestion workflow
- Verifications and health checks
- Troubleshooting
- Service URLs

## 1) Prerequisites
- Docker and Docker Compose
- For NVIDIA GPU profile: latest NVIDIA drivers + nvidia-container-toolkit configured
- For AMD GPU profile: ROCm-capable GPU and compatible driver
- Python 3.11+ installed locally (only if you plan to run some tools outside containers)

## 2) Environment
Copy your root .env with all required values. At minimum:

- POSTGRES_PASSWORD
- OPENAI_API_KEY (or your chosen provider keys)
- LLM_CHOICE (e.g., gpt-4o-mini, or use Ollama in future)
- EMBEDDING_MODEL (e.g., text-embedding-3-small)
- MINIO_ROOT_PASSWORD, CLICKHOUSE_PASSWORD (for Langfuse)
- Secrets for n8n and others as needed (see README.md)

Optional hostnames for Caddy reverse proxy:
- N8N_HOSTNAME, WEBUI_HOSTNAME, FLOWISE_HOSTNAME, SUPABASE_HOSTNAME, SEARXNG_HOSTNAME, LANGFUSE_HOSTNAME, NEO4J_HOSTNAME
- RAG_HOSTNAME (default :8009)

## 3) Startup (with automatic RAG schema init)
The script start_services.py will:
- Clone and configure Supabase (once)
- Prepare and apply the RAG schema (supabase/docker/volumes/db/init/02-rag-schema.sql)
- Start Supabase
- Wait for DB to be ready
- Start all app services

Examples:

CPU profile:
- python start_services.py --profile cpu

NVIDIA GPU profile:
- python start_services.py --profile gpu-nvidia

AMD GPU profile:
- python start_services.py --profile gpu-amd

Skip schema init (if already applied):
- python start_services.py --profile cpu --skip-schema-init

## 4) Ingestion
Add documents to: all-rag-strategies/implementation/documents

Run ingestion service (one-shot) using the ingestion profile:
- docker compose -p localai --profile ingestion up --build rag-ingestion

This will chunk, embed, and write to Supabase Postgres (db) using DATABASE_URL.

## 5) Verifications
- Rag API health: curl http://localhost:8009/health (or your RAG_HOSTNAME)
- List docs: curl http://localhost:8009/documents
- Simple search: curl -X POST http://localhost:8009/search -H 'Content-Type: application/json' -d '{"query":"What is in the KB?","limit":5}'

DB schema check (inside Supabase db container):
- docker compose -p localai -f supabase/docker/docker-compose.yml exec db psql -U postgres -d postgres -c "\dt"

## 6) Service URLs (defaults via Caddy)
- Open WebUI: http://localhost:8002
- n8n: http://localhost:8001
- Supabase Studio: http://localhost:8005
- Langfuse: http://localhost:8007
- RAG API: http://localhost:8009

## 7) Troubleshooting
- If DB not ready: the script waits using pg_isready; re-run start_services.py
- If schema missing: remove supabase/docker/volumes/db/init/02-rag-schema.sql and rerun without --skip-schema-init, or run runtime initializer in script
- GPU (NVIDIA): ensure nvidia-smi works and Docker has nvidia runtime; see all-rag-strategies/docs/UNIFIED_GPU_RAG_GUIDE.md
- Ports in use: stop existing containers with `docker compose -p localai down` (both root compose and supabase compose if needed)
- RAG API import errors: ensure api.py exists in all-rag-strategies/implementation and image rebuilt

## 8) Notes
- RAG Agent (CLI) is also available via `rag-agent` service; the HTTP API is provided by `rag-api`
- Caddy forwards RAG_HOSTNAME to rag-api:8000
- Ingestion is intentionally separated under an on-demand profile

For deeper docs:
- all-rag-strategies/docs/RAG-Implementation-GUIDE-1.md
- all-rag-strategies/docs/integration_guide_claude_conversation.md
- all-rag-strategies/docs/UNIFIED_GPU_RAG_GUIDE.md
- rag-integration-guide.md
