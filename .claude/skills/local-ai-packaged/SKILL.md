---
name: local-ai-packaged
description: Use when working in the local-ai-packaged repo - starting/stopping the Docker stack, configuring secrets via 1Password, choosing CPU/GPU profiles, building n8n workflows or Flowise chatflows, wiring Ollama/Qdrant/Supabase/Neo4j/SearXNG/Langfuse together, integrating Open WebUI with n8n via n8n_pipe.py, configuring Caddy hostnames, or debugging Supabase init failures, Postgres WAL corruption, port conflicts, orphan docker-proxy processes, SearXNG cap_drop errors, supabase-storage REGION-missing, n8n-import migration permission denied, Time Machine duplicate-suffix corruption, or Obsidian folder-index pollution.
---

# local-ai-packaged

## Overview

A self-hosted AI stack: 15+ Docker services unified under the `localai` Compose project, orchestrated by `start_services.py`. Bundles n8n (automation), Open WebUI (chat), Flowise (visual agent builder), Ollama (local LLMs), Qdrant + Neo4j + Supabase/Postgres (memory/RAG), SearXNG (private web search), Langfuse (LLM observability), and Caddy (reverse proxy + TLS).

**Two stacks, one project name**: the main `docker-compose.yml` and `supabase/docker/docker-compose.yml` are both run under `-p localai` so they appear as one in Docker.

## When to Use

- Starting/stopping the stack (`start_services.py`)
- Adding or modifying services in `docker-compose.yml`
- Generating `.env` from 1Password (`generate-env.sh`)
- Choosing a profile (`cpu`, `gpu-nvidia`, `gpu-amd`, `none`) or environment (`private`, `public`)
- Wiring n8n nodes to Ollama / Qdrant / Postgres / Supabase / Neo4j
- Connecting Open WebUI to an n8n workflow via `n8n_pipe.py`
- Debugging: Supabase DB won't start, port already in use, container restart loop, Caddy 502, `cap_drop` errors on SearXNG, `Region is missing` from supabase-storage, n8n-import migration `Permission denied`, Time Machine `<file> 2` duplicates, Obsidian Folder Index `.md` pollution

**Don't use** for unrelated Docker projects on the same host.

## Service Map (Private / Local Dev)

| Service | Host port | Internal hostname:port | Purpose |
|---|---|---|---|
| n8n | 5678 | `n8n:5678` | Workflow automation, AI agents |
| Open WebUI | 8080 | `open-webui:8080` | ChatGPT-style UI (NOT 3000 — README is stale) |
| Flowise | 3001 | `flowise:3001` | Visual agent / chatflow builder |
| Ollama | 11434 | `ollama:11434` | Local LLM runtime (CPU / GPU profiles only) |
| Qdrant | 6333, 6334 | `qdrant:6333` | Vector store |
| Neo4j browser | 7474 | `neo4j:7474` | Knowledge graph UI |
| Neo4j bolt | 7687 | `neo4j:7687` | Driver protocol |
| SearXNG | 8081 | `searxng:8080` | Private web meta-search |
| Supabase API (Kong) | 8000 | `kong:8000` | REST/GraphQL/auth gateway |
| Supabase Studio | via Kong | `studio:3000` | Supabase dashboard (proxied) |
| Supabase Postgres | n/a (internal only) | `db:5432` | Supabase's Postgres |
| Langfuse Web | 3000 | `langfuse-web:3000` | LLM trace UI |
| Langfuse Worker | 3030 | `langfuse-worker:3030` | Trace ingestion |
| Langfuse Postgres | 5433 | `postgres:5432` | Separate from Supabase DB |
| ClickHouse | 8123, 9000, 9009 | `clickhouse:8123` | Langfuse analytics store |
| MinIO API/console | 9010, 9011 | `minio:9000` | S3-compatible storage for Langfuse |
| Redis (Valkey) | 6379 | `redis:6379` | Langfuse queue |
| Caddy | 80, 443 | `caddy` | Reverse proxy / Let's Encrypt |

In **public** mode (`--environment public`), only ports 80 and 443 are exposed — everything else is reachable only through Caddy hostnames in `.env`.

## Quick Reference

### Start / stop

```bash
# CPU (Mac, no GPU passthrough on Apple Silicon)
python3 start_services.py --profile cpu --environment private

# Mac with host-side Ollama (faster on Apple Silicon GPU)
python3 start_services.py --profile none
# In n8n credentials, set Ollama base URL: http://host.docker.internal:11434/

# NVIDIA GPU
python3 start_services.py --profile gpu-nvidia

# Production
python3 start_services.py --profile gpu-nvidia --environment public

# Stop everything
docker compose -p localai -f docker-compose.yml down

# Pull latest images then restart
docker compose -p localai -f docker-compose.yml --profile cpu pull
python3 start_services.py --profile cpu
```

### Inspect

```bash
docker compose -p localai ps
docker logs --tail 50 supabase-db
docker exec -it supabase-db psql -U supabase_admin -d postgres
docker exec -it ollama ollama list
```

`start_services.py` always: clones Supabase sparsely when absent and otherwise keeps it at the root repository's pinned revision, copies `.env` into `supabase/docker/.env`, generates the SearXNG secret if missing, handles the SearXNG `cap_drop` first-run workaround, brings down old containers, starts Supabase first, sleeps 10s, then starts the AI stack.

## Configuration

### Secrets — 1Password (preferred)

```bash
./generate-env.sh --check    # Verify all op:// references resolve
./generate-env.sh            # Generate .env with Touch ID
```

Reads `.env.tpl` (committed, contains `op://Local AI Packaged/...` references) and writes `.env` (gitignored, 600 perms). Vault items: `n8n`, `Supabase`, `Neo4j`, `Langfuse`, plus `Langfuse (Local)` for the user account.

### Secrets — Manual

Copy `.env.example` → `.env`, fill in random values for: `N8N_ENCRYPTION_KEY`, `N8N_USER_MANAGEMENT_JWT_SECRET`, `POSTGRES_PASSWORD`, `JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY`, `DASHBOARD_USERNAME/PASSWORD`, `POOLER_TENANT_ID`, `NEO4J_AUTH`, `CLICKHOUSE_PASSWORD`, `MINIO_ROOT_PASSWORD`, `LANGFUSE_SALT`, `NEXTAUTH_SECRET`, `ENCRYPTION_KEY`. Generate Supabase JWTs from `JWT_SECRET` via Supabase's JWT generator.

**Hard rule**: no `@` in `POSTGRES_PASSWORD`. It breaks the Supabase auth/storage connection strings (Kong receives requests but downstream services error). Other special chars may also break — stick to alphanumerics.

### Required env vars not in upstream `.env.example`

Newer Supabase images break startup unless these are set. Add to `.env` (and `.env.tpl`):

```bash
REGION=local                    # Supabase storage v1.48+ S3VectorsClient requires this
GLOBAL_S3_BUCKET=stub           # used as on-disk dir name when STORAGE_BACKEND=file
STORAGE_TENANT_ID=stub
S3_PROTOCOL_ACCESS_KEY_ID=stub
S3_PROTOCOL_ACCESS_KEY_SECRET=stub
IMGPROXY_AUTO_WEBP=true
PG_META_CRYPTO_KEY=<32-hex-chars>   # supabase-meta won't start without it
```

### Profiles

| Profile | Effect |
|---|---|
| `cpu` | Adds `ollama-cpu` + `ollama-pull-llama-cpu` (auto-pulls `${OLLAMA_MODEL:-qwen3.5:9b}` and `nomic-embed-text`) |
| `gpu-nvidia` | NVIDIA passthrough (requires NVIDIA Container Toolkit) |
| `gpu-amd` | ROCm image |
| `none` | No Ollama container — assumes host-side `ollama serve` (Mac) |

### Environments

- `private` — applies `docker-compose.override.private.yml`, exposing every service on `127.0.0.1:<port>` for local dev
- `public` — applies `docker-compose.override.public.yml` + `.public.supabase.yml`, exposing only Caddy (80/443); all hostnames must be set in `.env` and DNS A-records pointed at the host

### Caddy hostnames

`Caddyfile` reads `{$N8N_HOSTNAME}`, `{$WEBUI_HOSTNAME}`, `{$FLOWISE_HOSTNAME}`, `{$LANGFUSE_HOSTNAME}`, `{$SUPABASE_HOSTNAME}`, `{$NEO4J_HOSTNAME}` from `.env`. Empty/unset means no proxy block. SearXNG and Ollama Caddy blocks are commented out by default. Custom site configs in `caddy-addon/*.conf` are auto-imported.

## Pre-built Workflows and Tools

| Path | What |
|---|---|
| `n8n/backup/workflows/V1_Local_RAG_AI_Agent.json` | Original RAG agent (Ollama + Postgres memory + Qdrant) |
| `n8n/backup/workflows/V2_Local_Supabase_RAG_AI_Agent.json` | RAG using Supabase Postgres + pgvector |
| `n8n/backup/workflows/V3_Local_Agentic_RAG_AI_Agent.json` | Multi-step agentic RAG |
| `n8n/backup/credentials/` | **Must exist** — `n8n-import` errors immediately if missing |
| `n8n-tool-workflows/*.json` | Reusable sub-workflows (Google Doc create, Postgres tables, Slack post/summarize) |
| `flowise/*.json` | Flowise custom tools + a "Web Search + n8n Agent" chatflow |
| `n8n_pipe.py` | Open WebUI Pipe Function bridging chat → n8n webhook |

`n8n-import` runs once on `up`, importing everything from `n8n/backup/workflows/` and `n8n/backup/credentials/` into the n8n instance, then exits 0.

## Common Workflows

### 1. Build a local RAG agent

1. Open n8n at http://localhost:5678 and complete the local-only signup
2. Open n8n's **Workflows** view and select the imported
   `V1_Local_RAG_AI_Agent.json` workflow as the baseline. V2 and V3 are also
   imported from `n8n/backup/workflows/`; workflow URL IDs are instance-specific,
   so do not rely on a hard-coded `/workflow/...` URL.
3. Create credentials inside n8n:
   - **Ollama** — base URL `http://ollama:11434` (or `http://host.docker.internal:11434/` if `--profile none`)
   - **Postgres (Supabase)** — Host `db`, port `5432`, user/password/db from `.env`
   - **Qdrant** — URL `http://qdrant:6333`, API key any string (auth disabled locally)
4. Test workflow once. Toggle **Active**, copy the **Production webhook URL**.

### 2. Wire Open WebUI to an n8n agent

1. Open WebUI at http://localhost:8080, complete local signup
2. Workspace → Functions → Add Function → paste contents of `n8n_pipe.py`
3. Open the function's gear icon, set `n8n_url` to the production webhook URL from step 1, set `n8n_bearer_token` if your webhook requires auth
4. Toggle the function on — it appears in the model dropdown as "N8N Pipe"

### 3. Use SearXNG from n8n / Flowise

Internal endpoint: `http://searxng:8080/search?q=<query>&format=json`. The Flowise file `flowise/Web Search + n8n Agent Chatflow.json` shows a working pattern.

### 4. Trace LLM calls with Langfuse

- Langfuse UI: http://localhost:3000 — use credentials from `Langfuse (Local)` vault item
- In n8n, the Langfuse credentials node uses `LANGFUSE_SECRET_KEY` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_BASE_URL` (already in `.env.tpl`). Internal base URL: `http://langfuse-web:3000`.

### 5. Access local files from n8n

`./shared/` on the host is mounted to `/data/shared` inside the n8n container. Use that path in Read/Write Files, Local File Trigger, and Execute Command nodes.

### 6. Use Docker Desktop's MCP Toolkit from n8n

n8n's `MCP Client Tool` node can plug into the Docker Desktop MCP Toolkit gateway, exposing every MCP server in your active Docker profile (context7, fetch, github-official, hugging-face, perplexity-ask, sequentialthinking, git, obsidian, dockerhub, …) to any AI Agent.

**One-time setup:**

1. Start the gateway with a stable token (foreground; keep terminal open):

   ```bash
   ./scripts/docker-mcp-gateway.sh             # default port 8811, profile "default"
   ./scripts/docker-mcp-gateway.sh --port 9000  # custom port
   ```

   The script writes a stable bearer token to `~/.docker/mcp-gateway-token` (chmod 600). Same token across restarts.

2. Confirm reachability from inside the n8n container:

   ```bash
   docker exec n8n wget -qO- \
     --header="Authorization: Bearer $(cat ~/.docker/mcp-gateway-token)" \
     --header='Accept: application/json, text/event-stream' \
     --header='Content-Type: application/json' \
     --post-data='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","clientInfo":{"name":"test","version":"1"},"capabilities":{}}}' \
     http://host.docker.internal:8811/mcp
   ```

   You should get an `event: message` SSE response with `serverInfo` and `capabilities`.

3. Import the demo workflow `n8n/Docker_MCP_Toolkit_Demo.json` into n8n (Workflow menu → Import from File). **Do not** try to create it through the n8n-mcp MCP server's `n8n_create_workflow` tool — the catalog ships v2.22.17 which crashes with `Cannot read properties of undefined (reading '_zod')` on every input. Updating the host-side npm package doesn't fix it; the bug is in the catalog container image.

4. In the imported workflow, create two credentials:
   - **Ollama** on the `Ollama Chat Model` node — base URL `http://ollama:11434` (or `http://host.docker.internal:11434/` if `--profile none`).
   - **HTTP Bearer Auth** on the `Docker MCP Gateway` node — paste the token from `~/.docker/mcp-gateway-token`.

5. Open the Chat panel and ask the agent something tool-shaped: *"Use context7 to fetch the latest n8n LangChain MCP Client Tool docs"* or *"Use perplexity-ask to summarize today's news on local LLMs."*

**Node parameters that matter:**

| Parameter | Value |
|---|---|
| `serverUrl` | `http://host.docker.internal:8811/mcp` (n8n is in Docker — `localhost` would mean the n8n container itself) |
| `serverTransport` | `httpStreamable` (use `sse` only for legacy gateways) |
| `authentication` | `bearerAuth` |
| `include` | `all`, `selected`, or `except` to whitelist/blacklist MCP tools |

**Persisting the gateway:** the script runs in foreground. Options to keep it alive:
- Run inside `tmux` / a dedicated terminal pane.
- Wrap in a `LaunchAgent` plist under `~/Library/LaunchAgents/` for auto-start.
- Add as a Docker Compose service mounting `/var/run/docker.sock` (advanced — gateway needs to spawn other MCP containers).

**Why the indirection?** `docker mcp gateway run` defaults to stdio (single-client, ephemeral). Each Claude Code / Copilot session spawns its own. n8n needs a long-running HTTP endpoint, hence `--transport streaming --port 8811`. You can run multiple gateways on different ports with different profiles if you want to expose different subsets of servers.

## Inter-Service Integration Cheatsheet

| Caller | Target | Use this URL |
|---|---|---|
| n8n / Flowise → Ollama | container | `http://ollama:11434` |
| n8n / Flowise → Ollama (host) | host (Mac, profile=none) | `http://host.docker.internal:11434/` |
| n8n → Qdrant | container | `http://qdrant:6333` |
| n8n → Supabase Postgres | container | host `db`, port `5432` |
| n8n → Supabase REST | container | `http://kong:8000` |
| n8n → Neo4j | container | `bolt://neo4j:7687` |
| n8n → SearXNG | container | `http://searxng:8080` |
| n8n → Langfuse | container | `http://langfuse-web:3000` |
| Anything → Langfuse Postgres | container | `postgres:5432` (different from Supabase `db`) |
| Open WebUI Pipe → n8n | container | `http://n8n:5678/webhook/...` (or host `http://localhost:5678/...`) |

## Troubleshooting

### Supabase DB: "PANIC: could not locate a valid checkpoint record"

Postgres WAL is corrupted (usually from unclean shutdown — host sleep, force-kill, Colima crash, mid-init container restart, or another process touching files concurrently — see TM section below).

```bash
docker compose -p localai down
rm -rf supabase/docker/volumes/db/data && mkdir supabase/docker/volumes/db/data
python3 start_services.py --profile cpu
```

This wipes Supabase data — only safe if you have nothing important in Supabase yet.

### Supabase analytics: `database "_supabase" does not exist`

Init scripts didn't run. Either the data dir wasn't empty when initdb ran, or migrations failed mid-flight. Same fix: wipe `supabase/docker/volumes/db/data` and restart.

### `initdb: directory "/var/lib/postgresql/data" exists but is not empty`

Stray non-postgres files in the data dir. Most common culprit on this machine: the **Obsidian Folder Index plugin** writes `<dirname>.md` files (frontmatter `tags: MOCs`) into every subdirectory. Pollutes `volumes/db/data/`, `pg_wal/`, `pg_multixact/`, etc.

Sweep all such files (handles spaces in names, **excludes this skill file** which mentions the marker string in code):

```bash
find . -type f -name "*.md" \
  ! -path "*/.claude/skills/local-ai-packaged/*" \
  -exec sh -c 'head -5 "$1" | grep -q "^tags: MOCs" && rm "$1"' _ {} \;
```

Long-term fix — the **entire `~/Documents/` is configured as an Obsidian vault** on this machine (see `~/Library/Application Support/obsidian/obsidian.json`). Edit `~/Documents/.obsidian/plugins/obsidian-folder-index/data.json` and add this project to `excludeFolders`:

```json
{
  "excludeFolders": ["01-PROJECTS/local-ai-packaged"],
  "excludePatterns": [
    "**/volumes/**", "**/data/**", "**/.git/**", "**/node_modules/**"
  ]
}
```

**Then reload Obsidian** (Cmd+R inside the app, or quit and relaunch). The plugin only re-reads its config on reload — without a reload the running session keeps polluting.

### Postgres data dir contains directories with `" 2"` suffix (e.g. `base/5 2/`)

**Time Machine** (or another macOS backup tool) is duplicating files mid-write while Postgres is running. Especially aggressive during a first-time TM backup. Symptom: Supabase DB reports `File "base/5/PG_VERSION" is missing` and clients fail with `"base/5" is not a valid data directory`.

Confirm and fix:

```bash
tmutil status                    # if BackupPhase = Copying, TM is active
tmutil addexclusion <project-abs-path>   # works without sudo
tmutil isexcluded <project-abs-path>     # must show "[Excluded]"
docker compose -p localai down
rm -rf supabase/docker/volumes/db/data && mkdir supabase/docker/volumes/db/data
python3 start_services.py --profile cpu
```

The exclusion takes effect for subsequent writes; a backup pass already in flight may finish what it started, but won't touch new files.

### Port conflict: "address already in use" on 8081 / 3001 / etc.

When using **Colima**, dead containers can leave orphan `docker-proxy` processes inside the VM holding ports.

```bash
colima ssh -- ps -eo pid,etime,args | grep docker-proxy
# Kill stale proxies (etime in days = stale)
colima ssh -- sudo kill <PID>
# Nuclear option (clears all stale state, restarts containers from restart-policy):
colima restart
```

Note: `colima restart` will auto-start containers with `restart: unless-stopped`. If Postgres is killed mid-write during restart you'll get the WAL PANIC above — always `docker compose -p localai down` first.

### supabase-storage restart loop with `Error: Region is missing`

Newer storage (v1.48+) requires region config. Add to `.env`: `REGION=local`, `GLOBAL_S3_BUCKET=stub`, `STORAGE_TENANT_ID=stub`, `S3_PROTOCOL_ACCESS_KEY_ID=stub`, `S3_PROTOCOL_ACCESS_KEY_SECRET=stub`, `IMGPROXY_AUTO_WEBP=true`. Then propagate and recreate just storage:

```bash
cp .env supabase/docker/.env
docker compose -p localai -f supabase/docker/docker-compose.yml \
  up -d --force-recreate --no-deps storage
```

### `n8n-import` exits 1 with `Migration "..." failed: could not open file "base/X/Y": Permission denied`

A Postgres data file got created with wrong ownership (`root:root` mode 600 inside the container) due to Colima's host↔container UID mapping quirk on macOS bind mounts. Postgres process (UID 105 in the supabase image) can't read root-owned files.

Workaround — delete the offending file (Postgres recreates it on retry), then recreate `n8n-import`:

```bash
docker exec supabase-db rm /var/lib/postgresql/data/base/<X>/<Y>
docker compose -p localai --profile cpu \
  -f docker-compose.yml -f docker-compose.override.private.yml \
  up -d --force-recreate --no-deps n8n-import
docker logs n8n-import   # should end with "Successfully imported N workflows."
```

### `n8n-import` exits 1 immediately, only message is "There was an error initializing DB"

The `n8n/backup/credentials/` directory is missing — n8n-import requires it to exist even if empty:

```bash
mkdir -p n8n/backup/credentials
docker compose -p localai --profile cpu \
  -f docker-compose.yml -f docker-compose.override.private.yml \
  up -d --force-recreate --no-deps n8n-import
```

### supabase-pooler restarts forever

Known upstream issue. Workaround: see [supabase/supabase#30210](https://github.com/supabase/supabase/issues/30210).

### SearXNG won't start ("cap_drop" related)

`start_services.py` auto-handles this on first run by commenting out `cap_drop: - ALL` in `docker-compose.yml`, then re-enabling it on subsequent runs. If it left the file in a half-edited state (commented out long-term), restore the original line manually.

### `supabase/` folder partially populated

A bad clone. Delete `supabase/` and re-run `start_services.py`.

### n8n cannot reach Supabase even though Kong responds

Almost always `@` (or other special char) in `POSTGRES_PASSWORD`. Regenerate it without special chars and rerun `generate-env.sh` (or edit `.env`).

## File Map

| Path | Role |
|---|---|
| `start_services.py` | Orchestrator — clones supabase, fixes SearXNG, starts both stacks |
| `generate-env.sh` | `.env.tpl` → `.env` via 1Password CLI |
| `.env.tpl` / `.env.example` | Templates (1P / manual) |
| `docker-compose.yml` | Main AI stack (n8n, ollama, qdrant, neo4j, flowise, langfuse, etc.) |
| `docker-compose.override.private.yml` | Localhost port mappings for dev |
| `docker-compose.override.public.yml` | Strips local ports for prod |
| `Caddyfile` | Reverse proxy config; uses `{$*_HOSTNAME}` env vars |
| `caddy-addon/*.conf` | Custom Caddy site configs (auto-imported) |
| `searxng/settings-base.yml` | Source for `searxng/settings.yml` (auto-generated) |
| `n8n/backup/workflows/` | Auto-imported on first n8n start |
| `n8n/backup/credentials/` | Required to exist (even if empty) |
| `n8n-tool-workflows/` | Reusable sub-workflows (not auto-imported) |
| `flowise/` | Flowise tools and chatflows |
| `n8n_pipe.py` | Open WebUI ↔ n8n bridge |
| `shared/` | Mounted into n8n at `/data/shared` |
| `supabase/` | Sparse checkout (gitignored), recreated by `start_services.py` |

## Red Flags — Stop and Investigate

- Container status `Restarting (1)` for more than ~30 s — pull `docker logs <name>`
- `start_services.py` failing at the supabase `up -d` step — almost always WAL corruption or stray files in `volumes/db/data/`
- Port conflicts after `docker compose down` — orphan Colima `docker-proxy` from a previous run
- Directories with `" 2"` suffix anywhere under `volumes/db/data/` — Time Machine is touching the data dir; exclude immediately
- `<dirname>.md` files reappearing in `volumes/`, `data/`, etc. — Obsidian Folder Index hasn't been reloaded with new exclusions
- n8n workflows don't appear in UI — `n8n-import` exited non-zero. Check `docker logs n8n-import`
- Open WebUI shows "Network Error" calling n8n — webhook isn't toggled to **Production / Active** in n8n
