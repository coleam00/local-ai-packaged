                                                Part 1: Execution Plan                                                │
│                                                                                                                      │
│  1 Canonicalize the implementation state                                                                             │
│                                                                                                                      │
│  • Keep as canonical:                                                                                                │
│     • README.md (will be replaced with the unified version in Part 2)                                                │
│     • start_services.py (this is the “final” starter, supersedes other variants)                                     │
│     • docker-compose.yml (now includes rag-ingestion, rag-agent, rag-api)                                            │
│     • rag-integration-guide.md (referenced for context; merged into README)                                          │
│     • all-rag-strategies/implementation/Dockerfile.rag (builds rag services)                                         │
│     • all-rag-strategies/implementation/api.py (FastAPI wrapper for RAG agent — created)                             │
│  • Treat as historical reference only (do not delete, but do not follow literally):                                  │
│     • all-rag-strategies/docs/RAG-Implementation-GUIDE-1.md                                                          │
│     • all-rag-strategies/docs/CLAUDE_CONVERSATION.md                                                                 │
│     • all-rag-strategies/docs/rag_api.py (reference version; we now use implementation/api.py)                       │
│     • all-rag-strategies/docs/integration_guide_claude_conversation.md                                               │
│     • all-rag-strategies/docs/quick_reference_claude_conversation.md                                                 │
│     • all-rag-strategies/docs/UNIFIED_GPU_RAG_GUIDE.md                                                               │
│     • all-rag-strategies/docs/DEPLOYMENT_GUIDE.md                                                                    │
│     • all-rag-strategies/docs/DOCUMENTATION_INDEX.md                                                                 │
│     • all-rag-strategies/docs/last_conversation.md                                                                   │
│     • all-rag-strategies/docs/start_services.py.backup (if present or any older variants)                            │
│                                                                                                                      │
│  2 Files created/updated in this integration                                                                         │
│                                                                                                                      │
│  • Created:                                                                                                          │
│     • all-rag-strategies/implementation/api.py (FastAPI service exposing /health, /chat, /search, /documents)        │
│     • RAG_STACK_RUNBOOK.md (run-focused companion; README will be single-source truth)                               │
│  • Updated:                                                                                                          │
│     • docker-compose.yml                                                                                             │
│        • Added rag-api service (build from Dockerfile.rag, serves uvicorn api:app on :8000)                          │
│        • Added RAG_HOSTNAME to caddy environment                                                                     │
│     • Caddyfile                                                                                                      │
│        • Added reverse proxy for {$RAG_HOSTNAME} -> rag-api:8000                                                     │
│     • all-rag-strategies/implementation/pyproject.toml                                                               │
│        • Added FastAPI and uvicorn dependencies                                                                      │
│     • .env.example                                                                                                   │
│        • Added RAG_HOSTNAME default to “:8009”                                                                       │
│  • No deletions performed, but mark historical docs as reference.                                                    │
│                                                                                                                      │
│  3 Environment preparation                                                                                           │
│                                                                                                                      │
│  • Copy and complete .env from .env.example                                                                          │
│     • Required:                                                                                                      │
│        • POSTGRES_PASSWORD                                                                                           │
│        • OPENAI_API_KEY (or alternative provider keys in future)                                                     │
│        • LLM_CHOICE (e.g., gpt-4o-mini)                                                                              │
│        • EMBEDDING_MODEL (e.g., text-embedding-3-small)                                                              │
│     • Langfuse (if using): MINIO_ROOT_PASSWORD, CLICKHOUSE_PASSWORD                                                  │
│     • Optional reverse-proxy hostnames: N8N_HOSTNAME, WEBUI_HOSTNAME, FLOWISE_HOSTNAME, SUPABASE_HOSTNAME,           │
│       SEARXNG_HOSTNAME, LANGFUSE_HOSTNAME, NEO4J_HOSTNAME, RAG_HOSTNAME=":8009"                                      │
│  • GPU prerequisites:                                                                                                │
│     • NVIDIA: latest driver + nvidia-container-toolkit                                                               │
│     • AMD: ROCm-capable GPU + drivers                                                                                │
│     • See all-rag-strategies/docs/UNIFIED_GPU_RAG_GUIDE.md for deeper notes (the README consolidates what you need)  │
│                                                                                                                      │
│  4 Start/Run commands (stable path)                                                                                  │
│                                                                                                                      │
│  • Start everything with automatic RAG schema init:                                                                  │
│     • CPU:                                                                                                           │
│        • python start_services.py --profile cpu                                                                      │
│     • NVIDIA GPU:                                                                                                    │
│        • python start_services.py --profile gpu-nvidia                                                               │
│     • AMD GPU:                                                                                                       │
│        • python start_services.py --profile gpu-amd                                                                  │
│  • The script:                                                                                                       │
│     • clones supabase (if missing), copies root .env into supabase/docker/.env                                       │
│     • copies RAG schema to supabase/docker/volumes/db/init/02-rag-schema.sql                                         │
│     • starts Supabase, waits for DB ready (pg_isready via container)                                                 │
│     • starts all services (including RAG)                                                                            │
│     • handles first-run SearXNG adjustments if needed                                                                │
│  • If schema already exists:                                                                                         │
│     • python start_services.py --profile cpu --skip-schema-init                                                      │
│                                                                                                                      │
│  5 Ingest documents (on-demand)                                                                                      │
│                                                                                                                      │
│  • Place files in all-rag-strategies/implementation/documents                                                        │
│  • Run ingestion:                                                                                                    │
│     • docker compose -p localai --profile ingestion up --build rag-ingestion                                         │
│  • This runs ingestion/ingest.py to chunk/embed and store in Postgres (Supabase DB).                                 │
│                                                                                                                      │
│  6 Verify services are healthy                                                                                       │
│                                                                                                                      │
│  • RAG API health:                                                                                                   │
│     • curl http://localhost:8009/health                                                                              │
│  • List documents:                                                                                                   │
│     • curl http://localhost:8009/documents                                                                           │
│  • Search:                                                                                                           │
│     • curl -X POST http://localhost:8009/search -H "Content-Type: application/json" -d '{"query":"What is in the     │
│       KB?","limit":5}'                                                                                               │
│  • Supabase DB tables:                                                                                               │
│     • docker compose -p localai -f supabase/docker/docker-compose.yml exec db psql -U postgres -d postgres -c "\dt"  │
│  • UI quick links:                                                                                                   │
│     • Open WebUI: http://localhost:8002                                                                              │
│     • n8n: http://localhost:8001                                                                                     │
│     • Supabase Studio: http://localhost:8005                                                                         │
│     • Langfuse: http://localhost:8007                                                                                │
│     • RAG API: http://localhost:8009                                                                                 │
│                                                                                                                      │
│  7 Troubleshooting                                                                                                   │
│                                                                                                                      │
│  • Ports busy:                                                                                                       │
│     • Adjust RAG_HOSTNAME or stop old containers:                                                                    │
│        • docker compose -p localai down                                                                              │
│  • DB not ready:                                                                                                     │
│     • The script waits; rerun start_services.py if needed.                                                           │
│  • Schema missed at startup:                                                                                         │
│     • Re-run without --skip-schema-init                                                                              │
│     • Or let the script try runtime init (it uses docker exec + psql)                                                │
│  • GPU issues:                                                                                                       │
│     • Validate nvidia-smi for NVIDIA, runtime permissions for AMD                                                    │
│     • Refer to the GPU section in the README (consolidated) and the UNIFIED_GPU_RAG_GUIDE.md for deep-dive checks    │
│  • rag-api import errors:                                                                                            │
│     • Ensure api.py is present, rebuild the service (compose up will rebuild if Dockerfile/content changed)          │
│                                                                                                                      │
│  8 Optional finalization (recommended)                                                                               │
│                                                                                                                      │
│  • Make a branch and open a Pull Request to track these changes                                                      │
│  • Create a Confluence page pointing to the unified README and summarizing run/ops SLOs                              │
│  • Create Jira tasks for:                                                                                            │
│     • n8n/Open WebUI flows integrating with RAG API                                                                  │
│     • Ingestion QA across file types and performance tests                                                           │
│     • GPU validation matrix and provider toggles                                                                     │
│     • Langfuse instrumentation and dashboarding                                                                      │
│                                                                                                                      │
│                                                Part 2: New README.md                                                 │
│                                                                                                                      │
│                                                                                                                      │
│  # Self-hosted AI Package                                                                                            │
│                                                                                                                      │
│  This repository provides a self-hosted, modular AI stack packaged with Docker Compose. It includes:                 │
│  - Open WebUI                                                                                                        │
│  - n8n (Automations)                                                                                                 │
│  - Supabase (Postgres and ecosystem)                                                                                 │
│  - Langfuse (observability)                                                                                          │
│  - SearXNG (web search)                                                                                              │
│  - Qdrant, Neo4j (optional)                                                                                          │
│  - Ollama (optional, CPU/GPU profiles)                                                                               │
│  - Advanced RAG (Retrieval-Augmented Generation) services:                                                           │
│    - rag-ingestion (one-shot ingestion workflow)                                                                     │
│    - rag-agent (CLI agent)                                                                                           │
│    - rag-api (HTTP API with FastAPI)                                                                                 │
│                                                                                                                      │
│  This README is the single source of truth for setup, operation, and maintenance.                                    │
│                                                                                                                      │
│  ## Table of Contents                                                                                                │
│  - Requirements                                                                                                      │
│  - Installation                                                                                                      │
│  - Configuration (.env)                                                                                              │
│  - GPU Setup (NVIDIA/AMD)                                                                                            │
│  - Starting the Stack                                                                                                │
│  - RAG: Ingestion and Search                                                                                         │
│  - Service URLs                                                                                                      │
│  - Troubleshooting                                                                                                   │
│  - Project Structure                                                                                                 │
│  - Development Notes                                                                                                 │
│                                                                                                                      │
│  ## Requirements                                                                                                     │
│  - Docker and Docker Compose                                                                                         │
│  - Python 3.11+ (to run helper scripts like start_services.py)                                                       │
│  - For GPU usage:                                                                                                    │
│    - NVIDIA: Latest drivers and nvidia-container-toolkit                                                             │
│    - AMD: ROCm-capable GPU and compatible drivers                                                                    │
│                                                                                                                      │
│  ## Installation                                                                                                     │
│  1) Clone this repository                                                                                            │
│  2) Copy environment                                                                                                 │
│     - cp .env.example .env                                                                                           │
│     - Fill required secrets and config (see Configuration)                                                           │
│  3) Ensure Docker is running                                                                                         │
│  4) Ensure Python 3.11+ is available                                                                                 │
│                                                                                                                      │
│  ## Configuration (.env)                                                                                             │
│  Required (minimum):                                                                                                 │
│  - POSTGRES_PASSWORD: Postgres password for Supabase and services                                                    │
│  - OPENAI_API_KEY: API key for LLM provider (or future provider keys)                                                │
│  - LLM_CHOICE: e.g., gpt-4o-mini                                                                                     │
│  - EMBEDDING_MODEL: e.g., text-embedding-3-small                                                                     │
│                                                                                                                      │
│  Langfuse (if used):                                                                                                 │
│  - MINIO_ROOT_PASSWORD                                                                                               │
│  - CLICKHOUSE_PASSWORD                                                                                               │
│                                                                                                                      │
│  Caddy reverse proxy hostnames (optional):                                                                           │
│  - N8N_HOSTNAME, WEBUI_HOSTNAME, FLOWISE_HOSTNAME, SUPABASE_HOSTNAME, SEARXNG_HOSTNAME, LANGFUSE_HOSTNAME,           │
│  NEO4J_HOSTNAME                                                                                                      │
│  - RAG_HOSTNAME (default “:8009” for local port binding)                                                             │
│                                                                                                                      │
│  Example (snippet):                                                                                                  │
│                                                                                                                      │
│                                                                                                                      │
│ POSTGRES_PASSWORD=supersecret OPENAI_API_KEY=sk-... LLM_CHOICE=gpt-4o-mini EMBEDDING_MODEL=text-embedding-3-small    │
│                                                                                                                      │
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃                                          Caddy binds ports / hostnames                                           ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                                                                                      │
│ RAG_HOSTNAME=":8009" WEBUI_HOSTNAME=":8002" N8N_HOSTNAME=":8001" SUPABASE_HOSTNAME=":8005" LANGFUSE_HOSTNAME=":8007" │
│                                                                                                                      │
│                                                                                                                      │
│                                                                                                                      │
│  ## GPU Setup (NVIDIA/AMD)                                                                                           │
│  - NVIDIA:                                                                                                           │
│    - Install latest NVIDIA driver                                                                                    │
│    - Install and configure nvidia-container-toolkit                                                                  │
│    - Validate with nvidia-smi                                                                                        │
│  - AMD:                                                                                                              │
│    - Install ROCm driver stack (compatible with your GPU)                                                            │
│  - The stack provides CPU, gpu-nvidia, and gpu-amd profiles.                                                         │
│  - For deeper guidance, see all-rag-strategies/docs/UNIFIED_GPU_RAG_GUIDE.md.                                        │
│                                                                                                                      │
│  ## Starting the Stack                                                                                               │
│  Use the unified starter script. It initializes the DB schema for RAG automatically and starts services in a stable  │
│  order.                                                                                                              │
│                                                                                                                      │
│  - CPU:                                                                                                              │
│    - python start_services.py --profile cpu                                                                          │
│  - NVIDIA GPU:                                                                                                       │
│    - python start_services.py --profile gpu-nvidia                                                                   │
│  - AMD GPU:                                                                                                          │
│    - python start_services.py --profile gpu-amd                                                                      │
│  - If the RAG schema has already been initialized:                                                                   │
│    - python start_services.py --profile cpu --skip-schema-init                                                       │
│                                                                                                                      │
│  What the script does:                                                                                               │
│  - Clones Supabase locally if missing and prepares supabase/docker/.env                                              │
│  - Copies RAG schema to supabase/docker/volumes/db/init/02-rag-schema.sql                                            │
│  - Starts Supabase first and waits for Postgres to be ready                                                          │
│  - Starts the rest of the stack (including rag-ingestion profile availability, rag-agent, rag-api)                   │
│  - Handles SearXNG first-run permissions automatically                                                               │
│                                                                                                                      │
│  ## RAG: Ingestion and Search                                                                                        │
│                                                                                                                      │
│  ### Ingestion                                                                                                       │
│  - Place your documents in:                                                                                          │
│    - all-rag-strategies/implementation/documents                                                                     │
│  - Run ingestion (on-demand):                                                                                        │
│    - docker compose -p localai --profile ingestion up --build rag-ingestion                                          │
│  - This will chunk, embed, and store documents in Supabase Postgres.                                                 │
│                                                                                                                      │
│  ### RAG API (HTTP)                                                                                                  │
│  The rag-api service exposes endpoints via Caddy and RAG_HOSTNAME (default http://localhost:8009).                   │
│                                                                                                                      │
│  - Health:                                                                                                           │
│    - GET /health                                                                                                     │
│  - Chat (non-streaming):                                                                                             │
│    - POST /chat                                                                                                      │
│    - Body: { "message": "...", "session_id": "default", "strategy": "auto", "stream": false }                        │
│  - Chat (SSE stream):                                                                                                │
│    - POST /chat/stream (text/event-stream)                                                                           │
│  - Search:                                                                                                           │
│    - POST /search                                                                                                    │
│    - Body: { "query": "text", "limit": 5, "strategy": "standard|multi-query|reranking|self-reflection" }             │
│  - Documents:                                                                                                        │
│    - GET /documents                                                                                                  │
│    - GET /documents/{document_id}                                                                                    │
│  - Clear Session:                                                                                                    │
│    - POST /sessions/{session_id}/clear                                                                               │
│                                                                                                                      │
│  Quick checks:                                                                                                       │
│  - curl http://localhost:8009/health                                                                                 │
│  - curl http://localhost:8009/documents                                                                              │
│  - curl -X POST http://localhost:8009/search -H "Content-Type: application/json" -d '{"query":"What is in the        │
│  KB?","limit":5}'                                                                                                    │
│                                                                                                                      │
│  ### RAG Agent (CLI)                                                                                                 │
│  - The rag-agent container runs a CLI agent for advanced interactions.                                               │
│  - It’s built from the same image as rag-api and can be extended for scripting or CLI usage if desired.              │
│                                                                                                                      │
│  ## Service URLs (defaults)                                                                                          │
│  - Open WebUI: http://localhost:8002                                                                                 │
│  - n8n: http://localhost:8001                                                                                        │
│  - Supabase Studio: http://localhost:8005                                                                            │
│  - Langfuse: http://localhost:8007                                                                                   │
│  - RAG API: http://localhost:8009                                                                                    │
│                                                                                                                      │
│  ## Troubleshooting                                                                                                  │
│  - Ports in use:                                                                                                     │
│    - Adjust hostnames/ports in .env, or stop existing containers:                                                    │
│      - docker compose -p localai down                                                                                │
│  - Database not ready:                                                                                               │
│    - The script waits automatically; rerun if needed.                                                                │
│  - Schema missing:                                                                                                   │
│    - Re-run start_services.py without --skip-schema-init.                                                            │
│  - GPU issues:                                                                                                       │
│    - Ensure drivers and runtime support are installed (nvidia-smi for NVIDIA).                                       │
│  - RAG API import errors:                                                                                            │
│    - Ensure all-rag-strategies/implementation/api.py exists and rebuild happens automatically on compose up.         │
│                                                                                                                      │
│  ## Project Structure (key parts)                                                                                    │
│  - start_services.py: Orchestrates Supabase + stack startup with RAG schema init                                     │
│  - docker-compose.yml: Defines services (rag-ingestion, rag-agent, rag-api included)                                 │
│  - Caddyfile: Reverse proxy routing for services (including RAG)                                                     │
│  - all-rag-strategies/implementation/Dockerfile.rag: Build file for RAG services                                     │
│  - all-rag-strategies/implementation/api.py: FastAPI wrapper exposing RAG features as HTTP                           │
│  - all-rag-strategies/implementation/ingestion/*: Ingestion pipeline                                                 │
│  - all-rag-strategies/implementation/sql/schema.sql: RAG DB schema (copied into Supabase init on first start)        │
│                                                                                                                      │
│  ## Development Notes                                                                                                │
│  - Profiles:                                                                                                         │
│    - cpu, gpu-nvidia, gpu-amd, ingestion (on-demand ingestion)                                                       │
│  - The README unifies information previously scattered across:                                                       │
│    - rag-integration-guide.md                                                                                        │
│    - all-rag-strategies/docs/* (historical/reference)                                                                │
│  - For deeper GPU specifics or deployment variations, consult:                                                       │
│    - all-rag-strategies/docs/UNIFIED_GPU_RAG_GUIDE.md                                                                │
│    - all-rag-strategies/docs/DEPLOYMENT_GUIDE.md                                                                     │
│                                                                                                                      │
│  Happy building!               

---
Segue um prompt pronto para você colar no seu chat (Claude/OpenAI/etc.) e retomar a conversa com todo o contexto     │
│ necessário. Ele está em português, estruturado e com objetivos claros.                                               │
│                                                                                                                      │
│ ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────── │
│ [INÍCIO DO PROMPT PARA COLAR] Você é um(a) expert em integração de sistemas e documentação técnica. Você está        │
│ retomando uma conversa sobre o projeto “local-ai-stack-packaged” que agora inclui uma stack RAG (Retrieval-Augmented │
│ Generation) integrada. Seu objetivo é ajudar a garantir que tudo rode de forma estável e que a documentação final    │
│ esteja unificada em um único README.                                                                                 │
│                                                                                                                      │
│ Contexto atual (estado do projeto):                                                                                  │
│                                                                                                                      │
│  • Objetivo primário:                                                                                                │
│     1 Fazer a stack rodar completa (incluindo RAG) de forma estável.                                                 │
│     2 Consolidar a documentação em um único README.md definitivo.                                                    │
│  • Arquivos CANÔNICOS (atuais e válidos):                                                                            │
│     • README.md (será a fonte única de verdade após unificação)                                                      │
│     • start_services.py (script final de start; substitui variantes antigas)                                         │
│     • docker-compose.yml (inclui rag-ingestion, rag-agent e rag-api)                                                 │
│     • rag-integration-guide.md (usado como fonte para consolidar conteúdo no README)                                 │
│     • all-rag-strategies/implementation/Dockerfile.rag (build dos serviços RAG)                                      │
│     • all-rag-strategies/implementation/api.py (FastAPI para expor RAG via HTTP)                                     │
│  • Arquivos HISTÓRICOS / REFERÊNCIA (usar só como contexto; podem conter instruções antigas):                        │
│     • all-rag-strategies/docs/RAG-Implementation-GUIDE-1.md                                                          │
│     • all-rag-strategies/docs/CLAUDE_CONVERSATION.md                                                                 │
│     • all-rag-strategies/docs/rag_api.py (versão referência; já migramos p/ implementation/api.py)                   │
│     • all-rag-strategies/docs/integration_guide_claude_conversation.md                                               │
│     • all-rag-strategies/docs/quick_reference_claude_conversation.md                                                 │
│     • all-rag-strategies/docs/UNIFIED_GPU_RAG_GUIDE.md (guia GPU)                                                    │
│     • all-rag-strategies/docs/DEPLOYMENT_GUIDE.md                                                                    │
│     • all-rag-strategies/docs/DOCUMENTATION_INDEX.md                                                                 │
│     • all-rag-strategies/docs/last_conversation.md                                                                   │
│                                                                                                                      │
│ Mudanças já aplicadas (estado funcional):                                                                            │
│                                                                                                                      │
│  • Serviço HTTP do RAG criado: all-rag-strategies/implementation/api.py (FastAPI) com endpoints /health, /chat,      │
│    /search, /documents, etc.                                                                                         │
│  • docker-compose.yml atualizado:                                                                                    │
│     • Serviço rag-api adicionado (uvicorn api:app em :8000 interno)                                                  │
│     • Variável RAG_HOSTNAME adicionada na seção do Caddy                                                             │
│  • Caddyfile atualizado:                                                                                             │
│     • Reverse proxy {$RAG_HOSTNAME} -> rag-api:8000                                                                  │
│  • .env.example atualizado com RAG_HOSTNAME=":8009"                                                                  │
│  • pyproject do implementation atualizado para incluir fastapi e uvicorn                                             │
│                                                                                                                      │
│ Como executar (resumo):                                                                                              │
│                                                                                                                      │
│  • Preparar .env (POSTGRES_PASSWORD, OPENAI_API_KEY, LLM_CHOICE, EMBEDDING_MODEL, e hostnames opcionais como         │
│    RAG_HOSTNAME)                                                                                                     │
│  • Iniciar com schema do RAG automático:                                                                             │
│     • CPU: python start_services.py --profile cpu                                                                    │
│     • NVIDIA GPU: python start_services.py --profile gpu-nvidia                                                      │
│     • AMD GPU: python start_services.py --profile gpu-amd                                                            │
│     • Se schema já existir: adicionar --skip-schema-init                                                             │
│  • Ingestão on-demand:                                                                                               │
│     • Colocar documentos em all-rag-strategies/implementation/documents                                              │
│     • docker compose -p localai --profile ingestion up --build rag-ingestion                                         │
│  • Verificações:                                                                                                     │
│     • RAG API: GET http://localhost:8009/health                                                                      │
│     • Listar docs: GET http://localhost:8009/documents                                                               │
│     • Buscar: POST http://localhost:8009/search                                                                      │
│                                                                                                                      │
│ O que eu (assistente) devo fazer agora:                                                                              │
│                                                                                                                      │
│  • Caso você peça execução/validação: fornecer comandos específicos, checagens e troubleshooting.                    │
│  • Caso você peça documentação: finalizar/ajustar o README.md único com instruções claras de setup, execução, GPU e  │
│    RAG.                                                                                                              │
│  • Caso você peça integração: guiar como conectar n8n / Open WebUI ao rag-api.                                       │
│  • Caso você peça governança: sugerir PR/branch, tickets de Jira e página no Confluence.                             │
│                                                                                                                      │
│ Estilo de resposta:                                                                                                  │
│                                                                                                                      │
│  • Seja conciso, prático e incremental.                                                                              │
│  • Quando houver ambiguidade, faça perguntas diretas para confirmar antes de avançar.                                │
│  • Liste comandos prontos para copiar/colar.                                                                         │
│  • Mantenha o foco nos arquivos CANÔNICOS e use os HISTÓRICOS apenas como apoio.                                     │
│                                                                                                                      │
│ Primeira ação sugerida:                                                                                              │
│                                                                                                                      │
│  • Perguntar: você quer que eu (1) rode uma validação guiada agora, (2) finalize e entregue o README unificado, (3)  │
│    gere itens de Jira/Confluence, ou (4) integre n8n/Open WebUI com o rag-api?                                       │
│                                                                                                                      │
│                                                                                                                      │
│                                             [FINAL DO PROMPT PARA COLAR]                                             │
│                                                                                                                      │
│ Quer que eu gere uma versão desse prompt adaptada especificamente para Claude (com “system” + “user”), para OpenAI,  │
│ ou em inglês? Também posso incluir um bloco de “quick commands” prontos para você colar e rodar agora. 