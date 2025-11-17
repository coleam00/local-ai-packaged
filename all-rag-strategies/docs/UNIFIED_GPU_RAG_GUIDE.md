# Documentation Enhancement: GPU PRIME/Docker + RAG Integration Strategy

## 1. Overview: Unified Architecture with GPU Acceleration & RAG

This document consolidates GPU acceleration strategies (NVIDIA PRIME/prime-run with Docker) and the RAG integration improvements previously discussed. The goal is to create a complete, optimized local-ai-packaged environment that leverages your hybrid graphics system (Intel iGPU + NVIDIA dGPU) for energy efficiency while dedicating the dGPU to compute-intensive workloads (LLMs, embeddings).

### Key Objectives:
1. **Host Display**: iGPU (Intel HD Graphics) for energy efficiency
2. **Docker Compute**: dGPU (NVIDIA GeForce 940MX) for LLM inference and embeddings
3. **RAG System**: Fully integrated with schema initialization, ingestion, and query capabilities
4. **Robustness**: Dynamic container discovery, fallback mechanisms, proper error handling

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HOST MACHINE                                │
│  ┌──────────────────────────────┐   ┌──────────────────────────┐   │
│  │   Display Management          │   │   GPU Resource Control   │   │
│  │  ├─ iGPU (Intel HD) - Active  │   │  ├─ prime-run (wrapper)  │   │
│  │  ├─ dGPU (NVIDIA) - Standby   │   │  ├─ PRIME Variables     │   │
│  │  └─ DISPLAY=:0                │   │  └─ Docker Runtime      │   │
│  └──────────────────────────────┘   └──────────────────────────┘   │
│          ▼                                        ▼                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │         Docker Compose Stack (localai project)               │   │
│  │                                                               │   │
│  │  ┌────────────────┐  ┌────────────────┐                     │   │
│  │  │   Open WebUI   │  │      n8n       │  (CPU/iGPU)        │   │
│  │  │   (ollama-cpu) │  │   Orchestration│                     │   │
│  │  └────────────────┘  └────────────────┘                     │   │
│  │                              │                                │   │
│  │  ┌──────────────────────────▼─────────────────────────────┐ │   │
│  │  │  ollama-gpu (GPU-accelerated LLM Inference)            │ │   │
│  │  │  ├─ Profile: gpu-nvidia                                │ │   │
│  │  │  ├─ Resource: dGPU (NVIDIA 940MX)                      │ │   │
│  │  │  └─ Deploy Config: driver: nvidia, count: 1            │ │   │
│  │  └──────────────────────────────────────────────────────┘ │   │
│  │                              │                                │   │
│  │  ┌────────────────────────────▼──────────────────────────┐ │   │
│  │  │  Supabase PostgreSQL + pgvector (RAG Vector DB)       │ │   │
│  │  │  ├─ Service: db (localai network)                     │ │   │
│  │  │  ├─ Schema: Dynamically initialized at startup        │ │   │
│  │  │  ├─ Tables: documents, chunks, embeddings            │ │   │
│  │  │  └─ Port: 5432 (internal), exposed for management     │ │   │
│  │  └──────────────────────────────────────────────────────┘ │   │
│  │                              ▲                                │   │
│  │              ┌───────────────┴────────────────┐            │   │
│  │              │                                 │            │   │
│  │    ┌─────────┴──────────┐       ┌─────────────┴────┐      │   │
│  │    │ rag-ingestion      │       │ rag-agent        │      │   │
│  │    │ (on-demand)        │       │ (optional CLI)   │      │   │
│  │    │ Profile: ingestion │       │ (standalone)     │      │   │
│  │    └────────────────────┘       └──────────────────┘      │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. GPU Strategy: NVIDIA PRIME + Docker

### 3.1 PRIME/prime-run Fundamentals

**PRIME (Presentation Render In Multiple Environments)** enables efficient hybrid GPU usage on Optimus notebooks:

- **Default Behavior**: iGPU renders to display (low power, sufficient for desktop)
- **On-Demand NVIDIA**: Use `__NV_PRIME_RENDER_OFFLOAD=1` to render on dGPU and composite to iGPU
- **prime-run Wrapper**: Simplifies by injecting PRIME variables automatically

#### PRIME Variables Explained:

```bash
# Core variables for OpenGL/GLX offload
__NV_PRIME_RENDER_OFFLOAD=1              # Enable offloading to NVIDIA
__GLX_VENDOR_LIBRARY_NAME=nvidia         # Use NVIDIA's GLX implementation

# For Vulkan/EGL applications
# __NV_PRIME_RENDER_OFFLOAD=1 usually sufficient; VK_LAYER_NV_optimus auto-enabled

# Advanced provider selection (if needed with multiple GPUs)
__NV_PRIME_RENDER_OFFLOAD_PROVIDER=NVIDIA-G0
```

#### prime-run Wrapper Setup:

If your system doesn't have `prime-run`, create one:

```bash
# Create wrapper script
sudo nano /usr/local/bin/prime-run

# Add content:
#!/bin/bash
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia exec "$@"

# Make executable
sudo chmod +x /usr/local/bin/prime-run

# Usage:
prime-run glxgears        # Run OpenGL app on dGPU
prime-run nvidia-smi      # Check GPU usage
```

### 3.2 Docker + GPU Integration

**NVIDIA Container Toolkit** manages GPU access within containers:

- **Runtime Setup**: Allows `--gpus` flag in Docker/Compose
- **No PRIME Variables Needed**: Toolkit handles GPU passthrough directly
- **CUDA Workloads**: Container can use CUDA/cuDNN without display server

#### Docker Compose GPU Configuration:

```yaml
services:
  ollama-gpu:
    image: ollama/ollama:latest
    profiles: ["gpu-nvidia"]  # Activated with --profile gpu-nvidia
    
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia      # Use NVIDIA runtime
              count: 1            # Allocate 1 GPU (use 'all' for all GPUs)
              capabilities: [gpu] # Enable GPU capability

    environment:
      # No PRIME variables needed for headless CUDA work
      - OLLAMA_NUM_PARALLEL=1
      - OLLAMA_NUM_THREAD=4
```

#### Verifying GPU Access:

```bash
# Test basic GPU passthrough
docker run --rm --gpus all nvidia/cuda:12.9.0-base-ubuntu22.04 nvidia-smi

# After starting your stack, verify ollama can access GPU
docker exec ollama nvidia-smi

# Monitor GPU usage in real-time
watch -n 1 nvidia-smi
```

### 3.3 Combining PRIME + Docker for Hybrid Workloads

**Scenario**: Run GUI application in container using dGPU for rendering, display on host iGPU

```bash
# If you need GPU-accelerated GUI apps in containers:
docker run \
  --rm \
  --gpus all \
  -e __NV_PRIME_RENDER_OFFLOAD=1 \
  -e __GLX_VENDOR_LIBRARY_NAME=nvidia \
  -e DISPLAY=:0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  nvidia/cuda:12.9.0-runtime-ubuntu22.04 \
  bash

# Inside container, PRIME variables guide GLX through NVIDIA driver
# while result displays on host's iGPU display
```

**For Your Project**: Not needed for headless LLM inference; container uses CUDA directly.

---

## 4. start_services.py: Enhanced with GPU & RAG Support

### 4.1 Key Improvements

The updated `start_services.py` includes:

1. **Dynamic Container Discovery**: Finds db container ID dynamically (no hardcoded names)
2. **Database Health Checks**: Waits for PostgreSQL to be ready before schema init
3. **RAG Schema Initialization**: Two-stage approach (init-time copy + runtime fallback)
4. **GPU Profile Support**: Passes `--profile` to select cpu/gpu-nvidia/gpu-amd
5. **Error Resilience**: Graceful fallbacks and informative error messages

### 4.2 Usage

```bash
# Start with CPU profile (uses ollama-cpu service)
python start_services.py --profile cpu

# Start with NVIDIA GPU acceleration (uses ollama-gpu service)
python start_services.py --profile gpu-nvidia

# Start with additional options
python start_services.py --profile gpu-nvidia --environment private

# Skip RAG schema initialization if already done
python start_services.py --profile gpu-nvidia --skip-schema-init
```

### 4.3 Script Enhancements Explained

#### Dynamic Container ID Resolution:

**Problem**: Original script hardcoded `supabase-db` container name, which fails if Docker generates different names.

**Solution**: Use `docker compose ps -q db` to get actual container ID:

```python
def get_db_container_id():
    """Dynamically find database container ID"""
    db_service_name = "db"
    project_name = "localai"
    compose_file = os.path.join("supabase", "docker", "docker-compose.yml")
    
    cmd = [
        "docker", "compose",
        "-p", project_name,
        "-f", compose_file,
        "ps", "-q", db_service_name
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()
```

#### Two-Stage Schema Initialization:

**Stage 1 (Init-time)**: Copy schema.sql to Supabase init directory
```python
schema_dest = os.path.join("supabase", "docker", "volumes", "db", "init", "02-rag-schema.sql")
shutil.copyfile(schema_source, schema_dest)  # Executed on db container startup
```

**Stage 2 (Runtime fallback)**: Apply via psql if Stage 1 fails
```python
process = subprocess.Popen(
    ["docker", "exec", "-i", container_id, "psql", "-U", "postgres", "-d", "postgres"],
    stdin=subprocess.PIPE,
    text=True
)
process.communicate(input=schema_sql)  # Executes schema against running db
```

#### Database Health Check:

```python
def wait_for_database():
    """Wait until database is ready to accept connections"""
    for attempt in range(30):
        result = subprocess.run(
            ["docker", "exec", container_id, "pg_isready", "-U", "postgres"],
            capture_output=True,
            check=False
        )
        if result.returncode == 0:
            return True  # Database ready!
        time.sleep(2)
    return False  # Timeout
```

---

## 5. RAG Integration: Complete Setup

### 5.1 Database Schema Initialization

**What happens at startup**:

1. Script copies `all-rag-strategies/implementation/sql/schema.sql` to Supabase init directory
2. Supabase db container starts and executes init scripts automatically
3. RAG tables created: `documents`, `chunks`, `embeddings_idx` (vector index)
4. Schema includes pgvector extension for semantic search

### 5.2 Services Configuration

#### rag-ingestion Service

Purpose: Process documents into chunks and generate embeddings

```yaml
rag-ingestion:
  build:
    context: ./all-rag-strategies/implementation
    dockerfile: Dockerfile.rag
  profiles: ["ingestion"]  # On-demand via --profile ingestion
  depends_on:
    db:
      condition: service_healthy
  environment:
    - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - EMBEDDING_MODEL=${EMBEDDING_MODEL:-text-embedding-3-small}
  volumes:
    - ./all-rag-strategies/implementation/documents:/app/documents
  command: ["uv", "run", "python", "ingestion/ingest.py", "--documents", "/app/documents"]
  restart: "no"
```

**Usage**:
```bash
# Add documents to ./all-rag-strategies/implementation/documents/
cp my-docs.pdf all-rag-strategies/implementation/documents/

# Run ingestion
docker compose -p localai --profile cpu --profile ingestion up rag-ingestion

# Monitor
docker logs -f rag_ingestion
```

#### rag-agent Service (Optional)

Purpose: Provide CLI/API interface for RAG queries

```yaml
rag-agent:
  build:
    context: ./all-rag-strategies/implementation
    dockerfile: Dockerfile.rag
  depends_on:
    db:
      condition: service_healthy
  environment:
    - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres
    - OPENAI_API_KEY=${OPENAI_API_KEY}
  volumes:
    - ./all-rag-strategies/implementation:/app
  command: ["uv", "run", "python", "rag_agent.py"]
  expose:
    - 8000/tcp
```

### 5.3 Environment Variables

**Critical for RAG + GPU**:

```bash
# Database (MUST use 'db' hostname for Supabase service)
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres
POSTGRES_PASSWORD=your-super-secret-and-long-postgres-password

# AI Providers
OPENAI_API_KEY=sk-your-key-here
LLM_CHOICE=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# GPU-related (optional for system tuning)
OLLAMA_NUM_PARALLEL=1        # Parallel inference threads
OLLAMA_NUM_THREAD=4          # CPU threads per inference
OLLAMA_GPU_LAYERS=0          # Let container auto-detect
```

### 5.4 Query Flow

```
User Input (Web UI)
    ↓
n8n Workflow (RAG Template)
    ↓
PostgreSQL Query (Vector Search)
    - Vector similarity: query_embedding vs stored chunks
    - Return top-k relevant chunks
    ↓
LLM Context Building (ollama-gpu)
    - Combine chunks with system prompt
    - Use dGPU for inference
    ↓
Response Generation
    ↓
Display in Web UI
```

---

## 6. Complete Startup Checklist

### Pre-Startup Verification

```bash
# 1. Verify GPU drivers and CUDA toolkit
nvidia-smi
# Should show: Driver 580.76.05, CUDA 13.0

# 2. Check NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.9.0-base-ubuntu22.04 nvidia-smi
# Should list GPU and report driver version inside container

# 3. Verify prime-run (optional, for native GPU apps)
prime-run nvidia-smi
# Should show NVIDIA GPU rendering offload

# 4. Check schema file exists
ls -la all-rag-strategies/implementation/sql/schema.sql

# 5. Verify .env file
grep "DATABASE_URL\|OPENAI_API_KEY" .env
```

### Startup Sequence

```bash
# 1. Start full stack with GPU support
python start_services.py --profile gpu-nvidia

# Wait ~30 seconds for all services to stabilize

# 2. Verify database schema initialized
docker exec -it $(docker ps -q -f "name=localai.*db") \
  psql -U postgres -d postgres -c "\dt"
# Should show: documents, chunks, embeddings_idx, etc.

# 3. Verify ollama-gpu has GPU access
docker exec ollama nvidia-smi
# Should list GeForce 940MX

# 4. Verify services are accessible
curl http://localhost:8001/api/v1/workflows  # n8n
curl http://localhost:8002               # Open WebUI
curl http://localhost:8005               # Supabase Studio

# 5. Monitor GPU usage
watch -n 1 nvidia-smi
# Should show GPU activity when running inferences
```

### Ingestion Process

```bash
# 1. Place documents
mkdir -p all-rag-strategies/implementation/documents
cp your-documents.pdf all-rag-strategies/implementation/documents/

# 2. Run ingestion with GPU profile (it uses CPU for processing)
docker compose -p localai --profile cpu --profile ingestion up rag-ingestion

# 3. Monitor progress
docker logs -f rag_ingestion

# 4. Verify documents in database
docker exec -it $(docker ps -q -f "name=localai.*db") \
  psql -U postgres -d postgres -c "SELECT COUNT(*) FROM documents;"
```

### Testing RAG Query

```bash
# 1. Access n8n workflow interface
# http://localhost:8001

# 2. Create or import RAG workflow
# Use database: postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres

# 3. Test query
# Should retrieve relevant chunks and generate answer with context

# 4. Monitor performance
# Watch GPU usage: watch -n 1 nvidia-smi
# Check logs: docker logs -f ollama
```

---

## 7. Troubleshooting Guide

### GPU Not Detected in Container

```bash
# Check 1: Host-level GPU access
nvidia-smi
# If fails, reinstall drivers

# Check 2: NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.9.0-base-ubuntu22.04 nvidia-smi
# If fails, reinstall toolkit: https://github.com/NVIDIA/nvidia-docker

# Check 3: Docker daemon config
sudo cat /etc/docker/daemon.json
# Should have: "runtimes": {"nvidia": {...}}

# Check 4: Compose file syntax
docker compose -p localai config --services | grep ollama
# Should list: ollama-cpu, ollama-gpu

# Check 5: Check profile activation
docker compose -p localai --profile gpu-nvidia config | grep -A 10 "ollama-gpu"
# Should show deploy.resources.reservations
```

### Database Schema Not Initialized

```bash
# Check 1: Schema file exists
ls all-rag-strategies/implementation/sql/schema.sql

# Check 2: Init directory populated
ls supabase/docker/volumes/db/init/02-rag-schema.sql

# Check 3: Database logs
docker logs $(docker ps -q -f "name=localai.*db")

# Check 4: Manually initialize (if needed)
docker exec -i $(docker ps -q -f "name=localai.*db") psql -U postgres -d postgres < \
  all-rag-strategies/implementation/sql/schema.sql

# Check 5: Verify schema created
docker exec -it $(docker ps -q -f "name=localai.*db") psql -U postgres -d postgres -c "\dt"
```

### Ingestion Fails

```bash
# Check 1: Database connectivity
docker logs rag_ingestion | grep "database\|DATABASE_URL"

# Check 2: API keys
docker logs rag_ingestion | grep "OPENAI\|API"

# Check 3: Document format
ls -la all-rag-strategies/implementation/documents/

# Check 4: Resource constraints
docker stats rag_ingestion

# Check 5: Full logs
docker logs -f rag_ingestion
```

### n8n Can't Connect to Database

```bash
# Check 1: Container network
docker network ls | grep localai

# Check 2: Service connectivity
docker exec n8n ping db
# Should respond (not "unknown host")

# Check 3: Port access
docker exec n8n psql postgresql://postgres:password@db:5432/postgres -c "SELECT 1"

# Check 4: Environment variables in n8n
docker exec n8n env | grep DATABASE
```

---

## 8. Performance Optimization

### GPU Configuration

```bash
# Adjust for your 940MX (2GB VRAM typical):
# In docker-compose.yml or via environment:

# Conservative (stable, safer)
OLLAMA_NUM_PARALLEL=1
OLLAMA_NUM_THREAD=2
# Load on GPU: 60-70%

# Moderate (balanced)
OLLAMA_NUM_PARALLEL=2
OLLAMA_NUM_THREAD=4
# Load on GPU: 80-90%

# Aggressive (higher throughput, may thermal throttle)
OLLAMA_NUM_PARALLEL=4
OLLAMA_NUM_THREAD=8
# Load on GPU: >90%, monitor temps
```

### Embedding Model Selection

```bash
# Fast, small (for 2GB GPU)
EMBEDDING_MODEL=text-embedding-3-small

# More accurate, requires more resources
EMBEDDING_MODEL=text-embedding-3-large

# For testing/CPU fallback
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Chunk Size Tuning

```bash
# In ingestion configuration:

# Smaller chunks (better precision, more embeddings)
chunk_size: 512
chunk_overlap: 100

# Larger chunks (faster processing, less precise)
chunk_size: 1024
chunk_overlap: 200
```

### Monitoring & Metrics

```bash
# Real-time GPU usage
watch -n 1 nvidia-smi

# Container resource usage
docker stats --no-stream

# Database query performance
docker exec -it $(docker ps -q -f "name=localai.*db") \
  psql -U postgres -d postgres << EOF
EXPLAIN ANALYZE
SELECT * FROM chunks 
WHERE embedding <-> (SELECT embedding FROM chunks LIMIT 1) 
LIMIT 5;
EOF

# Check index health
docker exec -it $(docker ps -q -f "name=localai.*db") \
  psql -U postgres -d postgres -c "\di+"
```

---

## 9. File References & Documentation Structure

### Key Files in Your Project

```
local-ai-packaged/
├── start_services.py                    # Enhanced with GPU & RAG support
├── docker-compose.yml                   # Main stack definition
├── .env                                 # Configuration (GPU, RAG, API keys)
├── all-rag-strategies/
│   └── implementation/
│       ├── sql/schema.sql              # RAG database schema
│       ├── documents/                  # Input documents for ingestion
│       ├── ingestion/ingest.py         # Document processing
│       └── rag_agent.py                # RAG query interface
└── supabase/docker/
    └── docker-compose.yml              # Supabase stack
```

### Documentation Files (Newly Created)

```
rag-integration-guide.md                 # Service definitions & setup
rag-integration-plan.pdf                 # 13-page comprehensive guide
GPU_CONFIGURATION_SUMMARY.md             # GPU setup verification
nvidia-docker.md                         # PRIME/Docker strategies
setup-rag-integration.sh                 # Automated setup script
[This Document]                          # Complete unified guide
```

---

## 10. Summary & Next Steps

### What You Now Have

✅ **GPU Support**:
- dGPU (NVIDIA 940MX) properly configured for Docker workloads
- iGPU (Intel HD) handling display for energy efficiency
- PRIME/prime-run ready for native GPU apps
- Proper NVIDIA Container Toolkit integration

✅ **RAG System**:
- Database schema automatically initialized at startup
- Two-stage initialization for reliability
- Ingestion pipeline for document processing
- Vector search for semantic retrieval
- Integration with n8n for workflow orchestration

✅ **Robust Infrastructure**:
- Dynamic container discovery (no hardcoded names)
- Comprehensive error handling
- Health checks and readiness probes
- Profile-based service activation

### Immediate Actions

1. **Verify Your Setup**:
   ```bash
   python start_services.py --profile gpu-nvidia
   ```

2. **Monitor Startup**:
   ```bash
   watch -n 1 nvidia-smi
   # In another terminal:
   docker logs -f localai-db-1
   docker logs -f ollama
   ```

3. **Test RAG**:
   - Add document to `all-rag-strategies/implementation/documents/`
   - Run ingestion: `docker compose -p localai --profile cpu --profile ingestion up`
   - Query via n8n workflow at http://localhost:8001

4. **Optimize**:
   - Adjust `OLLAMA_NUM_PARALLEL` for your 940MX
   - Monitor GPU usage to find sweet spot
   - Fine-tune chunk sizes for better retrieval

### Future Enhancements

- Multi-GPU support (if you upgrade)
- Custom embedding models
- Advanced retrieval strategies (reranking, fusion)
- Monitoring dashboard (Prometheus + Grafana)
- Production security hardening

---

## 11. Quick Reference Commands

```bash
# Startup
python start_services.py --profile gpu-nvidia

# Verify GPU in container
docker exec ollama nvidia-smi

# Check database
docker exec -it localai-db-1 psql -U postgres -d postgres -c "\dt"

# Ingest documents
docker compose -p localai --profile cpu --profile ingestion up rag-ingestion

# View logs
docker logs -f ollama           # LLM service
docker logs -f rag_ingestion    # Document processing
docker logs -f localai-db-1     # Database

# Monitor performance
watch -n 1 nvidia-smi           # GPU usage
docker stats --no-stream        # Container resources

# Access services
curl http://localhost:8001      # n8n (workflows)
curl http://localhost:8002      # Open WebUI (chat)
curl http://localhost:8005      # Supabase Studio (DB management)

# Troubleshoot
docker compose -p localai config --services
docker network inspect localai_default
docker exec db pg_isready -U postgres
```

---

**Document Version**: 2.0  
**Last Updated**: November 12, 2025  
**Status**: Complete Integration Ready
