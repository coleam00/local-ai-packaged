# Setup Guide Design Spec

**Date:** 2026-04-24
**Target:** Mac with native Ollama (`--profile none --environment private`)
**Scope:** Core services + Langfuse + Neo4j

## Deliverable

Self-contained interactive HTML file at `docs/setup-guide.html`.

## Design Decisions

1. **Phased accordion layout** with top-level progress bar and per-phase mini-progress
2. **Step badges**: `AUTOMATED` (green) / `USER ACTION` (blue)
3. **localStorage persistence** for checkbox state (survives page refresh)
4. **Copy-to-clipboard** on every command block
5. **"Open in Browser" buttons** on user-action steps that auto-open the correct localhost URL
6. **Combined setup script** — floating button copies all automated steps as a single bash script
7. **Dark theme** — modern card-based layout, accessible contrast

## Phases & Steps

### Phase 1: Prerequisites (4 steps)

| # | Step | Type | Command / Action |
|---|------|------|-----------------|
| 1.1 | Verify Docker Desktop installed | AUTO/USER | `docker --version`; if missing → open docker.com/download |
| 1.2 | Start Docker Desktop | AUTO | `open -a Docker`; poll `docker info` until ready |
| 1.3 | Verify Python 3 | AUTO | `python3 --version` |
| 1.4 | Verify Git | AUTO | `git --version` |

### Phase 2: Clone & Configure (5 steps)

| # | Step | Type | Command / Action |
|---|------|------|-----------------|
| 2.1 | Clone repository | AUTO | `git clone -b stable https://github.com/coleam00/local-ai-packaged.git ~/local-ai-packaged` |
| 2.2 | Create .env from template | AUTO | `cp .env.example .env` |
| 2.3 | Generate all secrets | AUTO | Python script generates: N8N keys, JWT_SECRET, matching ANON_KEY/SERVICE_ROLE_KEY (HS256 JWTs), POSTGRES_PASSWORD (no @), NEO4J_AUTH, Langfuse secrets. Uses `openssl rand -hex 32` + Python stdlib JWT generation |
| 2.4 | Set Langfuse NEXTAUTH_URL | AUTO | `sed` to set `NEXTAUTH_URL=http://localhost:3000` |
| 2.5 | Review .env | USER | Open in editor; verify no `[required]` placeholders remain |

### Phase 3: Install Ollama & Models (3 steps)

| # | Step | Type | Command / Action |
|---|------|------|-----------------|
| 3.1 | Install Ollama | AUTO | `brew install ollama` |
| 3.2 | Start Ollama | AUTO | `ollama serve &`; verify `curl -s http://localhost:11434` |
| 3.3 | Pull models | AUTO | `ollama pull qwen2.5:7b-instruct-q4_K_M && ollama pull nomic-embed-text` |

### Phase 4: Launch Stack (3 steps)

| # | Step | Type | Command / Action |
|---|------|------|-----------------|
| 4.1 | Run start_services.py | AUTO | `cd ~/local-ai-packaged && python3 start_services.py --profile none --environment private` |
| 4.2 | Wait for healthy containers | AUTO | Poll `docker compose -p localai ps` until key services are running (up to 120s) |
| 4.3 | Verify all services | AUTO | `docker compose -p localai ps --format table` |

### Phase 5: Service Setup & Verify (6 steps)

| # | Step | Type | URL | Instructions |
|---|------|------|-----|-------------|
| 5.1 | Create n8n account | USER | http://localhost:5678 | Set up owner account (email + password). Local only, not cloud. |
| 5.2 | Create Open WebUI account | USER | http://localhost:8080 | Create admin account. Go to Settings → Connections → set Ollama URL to `http://host.docker.internal:11434` |
| 5.3 | Verify Qdrant | AUTO | http://localhost:6333/dashboard | curl health check + open dashboard |
| 5.4 | Set up Neo4j | USER | http://localhost:7474 | Login with neo4j / password from NEO4J_AUTH. Change password if prompted. |
| 5.5 | Set up Langfuse | USER | http://localhost:3000 | Create account → Create project → Note API keys for n8n integration |
| 5.6 | Test end-to-end | USER | http://localhost:8080 | In Open WebUI, select qwen2.5 model and send a test message |

## Port Reference (Private Environment)

| Service | Port | URL |
|---------|------|-----|
| n8n | 5678 | http://localhost:5678 |
| Open WebUI | 8080 | http://localhost:8080 |
| Flowise | 3001 | http://localhost:3001 |
| Qdrant | 6333 | http://localhost:6333 |
| Neo4j Browser | 7474 | http://localhost:7474 |
| Langfuse | 3000 | http://localhost:3000 |
| SearXNG | 8081 | http://localhost:8081 |
| Supabase API | 8000 | http://localhost:8000 |

## Combined Script Strategy

All automated steps concatenated into a bash script with:
- `set -e` for fail-fast
- Echo headers between phases
- Python-based JWT generation for Supabase keys (stdlib only)
- Retry loops for health checks
- Color-coded terminal output
