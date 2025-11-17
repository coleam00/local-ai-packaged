# RAG Integration Guide - Complete Implementation

This guide walks you through integrating the advanced RAG strategies from `all-rag-strategies` into your `local-ai-packaged` ecosystem.

## Overview

We're connecting two systems:
- **local-ai-packaged**: Your existing n8n + Open WebUI + Supabase infrastructure
- **all-rag-strategies**: Advanced RAG implementation with multiple retrieval strategies

## Phase 1: File Placement and Setup

### Step 1.1: Save the Enhanced start_services.py

Replace your current `start_services.py` with the enhanced version from Artifact 1.

**Key changes:**
- Added `prepare_rag_schema()` - Copies RAG schema to Supabase init directory
- Added `wait_for_database()` - Waits for Supabase to be ready
- Added `verify_rag_schema()` - Confirms RAG tables and functions exist
- Added `initialize_rag_database()` - Orchestrates the schema setup

**Location:** `local-ai-packaged/start_services.py`

### Step 1.2: Update docker-compose.yml

Replace your `docker-compose.yml` with the enhanced version from Artifact 2.

**New services added:**
- `rag-ingestion`: On-demand service for populating the knowledge base
- `rag-agent`: Always-running service that provides RAG API endpoints

**Location:** `local-ai-packaged/docker-compose.yml`

### Step 1.3: Create Dockerfile for RAG Services

Create a new file `Dockerfile.rag` in the `all-rag-strategies/implementation/` directory using Artifact 3.

**Location:** `local-ai-packaged/all-rag-strategies/implementation/Dockerfile.rag`

### Step 1.4: Create FastAPI Service

Create `api.py` in the `all-rag-strategies/implementation/` directory using Artifact 4.

This provides HTTP endpoints for:
- `/chat` - Conversational RAG access
- `/chat/stream` - Streaming responses
- `/search` - Direct document search
- `/documents` - List/retrieve documents

**Location:** `local-ai-packaged/all-rag-strategies/implementation/api.py`

## Phase 2: Verify Directory Structure

Your directory structure should now look like this:

```
local-ai-packaged/
├── start_services.py              # ← Updated (Artifact 1)
├── docker-compose.yml             # ← Updated (Artifact 2)
├── .env                           # Existing (no changes needed)
├── supabase/                      # Created by start_services.py
│   └── docker/
│       ├── docker-compose.yml
│       └── volumes/
│           └── db/
│               └── init/
│                   └── 02-rag-schema.sql  # ← Auto-created by start_services.py
├── all-rag-strategies/
│   └── implementation/
│       ├── Dockerfile.rag         # ← New (Artifact 3)
│       ├── api.py                 # ← New (Artifact 4)
│       ├── cli.py                 # Existing
│       ├── rag_agent.py           # Existing
│       ├── rag_agent_advanced.py  # Existing
│       ├── sql/
│       │   └── schema.sql         # Existing (source for RAG schema)
│       ├── ingestion/             # Existing
│       │   ├── ingest.py
│       │   ├── chunker.py
│       │   ├── embedder.py
│       │   └── contextual_enrichment.py
│       ├── utils/                 # Existing
│       │   ├── db_utils.py
│       │   ├── models.py
│       │   └── providers.py
│       ├── documents/             # Existing (put your docs here)
│       └── requirements-advanced.txt  # Existing
├── n8n/
├── searxng/
└── ... (other existing directories)
```

## Phase 3: Environment Configuration

### Step 3.1: Verify .env File

Your `.env` file should already have these critical variables (no changes needed if they're already set):

```env
# Database (for RAG)
POSTGRES_PASSWORD=your-super-secret-password
DATABASE_URL="postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres"

# AI Configuration
OPENAI_API_KEY=your-openai-api-key
LLM_CHOICE=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# Other existing variables...
```

**Important Notes:**
- `DATABASE_URL` uses hostname `db` (the Supabase PostgreSQL service name)
- Do NOT use special characters like `@` in `POSTGRES_PASSWORD`
- The enhanced `start_services.py` will use these to connect and verify the database

## Phase 4: Initial Startup

### Step 4.1: Start the Services

```bash
# From the local-ai-packaged directory
python start_services.py --profile cpu

# Or for GPU:
python start_services.py --profile gpu-nvidia
```

**What happens:**
1. Clones/updates Supabase repository
2. Copies .env to Supabase directory
3. **Copies RAG schema.sql to Supabase init directory**
4. Stops any existing containers
5. Starts Supabase services
6. **Waits for database to be ready** (new!)
7. **Verifies RAG schema was applied** (new!)
8. Starts local AI services (including new rag-agent)

**Expected Output:**
```
==============================================================
RAG Database Initialization
==============================================================
Waiting for Supabase database to be ready...
✓ Database is ready (attempt 3/30)
Database ready, waiting 3 seconds for stabilization...
✓ RAG schema verification successful:
  ✓ documents table present
  ✓ chunks table present
  ✓ match_chunks() function present
  ✓ pgvector extension enabled
✓ RAG database initialization complete
==============================================================
✓ All services started successfully!
==============================================================
```

### Step 4.2: Verify Services are Running

```bash
# Check all services
docker ps

# You should see (among others):
# - supabase-db
# - rag_agent
# - n8n
# - open-webui
```

### Step 4.3: Manual Schema Verification (Optional)

If you want to double-check the schema was applied:

```bash
# Connect to Supabase database
docker compose -p localai exec db psql -U postgres

# Inside psql:
\dt           # List tables (should see documents, chunks)
\df           # List functions (should see match_chunks)
\dx vector    # Check pgvector extension
\q            # Exit
```

## Phase 5: Document Ingestion

### Step 5.1: Prepare Documents

Place your documents in the `documents/` directory:

```bash
# Example structure
all-rag-strategies/implementation/documents/
├── company_policies.pdf
├── technical_documentation.docx
├── product_guide.md
└── meeting_recording.mp3
```

**Supported formats:**
- PDF, Word (.docx), PowerPoint (.pptx)
- Markdown (.md), Text (.txt), HTML
- Audio (.mp3) - automatically transcribed with Whisper

### Step 5.2: Run Ingestion

```bash
# Basic ingestion (uses context-aware chunking)
docker compose -p localai --profile ingestion up

# With contextual enrichment (Anthropic's method, more expensive but better)
# Note: You'll need to modify the command in docker-compose.yml to add --contextual flag
```

**What happens during ingestion:**
1. Clears existing documents/chunks (fresh start)
2. Processes all documents in the `documents/` folder
3. Converts to Markdown (via Docling)
4. Chunks intelligently (Docling HybridChunker)
5. Optionally enriches chunks with context
6. Generates embeddings (OpenAI)
7. Stores in PostgreSQL with pgvector

**Expected output:**
```
Processing document: company_policies.pdf
✓ Converted to Markdown
✓ Created 45 chunks
✓ Generated embeddings
✓ Stored in database

Processing document: meeting_recording.mp3
✓ Transcribed with Whisper
✓ Created 12 chunks
✓ Generated embeddings
✓ Stored in database

Ingestion complete! Processed 4 documents, created 120 chunks.
```

### Step 5.3: Verify Ingestion

```bash
# Check via API
curl http://localhost:8000/documents

# Or via database
docker compose -p localai exec db psql -U postgres -c "SELECT COUNT(*) FROM documents;"
docker compose -p localai exec db psql -U postgres -c "SELECT COUNT(*) FROM chunks;"
```

## Phase 6: Testing the RAG Agent

### Test 6.1: Direct API Test

```bash
# Health check
curl http://localhost:8000/health

# Simple search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are our company policies?",
    "limit": 5,
    "strategy": "standard"
  }'

# Chat (conversational)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about our vacation policy",
    "session_id": "test-session"
  }'
```

### Test 6.2: Using the CLI

```bash
# Enter the rag-agent container
docker compose -p localai exec rag-agent bash

# Run the CLI
python cli.py

# Try some queries:
# - "What topics are covered in the knowledge base?"
# - "Tell me about [specific topic from your documents]"
```

### Test 6.3: Different Strategies

```bash
# Multi-query (for ambiguous queries)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python development",
    "strategy": "multi-query"
  }'

# Re-ranking (for precision)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "legal compliance requirements",
    "strategy": "reranking"
  }'

# Self-reflection (for complex questions)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the implications of our AI ethics policy?",
    "strategy": "self-reflection"
  }'
```

## Phase 7: Integration with n8n and Open WebUI

### Integration 7.1: Update n8n Workflow

Your existing n8n workflow needs to be updated to call the RAG agent API instead of (or in addition to) its current logic.

**Steps:**
1. Access n8n at `http://localhost:5678`
2. Open your RAG agent workflow
3. Add an HTTP Request node:
   - Method: POST
   - URL: `http://rag-agent:8000/chat`
   - Body:
     ```json
     {
       "message": "{{ $json.query }}",
       "session_id": "{{ $json.session_id }}",
       "strategy": "auto"
     }
     ```
4. Process the response and return to Open WebUI

### Integration 7.2: Update Open WebUI Pipeline

Your `n8n_pipe.py` in Open WebUI can be updated to call the RAG agent directly:

```python
# Add to n8n_pipe.py
import requests

def call_rag_agent(query, session_id):
    response = requests.post(
        "http://rag-agent:8000/chat",
        json={
            "message": query,
            "session_id": session_id,
            "stream": False
        }
    )
    return response.json()["response"]
```

### Integration 7.3: Test End-to-End

1. Open Open WebUI at `http://localhost:3000`
2. Select your n8n RAG agent from the model dropdown
3. Ask a question about your documents
4. Verify you get a response with source citations

## Phase 8: Monitoring and Troubleshooting

### Monitoring

```bash
# View all logs
docker compose -p localai logs -f

# View specific service logs
docker compose -p localai logs -f rag-agent
docker compose -p localai logs -f db

# Check service health
curl http://localhost:8000/health
```

### Common Issues

#### Issue: Schema not applied
**Symptom:** Agent fails with "relation 'documents' does not exist"

**Solution:**
```bash
# Manually apply schema
docker compose -p localai exec db psql -U postgres < all-rag-strategies/implementation/sql/schema.sql

# Or restart with fresh volumes
docker compose -p localai down -v
python start_services.py --profile cpu
```

#### Issue: Ingestion fails
**Symptom:** "Cannot connect to database"

**Solution:**
```bash
# Check database is running and healthy
docker compose -p localai ps db
docker compose -p localai logs db

# Verify DATABASE_URL in .env uses correct password
# Ensure no special characters like @ in POSTGRES_PASSWORD
```

#### Issue: RAG agent can't find documents
**Symptom:** "No relevant information found"

**Solution:**
```bash
# Check if documents were ingested
docker compose -p localai exec db psql -U postgres -c "SELECT COUNT(*) FROM chunks;"

# Re-run ingestion if needed
docker compose -p localai --profile ingestion up
```

## Phase 9: Advanced Features

### Feature 9.1: Contextual Enrichment

To enable Anthropic's contextual retrieval method (35-49% better accuracy):

1. Update the ingestion command in `docker-compose.yml`:
```yaml
rag-ingestion:
  # ... existing config ...
  command: ["python", "-m", "ingestion.ingest", "--documents", "/app/documents", "--contextual"]
```

2. Run ingestion:
```bash
docker compose -p localai --profile ingestion up
```

**Note:** This adds 1 LLM API call per chunk, increasing cost and time.

### Feature 9.2: Custom Chunking

Adjust chunk size for your specific needs:

```yaml
rag-ingestion:
  # ... existing config ...
  command: ["python", "-m", "ingestion.ingest", "--documents", "/app/documents", "--chunk-size", "800", "--chunk-overlap", "150"]
```

### Feature 9.3: Streaming Responses

For real-time streaming (better UX):

```bash
# Via API
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain our data privacy policy",
    "session_id": "test"
  }'
```

## Phase 10: Production Considerations

### Security

- [ ] Change all default passwords in `.env`
- [ ] Enable SSL/TLS via Caddy
- [ ] Restrict database access (firewall rules)
- [ ] Use secrets management (not plain .env)

### Performance

- [ ] Monitor embedding API usage (OpenAI costs)
- [ ] Consider caching frequent queries
- [ ] Use connection pooling (already configured)
- [ ] Monitor database size (pgvector indexes)

### Backup

```bash
# Backup database
docker compose -p localai exec db pg_dump -U postgres > backup.sql

# Backup documents
tar -czf documents-backup.tar.gz all-rag-strategies/implementation/documents/
```

### Scaling

- Consider separating ingestion and query services
- Use read replicas for high query volume
- Implement Redis for conversation history (instead of in-memory)
- Add rate limiting to API endpoints

## Summary Checklist

- [ ] Phase 1: Files placed and configured
- [ ] Phase 2: Directory structure verified
- [ ] Phase 3: Environment variables set
- [ ] Phase 4: Services started successfully
- [ ] Phase 5: Documents ingested
- [ ] Phase 6: RAG agent tested
- [ ] Phase 7: n8n/Open WebUI integrated
- [ ] Phase 8: Monitoring configured
- [ ] Phase 9: Advanced features explored
- [ ] Phase 10: Production readiness assessed

## Getting Help

If you encounter issues:

1. Check the logs: `docker compose -p localai logs -f [service-name]`
2. Verify environment variables: `cat .env`
3. Test database connection: `docker compose -p localai exec db psql -U postgres`
4. Test RAG agent health: `curl http://localhost:8000/health`

---

**You now have a fully integrated advanced RAG system running in your local AI ecosystem!** 🎉
