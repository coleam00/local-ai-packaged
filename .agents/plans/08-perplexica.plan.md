# Plan: Perplexica Integration (GitHub Issue #157)

## Summary

Add Perplexica as a new AI-powered search service to the local AI stack. Perplexica provides a "Perplexity AI" style search experience using local LLMs via Ollama and SearXNG for web search results. The implementation adds the Perplexica Docker service, integrates it with the existing SearXNG and Ollama services, configures Caddy reverse proxy routing, adds environment variables, and registers it in the Management UI for service control and monitoring.

## External Research

### Documentation
- [Perplexica GitHub Repository](https://github.com/ItzCrazyKns/Perplexica) - Official repository with Docker setup
- [Perplexica Docker Hub](https://hub.docker.com/r/itzcrazykns1337/perplexica) - Official Docker image

### Key Configuration Details
- **Docker Image**: `itzcrazykns1337/perplexica:latest` (full) or `itzcrazykns1337/perplexica:slim-latest` (for external SearXNG)
- **Default Port**: 3000 (web UI)
- **Data Volumes**:
  - `/home/perplexica/data` - configuration and database
  - `/home/perplexica/uploads` - file uploads
- **Key Environment Variable**: `SEARXNG_API_URL` - URL to SearXNG instance with JSON format enabled

### Gotchas & Best Practices Found
1. **SearXNG JSON format required**: SearXNG must have JSON format enabled in `settings.yml` - ALREADY DONE in this project (verified in `/opt/local-ai-packaged/searxng/settings.yml`)
2. **SearXNG rate limiting**: Should be disabled for internal use - ALREADY DONE (`limiter: false`)
3. **Ollama connectivity**: Use container network name `http://ollama:11434` (NOT `host.docker.internal`)
4. **Use slim image**: Since SearXNG already exists in stack, use `itzcrazykns1337/perplexica:slim-latest` to avoid bundled SearXNG
5. **First-run configuration**: Perplexica has a setup wizard on first run via web UI to configure LLM providers
6. **Port conflict**: Default port 3000 conflicts with `langfuse-web` - must use different port (8010)

## Patterns to Mirror

### Docker Compose Service Definition Pattern
FROM: `/opt/local-ai-packaged/docker-compose.yml:321-343` (searxng service)
```yaml
  searxng:
    container_name: searxng
    image: docker.io/searxng/searxng:latest
    restart: unless-stopped
    expose:
      - 8080/tcp
    volumes:
      - ./searxng:/etc/searxng:rw
    environment:
      - SEARXNG_BASE_URL=https://${SEARXNG_HOSTNAME:-localhost}/
      - UWSGI_WORKERS=${SEARXNG_UWSGI_WORKERS:-4}
      - UWSGI_THREADS=${SEARXNG_UWSGI_THREADS:-4}
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    logging:
      driver: "json-file"
      options:
        max-size: "1m"
        max-file: "1"
```

### Caddy Reverse Proxy Pattern
FROM: `/opt/local-ai-packaged/Caddyfile:23-26` (langfuse example)
```
# Langfuse
{$LANGFUSE_HOSTNAME} {
    reverse_proxy langfuse-web:3000
}
```

### Private Port Exposure Pattern
FROM: `/opt/local-ai-packaged/docker-compose.override.private.yml:52-54` (searxng)
```yaml
  searxng:
    ports:
      - 127.0.0.1:8081:8080
```

### Environment Variable Pattern
FROM: `/opt/local-ai-packaged/.env.example:73-81`
```bash
# N8N_HOSTNAME=n8n.yourdomain.com
# WEBUI_HOSTNAME=openwebui.yourdomain.com
# FLOWISE_HOSTNAME=flowise.yourdomain.com
# SUPABASE_HOSTNAME=supabase.yourdomain.com
# LANGFUSE_HOSTNAME=langfuse.yourdomain.com
# OLLAMA_HOSTNAME=ollama.yourdomain.com
# SEARXNG_HOSTNAME=searxng.yourdomain.com
```

### Caddy Environment Variable Pattern
FROM: `/opt/local-ai-packaged/docker-compose.yml:137-146`
```yaml
    environment:
      - N8N_HOSTNAME=${N8N_HOSTNAME:-":8001"}
      - WEBUI_HOSTNAME=${WEBUI_HOSTNAME:-":8002"}
      - FLOWISE_HOSTNAME=${FLOWISE_HOSTNAME:-":8003"}
      - OLLAMA_HOSTNAME=${OLLAMA_HOSTNAME:-":8004"}
      - SUPABASE_HOSTNAME=${SUPABASE_HOSTNAME:-":8005"}
      - SEARXNG_HOSTNAME=${SEARXNG_HOSTNAME:-":8006"}
      - LANGFUSE_HOSTNAME=${LANGFUSE_HOSTNAME:-":8007"}
      - NEO4J_HOSTNAME=${NEO4J_HOSTNAME:-":8008"}
```

### Service Dependencies Registration Pattern
FROM: `/opt/local-ai-packaged/management-ui/backend/app/core/service_dependencies.py:296-304`
```python
    "searxng": ServiceConfig(
        name="searxng",
        display_name="SearXNG",
        description="Privacy-respecting metasearch engine",
        group="infrastructure",
        dependencies=[],
        default_enabled=True,
        category="optional"
    ),
```

### Frontend Service URL Pattern
FROM: `/opt/local-ai-packaged/management-ui/frontend/src/utils/serviceUrls.ts:12-29`
```typescript
const SERVICE_URL_MAP: Record<string, ServiceUrlConfig> = {
  // Direct port access (from docker-compose.override.private.yml)
  'n8n': { port: 5678, name: 'n8n' },
  'open-webui': { port: 8080, name: 'Open WebUI' },
  'flowise': { port: 3001, name: 'Flowise' },
  'langfuse-web': { port: 3000, name: 'Langfuse' },
  ...
  'searxng': { port: 8081, name: 'SearXNG' },
  ...
};
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `docker-compose.yml` | UPDATE | Add perplexica service definition and volume |
| `docker-compose.override.private.yml` | UPDATE | Expose Perplexica port locally (127.0.0.1:8010:3000) |
| `Caddyfile` | UPDATE | Add Perplexica reverse proxy entry |
| `.env.example` | UPDATE | Add PERPLEXICA_HOSTNAME variable |
| `management-ui/backend/app/core/service_dependencies.py` | UPDATE | Register Perplexica in service configs and groups |
| `management-ui/frontend/src/utils/serviceUrls.ts` | UPDATE | Add Perplexica URL mapping |

## NOT Building

- **Custom Perplexica configuration file**: First-run setup wizard handles LLM configuration via web UI
- **Embedded SearXNG instance**: Using existing SearXNG service via slim Docker image
- **Automatic model pulling**: User configures preferred models via Perplexica UI after startup
- **API key configuration in .env**: Perplexica stores config in its data volume, not via environment variables
- **Ollama service dependency**: Perplexica can work with external LLM providers, not requiring Ollama

## Tasks

### Task 1: Add perplexica volume to docker-compose.yml

**Why**: Perplexica requires persistent storage for configuration and uploads.

**Mirror**: `/opt/local-ai-packaged/docker-compose.yml:4-16` (volumes section)

**Do**:
Add `perplexica-data` and `perplexica-uploads` volumes after `langfuse_minio_data`:
```yaml
volumes:
  n8n_storage:
  ollama_storage:
  qdrant_storage:
  open-webui:
  flowise:
  caddy-data:
  caddy-config:
  valkey-data:
  langfuse_postgres_data:
  langfuse_clickhouse_data:
  langfuse_clickhouse_logs:
  langfuse_minio_data:
  perplexica-data:
  perplexica-uploads:
```

**Don't**:
- Add volume driver options (not needed)
- Use named volume with explicit `name:` property

**Verify**: `docker compose -f /opt/local-ai-packaged/docker-compose.yml config 2>&1 | grep -A2 perplexica`

---

### Task 2: Add Perplexica service to docker-compose.yml

**Why**: Define the Perplexica container with proper configuration for internal SearXNG and Ollama connectivity.

**Mirror**: `/opt/local-ai-packaged/docker-compose.yml:321-343` (searxng service pattern)

**Do**:
Add the perplexica service after the searxng service definition (before ollama-cpu):
```yaml
  perplexica:
    container_name: perplexica
    image: itzcrazykns1337/perplexica:slim-latest
    restart: unless-stopped
    expose:
      - 3000/tcp
    volumes:
      - perplexica-data:/home/perplexica/data
      - perplexica-uploads:/home/perplexica/uploads
    environment:
      - SEARXNG_API_URL=http://searxng:8080
    depends_on:
      - searxng
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    logging:
      driver: "json-file"
      options:
        max-size: "1m"
        max-file: "1"
```

**Don't**:
- Use `ports:` directive (only `expose:` - ports are handled by override file)
- Add Ollama as hard dependency (Perplexica can use other providers)
- Use the full `perplexica:latest` image (has embedded SearXNG we don't need)

**Verify**: `docker compose -f /opt/local-ai-packaged/docker-compose.yml config --services | grep perplexica`

---

### Task 3: Add PERPLEXICA_HOSTNAME to Caddy environment in docker-compose.yml

**Why**: Caddy needs the hostname variable to configure reverse proxy routing.

**Mirror**: `/opt/local-ai-packaged/docker-compose.yml:137-146` (caddy environment)

**Do**:
Add PERPLEXICA_HOSTNAME after NEO4J_HOSTNAME in the caddy service environment section:
```yaml
      - PERPLEXICA_HOSTNAME=${PERPLEXICA_HOSTNAME:-":8010"}
```

Note: Using port 8010 as 8009 is used by management-ui.

**Don't**:
- Change the default port ordering scheme
- Use port 3000 (conflicts with langfuse-web)

**Verify**: `grep -A20 "caddy:" /opt/local-ai-packaged/docker-compose.yml | grep PERPLEXICA`

---

### Task 4: Add Perplexica to docker-compose.override.private.yml

**Why**: Expose Perplexica port on localhost for private/development mode.

**Mirror**: `/opt/local-ai-packaged/docker-compose.override.private.yml:52-54`

**Do**:
Add perplexica service after searxng in docker-compose.override.private.yml:
```yaml
  perplexica:
    ports:
      - 127.0.0.1:8010:3000
```

**Don't**:
- Use 0.0.0.0 binding (security risk)
- Use port 3000 on host (conflicts with langfuse-web)

**Verify**: `docker compose -f /opt/local-ai-packaged/docker-compose.yml -f /opt/local-ai-packaged/docker-compose.override.private.yml config | grep -A3 "perplexica:"`

---

### Task 5: Add Perplexica reverse proxy entry to Caddyfile

**Why**: Enable external access to Perplexica through Caddy reverse proxy.

**Mirror**: `/opt/local-ai-packaged/Caddyfile:23-26`

**Do**:
Add Perplexica entry before the `import /etc/caddy/addons/*.conf` line:
```
# Perplexica - AI Search
{$PERPLEXICA_HOSTNAME} {
    reverse_proxy perplexica:3000
}
```

**Don't**:
- Add complex headers (not needed for Perplexica)
- Add authentication (Perplexica has its own)

**Verify**: `grep -A3 "PERPLEXICA" /opt/local-ai-packaged/Caddyfile`

---

### Task 6: Add PERPLEXICA_HOSTNAME to .env.example

**Why**: Document the environment variable for production deployments.

**Mirror**: `/opt/local-ai-packaged/.env.example:73-81`

**Do**:
Add after SEARXNG_HOSTNAME comment:
```bash
# PERPLEXICA_HOSTNAME=perplexica.yourdomain.com
```

**Don't**:
- Uncomment the variable (it's example-only)
- Add other Perplexica-specific variables (config is done via web UI)

**Verify**: `grep PERPLEXICA /opt/local-ai-packaged/.env.example`

---

### Task 7: Register Perplexica in service_dependencies.py

**Why**: Enable Management UI to display and control Perplexica service.

**Mirror**: `/opt/local-ai-packaged/management-ui/backend/app/core/service_dependencies.py:296-304`

**Do**:
Add Perplexica config after searxng in the SERVICE_CONFIGS dictionary:
```python
    "perplexica": ServiceConfig(
        name="perplexica",
        display_name="Perplexica",
        description="AI-powered search engine (Perplexity AI alternative)",
        group="core_ai",
        dependencies=["searxng"],
        default_enabled=True,
        category="optional"
    ),
```

**Don't**:
- Add Ollama as dependency (optional, user may use other providers)
- Mark as required (it's optional)
- Put in infrastructure group (it's an AI service)

**Verify**: `grep -A8 '"perplexica"' /opt/local-ai-packaged/management-ui/backend/app/core/service_dependencies.py`

---

### Task 8: Add Perplexica to frontend serviceUrls.ts

**Why**: Enable "Open" button in Management UI to launch Perplexica web interface.

**Mirror**: `/opt/local-ai-packaged/management-ui/frontend/src/utils/serviceUrls.ts:12-20`

**Do**:
Add perplexica entry after searxng in SERVICE_URL_MAP:
```typescript
  'perplexica': { port: 8010, name: 'Perplexica' },
```

**Don't**:
- Use port 3000 (that's internal, we expose 8010)
- Add path property (not needed)

**Verify**: `grep perplexica /opt/local-ai-packaged/management-ui/frontend/src/utils/serviceUrls.ts`

---

## Validation Strategy

### Automated Checks
- [ ] `docker compose -f docker-compose.yml config` - YAML syntax valid
- [ ] `docker compose -f docker-compose.yml -f docker-compose.override.private.yml config` - Merged config valid
- [ ] `grep -q perplexica docker-compose.yml` - Service definition exists
- [ ] `grep -q PERPLEXICA Caddyfile` - Caddy entry exists

### Manual Validation

#### Service Definition Test
```bash
cd /opt/local-ai-packaged
docker compose -f docker-compose.yml config --services | grep perplexica
# Expected output: perplexica
```

#### Start Perplexica Service
```bash
cd /opt/local-ai-packaged
docker compose -p localai -f docker-compose.yml -f docker-compose.override.private.yml up -d perplexica
# Expected: perplexica container starts
```

#### Verify Container Running
```bash
docker ps --filter name=perplexica --format "{{.Names}} {{.Status}}"
# Expected: perplexica Up X seconds
```

#### Test Web UI Access
```bash
curl -I http://localhost:8010
# Expected: HTTP/1.1 200 OK (or 302 redirect to setup page)
```

#### Test SearXNG Connectivity (from inside container)
```bash
docker exec perplexica wget -q -O- http://searxng:8080/search?q=test&format=json | head -c 200
# Expected: JSON search results
```

#### Management UI Test
1. Open http://localhost:9009 (Management UI)
2. Navigate to Services page
3. Verify Perplexica appears in "AI Services" group
4. Verify status badge shows correct state
5. Click "Open" button - should open http://localhost:8010

### Edge Cases to Test
- [ ] Start Perplexica without SearXNG running - should show connection error in UI
- [ ] Start Perplexica without Ollama - should work (can use other providers)
- [ ] Access Perplexica via Caddy port (:8010) - should work
- [ ] Stop/restart via Management UI - should work
- [ ] View logs via Management UI - should show Perplexica logs

### Regression Check
- [ ] Existing services still start: `docker compose -p localai -f docker-compose.yml --profile cpu -f docker-compose.override.private.yml up -d`
- [ ] SearXNG still works: `curl -s "http://localhost:8081/search?q=test&format=json" | jq .`
- [ ] Management UI still loads: `curl -I http://localhost:9009`
- [ ] Caddy still proxies other services: `curl -I http://localhost:8001` (n8n)

## Risks

1. **Port conflict**: Port 8010 chosen to avoid conflicts, but verify no other service uses it
2. **SearXNG dependency**: If SearXNG is down, Perplexica search won't work (by design)
3. **First-run setup**: User must complete setup wizard on first access - document this
4. **Image size**: `itzcrazykns1337/perplexica:slim-latest` is large (~1GB) - first pull takes time
5. **Ollama network access**: User must configure Ollama URL as `http://ollama:11434` in Perplexica setup, not localhost

## Post-Implementation Notes

After implementation, document in CLAUDE.md or README:
- Perplexica first-run setup requires configuring LLM provider via web UI
- For local Ollama: use `http://ollama:11434` as Ollama URL in Perplexica settings
- SearXNG is pre-configured and connected automatically
