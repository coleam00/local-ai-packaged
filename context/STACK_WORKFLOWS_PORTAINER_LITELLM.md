# Local AI Stack: Workflows, Portainer, and LiteLLM

Status: aligned with consolidated stack (start_services.py + Caddy). Includes Portainer management and LiteLLM usage (external by default, optional container profile).

## 1) System Workflows (Runbook)

Primary orchestration: start_services.py
- Clones/updates Supabase locally (sparse checkout)
- Copies root .env into supabase/docker/.env
- Prepares RAG schema (copies all-rag-strategies/implementation/sql/schema.sql → supabase/docker/volumes/db/init/02-rag-schema.sql)
- Starts Supabase first, then waits for db readiness via pg_isready
- Generates SearXNG secret on first run; adjusts compose security flags when needed
- Starts the rest of the stack with a chosen profile: cpu, gpu-nvidia, gpu-amd

Common commands
- CPU: python start_services.py --profile cpu
- NVIDIA: python start_services.py --profile gpu-nvidia
- AMD: python start_services.py --profile gpu-amd
- Ingestion (one-shot): docker compose -p localai --profile ingestion up --build rag-ingestion

Reverse proxy (Caddy)
- Hostnames set in .env; defaults are local ports like :8001, :8002, :8009
- RAG API default: RAG_HOSTNAME (e.g., :8009)

## 2) Portainer (Visual Stack Manager)

Purpose
- Visual management for all containers in the stack: logs, health, restarts, volumes, environment, and compose stacks.

Access
- Caddy route: PORTAINER_HOSTNAME (default :8010 in .env.example)
- Example: http://localhost:8010

Compose service (already added)
- Service: portainer (port 9443 inside, reverse-proxied by Caddy)
- Volumes: Docker socket (read/write) + persistent /data

Tips
- Use Portainer to:
  - Check container health and logs (db, rag-api, n8n, etc.)
  - Inspect env vars, mounts, and restart policies
  - Confirm Supabase db readiness and RAG API exposure

## 3) LiteLLM Integration

Modes
- External (default): run LiteLLM on the host at http://host.docker.internal:4000/v1
- Optional container: profile litellm, exposed via Caddy at LITELLM_HOSTNAME (default :8011)

Why centralize through LiteLLM?
- Single master key (LITELLM_MASTER_KEY) for clients
- Unified headers and auth; provider keys live only in the proxy
- Logical model routing and easy swaps

Using LiteLLM (external mode)
- Containers reference: LLM_BASE_URL=http://host.docker.internal:4000/v1
- Clients use: OPENAI_API_KEY set to LITELLM_MASTER_KEY

Using LiteLLM (container mode)
- Start: docker compose --profile litellm up -d litellm
- Access via Caddy: LITELLM_HOSTNAME (e.g., http://localhost:8011)
- Then set LLM_BASE_URL=http://localhost:8011/v1 for clients outside the Docker network

Service-specific examples
- Archon (.env):
  - LLM_BASE_URL=http://host.docker.internal:4000/v1
  - OPENAI_API_KEY=${LITELLM_MASTER_KEY}
- RAG API / Ingestion:
  - OPENAI_API_KEY=${LITELLM_MASTER_KEY}
  - LLM_CHOICE points to your logical model
- Open WebUI:
  - Configure a custom provider pointing to the LiteLLM /v1 base
  - API key: ${LITELLM_MASTER_KEY}
- n8n:
  - OpenAI credentials → Base URL: http://host.docker.internal:4000/v1; Key: ${LITELLM_MASTER_KEY}

Security & headers
- Prefer passing only the LiteLLM master key to clients/services
- Keep provider secrets (OpenAI/Groq/OpenRouter/etc.) in LiteLLM config

## 4) Verification

RAG services
- Health: curl http://localhost:8009/health
- List docs: curl http://localhost:8009/documents
- Search: curl -X POST http://localhost:8009/search -H 'Content-Type: application/json' -d '{"query":"What is in the KB?","limit":5}'

Database
- Tables: docker compose -p localai -f supabase/docker/docker-compose.yml exec db \
  psql -U postgres -d postgres -c "\\dt"
- pgvector: \dx vector

Portainer
- Visit your PORTAINER_HOSTNAME and verify container health and logs

LiteLLM (external)
- Test: curl http://localhost:4000/v1/models -H "Authorization: Bearer ${LITELLM_MASTER_KEY}"

LiteLLM (container)
- Test: curl http://localhost:8011/v1/models -H "Authorization: Bearer ${LITELLM_MASTER_KEY}"

## 5) Troubleshooting

DB not ready
- The script waits using pg_isready; re-run start_services.py
- Use Portainer to inspect db logs and restart only the db service if needed

Schema not initialized
- Remove supabase/docker/volumes/db/init/02-rag-schema.sql and rerun without --skip-schema-init
- Or allow the runtime schema initializer to apply via docker exec psql

Ports in use
- docker compose -p localai down (root compose)
- Also stop the supabase compose if needed

LiteLLM issues
- External mode: confirm host service on port 4000
- Container mode: ensure you used --profile litellm and that LITELLM_HOSTNAME is routable via Caddy

## 6) References
- RAG_STACK_RUNBOOK.md
- EXECUTING_STACK_RUNBOOK.md
- CLAUDE.md
- all-rag-strategies/docs/PORTAINER_SETUP.md
- all-rag-strategies/docs/UNIFIED_GPU_RAG_GUIDE.md
