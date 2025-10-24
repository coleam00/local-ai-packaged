# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **self-hosted AI development environment** that combines multiple AI services into a unified Docker Compose stack. The project orchestrates n8n (workflow automation), Ollama (local LLMs), Open WebUI, Flowise, Supabase (database/vector store), and supporting services like Neo4j, SearXNG, Qdrant, and Langfuse for a complete local AI development platform.

**Key Architecture Principle**: This is a multi-service orchestration project where services are started in stages (Supabase first, then AI services) and share a unified Docker Compose project namespace (`localai`) for cohesive management.

## Essential Commands

### Initial Setup

```bash
# 1. Create environment file from template
cp .env.example .env

# 2. Generate required secrets for .env
# For N8N_ENCRYPTION_KEY, N8N_USER_MANAGEMENT_JWT_SECRET, ENCRYPTION_KEY:
openssl rand -hex 32

# For Supabase JWT tokens (ANON_KEY, SERVICE_ROLE_KEY):
# Follow: https://supabase.com/docs/guides/self-hosting/docker#generate-api-keys

# 3. Edit .env and replace all placeholder values
# Required: POSTGRES_PASSWORD, JWT_SECRET, NEO4J_AUTH, DASHBOARD_PASSWORD
# For Langfuse: CLICKHOUSE_PASSWORD, MINIO_ROOT_PASSWORD, LANGFUSE_SALT, NEXTAUTH_SECRET
```

### Starting Services

**Mac/Apple Silicon (M1+) - Recommended Approach:**
```bash
# Option 1: Install Ollama locally for better performance (recommended)
brew install ollama
ollama serve  # Run in separate terminal
python start_services.py --profile none --environment private

# Option 2: Run everything in Docker (slower inference)
python start_services.py --profile cpu --environment private
```

**GPU Users:**
```bash
# NVIDIA GPU
python start_services.py --profile gpu-nvidia --environment private

# AMD GPU (Linux only)
python start_services.py --profile gpu-amd --environment private
```

**Environment Options:**
- `--environment private`: Localhost-only access (127.0.0.1), all ports exposed locally (default)
- `--environment public`: Production mode, only ports 80/443 exposed, requires Caddy hostnames in .env

### Service Access (Private Environment)

After services start successfully:
- **n8n**: http://localhost:5678 - Workflow automation
- **Open WebUI**: http://localhost:8080 - Chat interface
- **Flowise**: http://localhost:3001 - Visual AI builder
- **Supabase Studio**: http://localhost:8000 - Database dashboard
- **Qdrant**: http://localhost:6333 - Vector store
- **Neo4j Browser**: http://localhost:7474 - Graph database
- **Langfuse**: http://localhost:3000 - LLM observability

### Managing Services

```bash
# Stop all services
docker compose -p localai down

# Stop and remove volumes (clean slate)
docker compose -p localai down -v

# View logs
docker compose -p localai logs -f [service_name]

# Restart specific service
docker compose -p localai restart [service_name]

# List running containers
docker ps --filter "name=localai"
```

## Critical Architecture Details

### Service Startup Sequence

The `start_services.py` script orchestrates a **two-phase startup**:

1. **Phase 1**: Clones/updates Supabase repo, prepares environment, starts Supabase services
2. **10-second delay**: Allows Supabase to initialize database
3. **Phase 2**: Starts AI services (n8n, Ollama, Open WebUI, Flowise, etc.)

**Why this matters**: Direct `docker compose up` will fail. Always use `start_services.py`.

### SearXNG First-Run Handling

The startup script automatically handles a SearXNG security constraint:

- **First run**: Temporarily comments out `cap_drop: - ALL` in docker-compose.yml (required for initial setup)
- **Subsequent runs**: Re-enables `cap_drop: - ALL` for security
- Secret key auto-generated from `searxng/settings-base.yml` → `searxng/settings.yml`

**Manual SearXNG secret generation** (if needed):
```bash
# macOS
sed -i '' "s|ultrasecretkey|$(openssl rand -hex 32)|g" searxng/settings.yml

# Linux
sed -i "s|ultrasecretkey|$(openssl rand -hex 32)|g" searxng/settings.yml
```

### Docker Compose Structure

**Unified project namespace**: All services use `-p localai` to appear together in Docker Desktop.

**File hierarchy**:
- `docker-compose.yml`: Main service definitions, includes Supabase via `include:`
- `docker-compose.override.private.yml`: Localhost port bindings (127.0.0.1)
- `docker-compose.override.public.yml`: Production mode (ports closed except 80/443)
- `docker-compose.override.public.supabase.yml`: Supabase-specific public overrides

**Profiles** (GPU selection):
- `cpu`: CPU-only Ollama (x-ollama anchor + cpu profile service)
- `gpu-nvidia`: NVIDIA GPU acceleration
- `gpu-amd`: AMD GPU (Linux only)
- `none`: No Ollama container (use local Ollama installation)

### n8n Workflow Integration

**Auto-imported workflows on startup**:
- `n8n-import` container runs once, imports credentials and workflows from `n8n/backup/`
- Pre-configured workflows: Local RAG AI Agent (V1, V2 with Supabase, V3 Agentic)
- Tool workflows: Google Docs, Slack, Postgres table queries

**n8n ↔ Open WebUI integration**:
- `n8n_pipe.py`: Open WebUI pipe function that calls n8n webhooks
- Enables chat interface to trigger n8n workflows via bearer token auth
- Configure in Open WebUI: Settings → Functions → Add n8n pipe

**Mac users running local Ollama**: Update `docker-compose.yml`:
```yaml
x-n8n: &service-n8n
  environment:
    - OLLAMA_HOST=host.docker.internal:11434
```
Also update n8n credential: http://localhost:5678/home/credentials → "Local Ollama service" → Base URL: `http://host.docker.internal:11434/`

### Flowise Integration

**Pre-configured templates**:
- `flowise/Web Search + n8n Agent Chatflow.json`: Main chatflow combining search + n8n tools
- Custom tools (JSON configs): `create_google_doc`, `get_postgres_tables`, `summarize_slack_conversation`, `send_slack_message_through_n8n`

**Import process**: Upload JSON files via Flowise UI (Flows → Import)

### Volume Persistence

**Persistent data locations**:
- **n8n**: `n8n_storage` volume + `./n8n/backup` bind mount
- **Ollama models**: `ollama_storage` volume (~several GB per model)
- **Supabase/Postgres**: `supabase/docker/volumes/` (managed by Supabase compose)
- **Neo4j**: `./neo4j/{data,logs,config,plugins}` bind mounts
- **Qdrant**: `qdrant_storage` volume
- **Shared data**: `./shared` bind mount (accessible across services)

**Initial model pull**: `x-init-ollama` service auto-downloads:
- `qwen2.5:7b-instruct-q4_K_M` (default LLM, ~4.4GB)
- `nomic-embed-text` (embeddings model)

## Important Configuration Notes

### Environment Variable Requirements

**Critical secrets** (must change before production):
1. `N8N_ENCRYPTION_KEY`, `N8N_USER_MANAGEMENT_JWT_SECRET`: n8n security (32-char hex)
2. `POSTGRES_PASSWORD`: Supabase database password (avoid special chars or percent-encode)
3. `JWT_SECRET`: Supabase JWT signing (min 32 chars)
4. `ANON_KEY`, `SERVICE_ROLE_KEY`: Supabase API keys (generate via Supabase docs)
5. `NEO4J_AUTH`: Format `username/password`
6. `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD`: Supabase Studio access

**Production-only** (commented by default):
- Caddy hostname variables: `N8N_HOSTNAME`, `WEBUI_HOSTNAME`, etc.
- `LETSENCRYPT_EMAIL`: Required for SSL certificates

**Special note on POOLER_TENANT_ID**: Required since June 2024 Supabase update. Default: Any numeric value (e.g., `1000`).

### Service Dependencies

**Database requirements**:
- n8n requires Postgres (provided by Supabase)
- Langfuse requires Postgres + ClickHouse + MinIO (all included)

**Network connectivity**:
- Services communicate via Docker network (no localhost needed)
- Exception: Mac users with local Ollama use `host.docker.internal:11434`

### Caddy Reverse Proxy

**Default behavior** (no hostnames set): Direct localhost URLs with original ports

**Production setup** (hostnames configured in .env):
- Automatic HTTPS via Let's Encrypt
- Custom domains for each service
- Port 80/443 only (internal ports closed)

**Note**: Ollama and SearXNG aren't secured by default - consider not exposing publicly.

## Troubleshooting

### Service won't start
1. Check `.env` exists and has all required secrets
2. Verify Docker daemon is running
3. Check logs: `docker compose -p localai logs [service_name]`
4. For Supabase issues: Ensure 10-second delay completed before AI services start

### Ollama connection issues (n8n/Flowise)
- Mac local Ollama: Verify `OLLAMA_HOST=host.docker.internal:11434` in compose file and n8n credentials
- Container Ollama: Check `docker logs ollama`
- Model not found: Wait for `ollama-pull-llama` init container to complete

### SearXNG cap_drop error
- First run: Script should auto-comment `cap_drop: - ALL`
- If manual fix needed: Comment line in `docker-compose.yml`, start services, then uncomment

### Port conflicts
- Private mode: Ensure ports 5678, 8080, 3001, 6333, 7474 aren't in use
- Check: `lsof -i :[port]` or `netstat -an | grep [port]`

### Reset everything
```bash
docker compose -p localai down -v
rm -rf supabase/docker/volumes/ neo4j/data/ neo4j/logs/
# Re-run start_services.py
```

## Development Workflow

### Adding new n8n workflows
1. Create workflow in n8n UI (localhost:5678)
2. Export via n8n: Workflows → ... → Download
3. Save to `n8n/backup/workflows/[name].json`
4. On next startup, `n8n-import` container auto-imports

### Adding Flowise chatflows
1. Create in Flowise UI (localhost:3001)
2. Export chatflow (JSON)
3. Save to `flowise/[name].json` for documentation
4. Import manually via Flowise UI as needed

### Modifying service configurations
- **Port changes**: Edit override files (`.override.private.yml` or `.override.public.yml`)
- **Environment variables**: Update `docker-compose.yml` service definitions
- **Volume mounts**: Add to service `volumes:` section
- Apply: `docker compose -p localai up -d [service]` (recreates container)

### Testing with different LLM models
```bash
# Connect to Ollama container (or local instance)
docker exec -it ollama ollama pull [model-name]

# Or via local Ollama
ollama pull [model-name]

# Update n8n/Flowise to use new model via UI
```

## Repository Structure

```
.
├── start_services.py           # Main orchestration script
├── docker-compose.yml          # Core service definitions
├── docker-compose.override.*   # Environment-specific overrides
├── .env.example                # Environment template
├── Caddyfile                   # Reverse proxy configuration
├── n8n_pipe.py                 # Open WebUI ↔ n8n integration
├── n8n/
│   └── backup/                 # Auto-imported workflows & credentials
├── n8n-tool-workflows/         # Example tool workflows (Slack, GDocs, Postgres)
├── flowise/                    # Chatflow templates & custom tools
├── searxng/
│   ├── settings-base.yml       # SearXNG template
│   └── settings.yml            # Generated on first run (gitignored)
├── neo4j/                      # Neo4j data/config (gitignored)
├── shared/                     # Cross-service shared files (gitignored)
└── supabase/                   # Cloned on first run (gitignored)
```

## External Resources

- **Community forum**: https://thinktank.ottomator.ai/c/local-ai/18
- **Project board**: https://github.com/users/coleam00/projects/2/views/1
- **Original n8n starter**: https://github.com/n8n-io/self-hosted-ai-starter-kit
- **n8n Open WebUI pipe**: https://openwebui.com/f/coleam/n8n_pipe/
- **Supabase self-hosting guide**: https://supabase.com/docs/guides/self-hosting/docker
