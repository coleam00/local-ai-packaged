# Docker Compose Service Additions for RAG Integration

This document provides the service definitions that should be added to your main `docker-compose.yml` file to complete the RAG integration.

## Services to Add

### 1. RAG Ingestion Service

Add this service definition to enable document ingestion into the RAG knowledge base:

```yaml
  # RAG Document Ingestion Service
  rag-ingestion:
    build:
      context: ./all-rag-strategies/implementation
      dockerfile: Dockerfile.rag
    container_name: rag_ingestion
    profiles:
      - ingestion
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LLM_CHOICE=${LLM_CHOICE:-gpt-4o-mini}
      - EMBEDDING_MODEL=${EMBEDDING_MODEL:-text-embedding-3-small}
    volumes:
      - ./all-rag-strategies/implementation/documents:/app/documents
      - ./all-rag-strategies/implementation:/app
      - ./.env:/app/.env
    command: ["uv", "run", "python", "ingestion/ingest.py", "--documents", "/app/documents"]
    restart: "no"
```

**Key Points:**
- Uses profile `ingestion` so it only runs when explicitly requested
- Depends on Supabase `db` service being healthy
- Mounts the documents directory for processing
- Uses the main project's `.env` file
- Restart policy is "no" since ingestion is a one-time operation

### 2. RAG Agent Service (Optional)

If you want to run the RAG agent as a standalone service (separate from n8n integration):

```yaml
  # RAG Agent Service (Optional - for standalone CLI usage)
  rag-agent:
    build:
      context: ./all-rag-strategies/implementation
      dockerfile: Dockerfile.rag
    container_name: rag_agent
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LLM_CHOICE=${LLM_CHOICE:-gpt-4o-mini}
      - EMBEDDING_MODEL=${EMBEDDING_MODEL:-text-embedding-3-small}
    volumes:
      - ./all-rag-strategies/implementation:/app
      - ./.env:/app/.env
    command: ["uv", "run", "python", "rag_agent.py"]
    expose:
      - 8000/tcp
```

**Note:** This service is optional because:
- The RAG functionality is primarily accessed through n8n workflows
- This service is useful for CLI testing and standalone usage
- It's not required if you only use the RAG system via n8n

## Installation Steps

### Step 1: Add Services to docker-compose.yml

1. Open your main `docker-compose.yml` file
2. Add the `rag-ingestion` service definition under the `services:` section
3. Optionally add the `rag-agent` service if you want standalone  z access

### Step 2: Create Dockerfile for RAG Services

Create `all-rag-strategies/implementation/Dockerfile.rag`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv for fast Python package management
RUN pip install uv

# Copy requirements and install dependencies
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Default command (can be overridden in docker-compose)
CMD ["uv", "run", "python", "rag_agent.py"]
```

### Step 3: Update Environment Variables

Ensure your `.env` file contains these variables:

```bash
# Database Configuration (for RAG)
DATABASE_URL=postgresql://postgres:your-password@db:5432/postgres
POSTGRES_PASSWORD=your-super-secret-and-long-postgres-password

# AI Provider Configuration
OPENAI_API_KEY=your-openai-api-key
LLM_CHOICE=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# Optional: Alternative AI Providers
# ANTHROPIC_API_KEY=
# GEMINI_API_KEY=
```

## Usage

### Running the Ingestion Service

To ingest documents into your RAG knowledge base:

```bash
# Start the ingestion service with the ingestion profile
docker compose -p localai --profile ingestion up rag-ingestion

# Or if you're using the full stack:
docker compose -p localai --profile cpu --profile ingestion up -d
```

### Running the RAG Agent (if included)

The RAG agent will start automatically with your main stack if you've added it without a profile.

### Verifying Integration

1. **Check Database Schema:**
   ```bash
   docker exec -it supabase-db psql -U postgres -d postgres -c "\dt"
   ```
   You should see tables like `documents`, `chunks`, etc.

2. **Check Ingestion Logs:**
   ```bash
   docker logs rag_ingestion
   ```

3. **Test RAG Query:**
   - Access n8n at http://localhost:8001
   - Use the RAG workflow to test queries
   - Or use the RAG agent CLI if you included that service

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Local AI Stack                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   Open WebUI │──────│     n8n      │                    │
│  └──────────────┘      └───────┬──────┘                    │
│                                 │                            │
│                                 ▼                            │
│                        ┌────────────────┐                   │
│                        │  RAG Workflow  │                   │
│                        └────────┬───────┘                   │
│                                 │                            │
│                                 ▼                            │
│  ┌─────────────────────────────────────────────┐           │
│  │         Supabase PostgreSQL + pgvector       │           │
│  │  ┌────────────┐  ┌────────────┐             │           │
│  │  │ documents  │  │   chunks   │             │           │
│  │  │   table    │  │   table    │             │           │
│  │  └────────────┘  └────────────┘             │           │
│  └─────────────────────────────────────────────┘           │
│                        ▲                                     │
│                        │                                     │
│              ┌─────────┴─────────┐                         │
│              │                    │                         │
│    ┌─────────┴────────┐  ┌──────┴────────┐               │
│    │  rag-ingestion   │  │   rag-agent   │ (optional)    │
│    │  (on-demand)     │  │  (CLI/API)    │               │
│    └──────────────────┘  └───────────────┘               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Issue: Schema not initialized

**Solution:** Run the enhanced start_services.py script which includes schema initialization:
```bash
python start_services_enhanced.py --profile cpu
```

### Issue: Ingestion fails with database connection error

**Check:**
1. Is the Supabase db service healthy? `docker ps | grep supabase-db`
2. Is the DATABASE_URL correct in your .env file?
3. Can you connect manually? `docker exec -it supabase-db psql -U postgres`

### Issue: Documents not being ingested

**Check:**
1. Are documents in the correct location? `./all-rag-strategies/implementation/documents/`
2. Are they in supported formats? (PDF, TXT, MD, etc.)
3. Check ingestion logs: `docker logs rag_ingestion`

## Next Steps

1. **Update start_services.py**: Replace your current `start_services.py` with the enhanced version that includes RAG schema initialization
2. **Add Services**: Add the service definitions above to your `docker-compose.yml`
3. **Create Dockerfile**: Create the `Dockerfile.rag` in the appropriate location
4. **Test Integration**: Run the full stack and verify RAG functionality
5. **Ingest Documents**: Use the ingestion service to populate your knowledge base
6. **Update n8n Workflow**: Ensure your n8n workflow is configured to use the RAG database
