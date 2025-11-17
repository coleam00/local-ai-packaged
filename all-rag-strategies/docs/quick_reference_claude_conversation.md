# RAG Integration - Quick Reference Card

## Essential Commands

### Starting/Stopping Services

```bash
# Start everything (CPU mode)
python start_services.py --profile cpu

# Start with GPU support
python start_services.py --profile gpu-nvidia

# Stop all services
docker compose -p localai down

# Stop and remove ALL data (⚠️ DESTRUCTIVE)
docker compose -p localai down -v
```

### Document Ingestion

```bash
# Basic ingestion (fast, good quality)
docker compose -p localai --profile ingestion up

# With contextual enrichment (slow, best quality)
# First, edit docker-compose.yml rag-ingestion command to add --contextual
docker compose -p localai --profile ingestion up

# Check ingestion status
docker compose -p localai logs -f rag-ingestion
```

### Testing RAG Agent

```bash
# Health check
curl http://localhost:8000/health

# Search documents
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are our company policies?", "session_id": "test"}'

# List documents
curl http://localhost:8000/documents

# Interactive CLI
docker compose -p localai exec rag-agent python cli.py
```

### Database Operations

```bash
# Connect to database
docker compose -p localai exec db psql -U postgres

# Count documents and chunks
docker compose -p localai exec db psql -U postgres -c "SELECT COUNT(*) FROM documents;"
docker compose -p localai exec db psql -U postgres -c "SELECT COUNT(*) FROM chunks;"

# Verify schema
docker compose -p localai exec db psql -U postgres -c "\dt"
docker compose -p localai exec db psql -U postgres -c "\df match_chunks"
```

### Viewing Logs

```bash
# All services
docker compose -p localai logs -f

# Specific service
docker compose -p localai logs -f rag-agent
docker compose -p localai logs -f db
docker compose -p localai logs -f n8n
```

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| RAG Agent API | http://localhost:8000 | RAG endpoints |
| n8n | http://localhost:5678 | Workflow automation |
| Open WebUI | http://localhost:3000 | Chat interface |
| Supabase Studio | http://localhost:8005 | Database UI |
| Langfuse | http://localhost:8007 | LLM observability |

## RAG Strategies

Use `"strategy"` parameter in API calls:

| Strategy | When to Use | Cost | Latency |
|----------|-------------|------|---------|
| `standard` | Most queries | $ | ⚡⚡⚡ |
| `multi-query` | Ambiguous questions | $$ | ⚡⚡ |
| `reranking` | Precision-critical | $$ | ⚡⚡ |
| `self-reflection` | Complex research | $$$ | ⚡ |

Example:
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "legal compliance", "strategy": "reranking"}'
```

## Common Issues & Quick Fixes

### Database not ready
```bash
# Wait 30 seconds and retry, or check logs
docker compose -p localai logs db
```

### Schema missing
```bash
# Manually apply schema
docker compose -p localai exec db psql -U postgres < all-rag-strategies/implementation/sql/schema.sql
```

### Ingestion fails
```bash
# Check database connection
docker compose -p localai exec rag-ingestion env | grep DATABASE_URL

# Restart ingestion
docker compose -p localai --profile ingestion down
docker compose -p localai --profile ingestion up
```

### No search results
```bash
# Verify documents exist
curl http://localhost:8000/documents

# Check chunk count
docker compose -p localai exec db psql -U postgres -c "SELECT COUNT(*) FROM chunks;"

# Re-ingest if needed
docker compose -p localai --profile ingestion up
```

## File Locations

```
local-ai-packaged/
├── start_services.py          # Main startup script
├── docker-compose.yml         # Service definitions
├── .env                       # Configuration
├── all-rag-strategies/
│   └── implementation/
│       ├── api.py             # RAG API service
│       ├── Dockerfile.rag     # RAG container
│       ├── documents/         # 📁 PUT YOUR DOCS HERE
│       └── sql/schema.sql     # Database schema
└── supabase/
    └── docker/
        └── volumes/
            └── db/
                └── init/
                    └── 02-rag-schema.sql  # Auto-created
```

## Environment Variables Checklist

Required in `.env`:
```env
POSTGRES_PASSWORD=xxx          # No @ symbol!
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres
OPENAI_API_KEY=xxx
LLM_CHOICE=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

## API Endpoints Reference

### POST /chat
Conversational RAG access
```json
{
  "message": "your question",
  "session_id": "unique-id",
  "strategy": "auto"
}
```

### POST /chat/stream
Streaming responses (SSE)

### POST /search
Direct document search
```json
{
  "query": "search term",
  "limit": 5,
  "strategy": "standard"
}
```

### GET /documents
List all documents in knowledge base

### GET /documents/{id}
Retrieve specific document

### GET /health
Service health check

### POST /sessions/{id}/clear
Clear conversation history

## Backup & Restore

### Backup
```bash
# Database
docker compose -p localai exec db pg_dump -U postgres > backup-$(date +%Y%m%d).sql

# Documents
tar -czf docs-backup-$(date +%Y%m%d).tar.gz all-rag-strategies/implementation/documents/

# Environment
cp .env .env.backup
```

### Restore
```bash
# Database
docker compose -p localai exec -T db psql -U postgres < backup.sql

# Documents
tar -xzf docs-backup.tar.gz -C all-rag-strategies/implementation/
```

## Performance Tuning

### Chunk Size Optimization
```yaml
# In docker-compose.yml rag-ingestion command:
--chunk-size 800    # Smaller = more precise, more chunks
--chunk-size 1500   # Larger = more context, fewer chunks
```

### Database Connection Pool
```python
# In utils/db_utils.py
min_size=5          # Minimum connections
max_size=20         # Maximum connections
```

### Embedding Cache
Already configured in `ingestion/embedder.py` - no changes needed

## Monitoring

### Resource Usage
```bash
# Container stats
docker stats

# Disk usage
docker system df

# Database size
docker compose -p localai exec db psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('postgres'));"
```

### API Performance
```bash
# Response time test
time curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test query"}'
```

## Troubleshooting Decision Tree

```
Problem: Can't connect to RAG agent
├─ Check: docker compose -p localai ps rag-agent
│  └─ Not running? → docker compose -p localai logs rag-agent
│
Problem: No search results
├─ Check: curl http://localhost:8000/documents
│  ├─ Empty? → Re-run ingestion
│  └─ Has docs? → Try different query or strategy
│
Problem: Database error
├─ Check: docker compose -p localai logs db
│  ├─ Connection refused? → Wait 30s, db still starting
│  └─ Schema error? → Apply schema manually
│
Problem: Ingestion fails
├─ Check: docker compose -p localai logs rag-ingestion
│  ├─ DB connection error? → Verify DATABASE_URL
│  └─ File error? → Check documents/ directory
```

## Quick Start from Scratch

```bash
# 1. Clone and navigate
cd local-ai-packaged

# 2. Set up environment
cp .env.example .env
# Edit .env with your keys

# 3. Start everything
python start_services.py --profile cpu

# 4. Add documents
cp your_documents/* all-rag-strategies/implementation/documents/

# 5. Ingest documents
docker compose -p localai --profile ingestion up

# 6. Test
curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What can you tell me?"}'

# 7. Use via Open WebUI
# Go to http://localhost:3000
```

---

**Save this reference for quick access to common operations!**
