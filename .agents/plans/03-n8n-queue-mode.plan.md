# Plan: n8n Queue Mode with Workers (GitHub Issue #159)

## Summary

Implement n8n queue mode support to enable horizontal scaling of workflow executions. The main n8n instance will handle UI, webhooks, and triggers while worker instances process the actual workflow executions. Redis/Valkey (already in the stack) will serve as the message broker. This requires adding a scalable n8n-worker service definition, queue-mode environment variables, shared volumes, health monitoring in the management UI, and documentation.

## External Research

### Documentation
- [n8n Queue Mode Configuration](https://docs.n8n.io/hosting/scaling/queue-mode/) - Official n8n queue mode setup guide
- [Queue Mode Environment Variables](https://docs.n8n.io/hosting/configuration/environment-variables/queue-mode/) - Complete list of queue-related env vars
- [GitHub: n8n-queue-mode](https://github.com/thenguyenvn90/n8n-queue-mode) - Reference Docker Compose implementation

### Key Environment Variables (from n8n docs)

| Variable | Type | Default | Purpose |
|----------|------|---------|---------|
| `EXECUTIONS_MODE` | String | `regular` | Set to `queue` for queue mode |
| `QUEUE_BULL_REDIS_HOST` | String | `localhost` | Redis server hostname |
| `QUEUE_BULL_REDIS_PORT` | Number | `6379` | Redis port |
| `QUEUE_BULL_REDIS_DB` | Number | `0` | Redis database number |
| `QUEUE_BULL_REDIS_PASSWORD` | String | - | Redis password (if set) |
| `QUEUE_HEALTH_CHECK_ACTIVE` | Boolean | `false` | Enable worker health endpoints |
| `QUEUE_HEALTH_CHECK_PORT` | Number | `5678` | Port for health checks |
| `N8N_CONCURRENCY_PRODUCTION_LIMIT` | Number | `10` | Max concurrent executions per worker |
| `OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS` | Boolean | `false` | Run manual executions on workers |

### Worker Health Endpoints
- `/healthz` - Returns whether the worker is up
- `/healthz/readiness` - Returns whether worker's DB and Redis connections are ready

### Gotchas & Best Practices
- **Same encryption key**: All instances (main + workers) MUST use the same `N8N_ENCRYPTION_KEY`
- **Same database**: All instances connect to the same PostgreSQL database
- **Shared files**: Use shared volume for `/files` directory between main and workers (NOT binary data - use S3/MinIO for that)
- **Health checks required**: Enable `QUEUE_HEALTH_CHECK_ACTIVE=true` for worker monitoring
- **Redis not exposed publicly**: Keep Redis internal-only, no public ports
- **Graceful shutdown**: Use `N8N_GRACEFUL_SHUTDOWN_TIMEOUT` for clean worker shutdown
- **Scaling**: Use `docker compose up -d --scale n8n-worker=N` to scale workers

## Patterns to Mirror

### Pattern 1: Service Definition with YAML Anchors (x-n8n)
FROM: `/opt/local-ai-packaged/docker-compose.yml:18-31`

```yaml
x-n8n: &service-n8n
  image: n8nio/n8n:latest
  environment:
    - DB_TYPE=postgresdb
    - DB_POSTGRESDB_HOST=db
    - DB_POSTGRESDB_USER=postgres
    - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
    - DB_POSTGRESDB_DATABASE=postgres
    - N8N_DIAGNOSTICS_ENABLED=false
    - N8N_PERSONALIZATION_ENABLED=false
    - N8N_ENCRYPTION_KEY
    - N8N_USER_MANAGEMENT_JWT_SECRET
    - WEBHOOK_URL=${N8N_HOSTNAME:+https://}${N8N_HOSTNAME:-http://localhost:5678}
```

### Pattern 2: Worker Service Definition (langfuse-worker)
FROM: `/opt/local-ai-packaged/docker-compose.yml:157-213`

```yaml
langfuse-worker:
  image: langfuse/langfuse-worker:3
  restart: always
  depends_on: &langfuse-depends-on
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  expose:
   - 3030/tcp
  environment: &langfuse-worker-env
    # ... environment variables
```

### Pattern 3: Service Dependencies Configuration
FROM: `/opt/local-ai-packaged/management-ui/backend/app/core/service_dependencies.py:199-208`

```python
"n8n": ServiceConfig(
    name="n8n",
    display_name="n8n",
    description="Workflow automation platform",
    group="workflow",
    dependencies=["db"],
    default_enabled=True,
    category="optional"
),
```

### Pattern 4: Environment Variable Schema
FROM: `/opt/local-ai-packaged/management-ui/backend/app/core/env_manager.py:8-20`

```python
ENV_SCHEMA = {
    "N8N_ENCRYPTION_KEY": {
        "category": "n8n",
        "is_secret": True,
        "is_required": True,
        "description": "Encryption key for n8n credentials (64 hex chars)",
        "validation_regex": r"^[a-f0-9]{64}$",
        "generate": "hex_32"
    },
}
```

### Pattern 5: Private Override Ports
FROM: `/opt/local-ai-packaged/docker-compose.override.private.yml:10-12`

```yaml
n8n:
  ports:
    - 127.0.0.1:5678:5678
```

### Pattern 6: Redis Healthcheck (existing)
FROM: `/opt/local-ai-packaged/docker-compose.yml:315-319`

```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 3s
  timeout: 10s
  retries: 10
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `docker-compose.yml` | UPDATE | Add n8n-worker service, extend x-n8n anchor with queue config |
| `docker-compose.override.private.yml` | UPDATE | Add n8n-worker health check port exposure |
| `.env.example` | UPDATE | Add queue mode environment variables with documentation |
| `management-ui/backend/app/core/service_dependencies.py` | UPDATE | Add n8n-worker service config |
| `management-ui/backend/app/core/dependency_graph.py` | UPDATE | Add n8n-worker to workflow group |
| `management-ui/backend/app/core/env_manager.py` | UPDATE | Add queue mode env var schema |
| `CLAUDE.md` | UPDATE | Add documentation for queue mode setup |

## NOT Building

- Multi-main setup (requires n8n license, out of scope)
- Webhook processors (separate scaling layer, can add later)
- External Redis cluster support (overkill for self-hosted)
- Auto-scaling based on queue length (can add later)
- S3/MinIO integration for binary data (separate concern)
- Custom n8n-worker Docker image (use official image)

## Tasks

### Task 1: Extend x-n8n YAML anchor with queue mode base config

**Why**: The x-n8n anchor provides shared configuration for all n8n instances. We need to add queue mode variables that apply to both main and worker instances.

**Mirror**: `docker-compose.yml:18-31` (existing x-n8n anchor)

**Do**:
1. Add queue mode environment variables to x-n8n anchor:
```yaml
x-n8n: &service-n8n
  image: n8nio/n8n:latest
  environment:
    # ... existing env vars ...
    # Queue Mode (when enabled)
    - EXECUTIONS_MODE=${N8N_EXECUTIONS_MODE:-regular}
    - QUEUE_BULL_REDIS_HOST=${N8N_QUEUE_REDIS_HOST:-redis}
    - QUEUE_BULL_REDIS_PORT=${N8N_QUEUE_REDIS_PORT:-6379}
    - QUEUE_BULL_REDIS_DB=${N8N_QUEUE_REDIS_DB:-0}
    - QUEUE_HEALTH_CHECK_ACTIVE=${N8N_QUEUE_HEALTH_CHECK:-false}
```

**Don't**:
- Don't add Redis password (current stack doesn't use one)
- Don't add TLS settings (internal network only)

**Verify**: `docker compose config | grep -A 20 "n8n:"`

---

### Task 2: Add n8n-worker service definition

**Why**: Workers are separate n8n instances that process executions from the Redis queue. They need similar config to main but run in worker mode.

**Mirror**: `docker-compose.yml:157-213` (langfuse-worker pattern)

**Do**:
Add after the n8n service definition (around line 94):

```yaml
  n8n-worker:
    <<: *service-n8n
    container_name: n8n-worker
    restart: unless-stopped
    command: worker
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    expose:
      - 5681/tcp
    environment:
      # Inherit from x-n8n anchor, add worker-specific
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=db
      - DB_POSTGRESDB_USER=postgres
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - DB_POSTGRESDB_DATABASE=postgres
      - N8N_DIAGNOSTICS_ENABLED=false
      - N8N_PERSONALIZATION_ENABLED=false
      - N8N_ENCRYPTION_KEY
      - N8N_USER_MANAGEMENT_JWT_SECRET
      - EXECUTIONS_MODE=queue
      - QUEUE_BULL_REDIS_HOST=${N8N_QUEUE_REDIS_HOST:-redis}
      - QUEUE_BULL_REDIS_PORT=${N8N_QUEUE_REDIS_PORT:-6379}
      - QUEUE_BULL_REDIS_DB=${N8N_QUEUE_REDIS_DB:-0}
      - QUEUE_HEALTH_CHECK_ACTIVE=true
      - QUEUE_HEALTH_CHECK_PORT=5681
      - N8N_CONCURRENCY_PRODUCTION_LIMIT=${N8N_WORKER_CONCURRENCY:-10}
      - OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS=${N8N_OFFLOAD_MANUAL:-false}
    volumes:
      - n8n_storage:/home/node/.n8n
      - ./shared:/data/shared
    profiles:
      - queue
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:5681/healthz || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

**Don't**:
- Don't include `/backup` volume (workers don't need backup dir)
- Don't set container_name with number (docker compose scale won't work)
- Actually, DO use container_name for single worker - scaling requires `docker compose up --scale` which overrides it

**Verify**: `docker compose --profile queue config | grep -A 30 "n8n-worker"`

---

### Task 3: Update n8n main service for queue mode

**Why**: When queue mode is enabled, the main n8n instance needs to be configured to enqueue executions rather than process them directly.

**Mirror**: `docker-compose.yml:84-93` (existing n8n service)

**Do**:
Update the n8n service to include queue mode variables and Redis dependency:

```yaml
n8n:
  <<: *service-n8n
  container_name: n8n
  restart: unless-stopped
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
  expose:
    - 5678/tcp
  volumes:
    - n8n_storage:/home/node/.n8n
    - ./n8n/backup:/backup
    - ./shared:/data/shared
```

Note: The queue mode environment variables are already in the x-n8n anchor from Task 1.

**Don't**:
- Don't make Redis a hard dependency (queue mode is optional)

**Verify**: `docker compose config | grep -B5 -A15 "n8n:"`

---

### Task 4: Add n8n-worker to docker-compose.override.private.yml

**Why**: In private mode, we expose service ports to localhost for debugging. The worker health check port should be accessible.

**Mirror**: `docker-compose.override.private.yml:10-12` (n8n port pattern)

**Do**:
Add after the n8n ports section:

```yaml
  n8n-worker:
    ports:
      - 127.0.0.1:5681:5681
```

**Don't**:
- Don't expose to 0.0.0.0 (security risk)

**Verify**: `cat docker-compose.override.private.yml | grep -A2 n8n-worker`

---

### Task 5: Add queue mode environment variables to .env.example

**Why**: Users need documented environment variables to configure queue mode.

**Mirror**: `.env.example:10-13` (n8n secrets section pattern)

**Do**:
Add a new section after the n8n credentials section (around line 13):

```bash
############
# [optional]
# n8n Queue Mode - Enable horizontal scaling for workflow executions
# To enable: Set N8N_EXECUTIONS_MODE=queue and start with --profile queue
# Scale workers: docker compose -p localai --profile queue up -d --scale n8n-worker=3
############

# Set to 'queue' to enable queue mode (default: regular)
# N8N_EXECUTIONS_MODE=queue

# Redis connection for queue (defaults work with included Redis/Valkey)
# N8N_QUEUE_REDIS_HOST=redis
# N8N_QUEUE_REDIS_PORT=6379
# N8N_QUEUE_REDIS_DB=0

# Worker configuration
# N8N_WORKER_CONCURRENCY=10
# N8N_OFFLOAD_MANUAL=false
# N8N_QUEUE_HEALTH_CHECK=true
```

**Don't**:
- Don't uncomment values by default (queue mode should be opt-in)
- Don't include Redis password (not used in current stack)

**Verify**: `grep -A20 "Queue Mode" .env.example`

---

### Task 6: Add n8n-worker to service_dependencies.py

**Why**: The management UI needs to know about n8n-worker for proper dependency resolution and display.

**Mirror**: `service_dependencies.py:199-208` (n8n ServiceConfig pattern)

**Do**:
Add after the n8n config (around line 208):

```python
"n8n-worker": ServiceConfig(
    name="n8n-worker",
    display_name="n8n Worker",
    description="Queue worker for n8n workflow executions",
    group="workflow",
    dependencies=["db", "redis", "n8n"],
    profiles=["queue"],
    default_enabled=False,
    category="optional"
),
```

**Don't**:
- Don't set `required=True` (it's optional)
- Don't add to default_enabled (queue mode is opt-in)

**Verify**: `grep -A10 "n8n-worker" management-ui/backend/app/core/service_dependencies.py`

---

### Task 7: Update dependency_graph.py SERVICE_GROUPS

**Why**: The n8n-worker needs to be in the workflow group for proper UI grouping.

**Mirror**: `dependency_graph.py:23-27` (workflow group pattern)

**Do**:
Update the workflow group to include n8n-worker:

```python
"workflow": {
    "name": "Workflow",
    "services": ["n8n", "n8n-worker"],
    "description": "Workflow automation"
},
```

**Don't**:
- Don't create a separate group for workers

**Verify**: `grep -A5 '"workflow"' management-ui/backend/app/core/dependency_graph.py`

---

### Task 8: Add queue mode env vars to env_manager.py ENV_SCHEMA

**Why**: The management UI validates environment variables and needs schema for queue mode vars.

**Mirror**: `env_manager.py:8-20` (N8N_ENCRYPTION_KEY schema pattern)

**Do**:
Add after the existing n8n variables (around line 23):

```python
"N8N_EXECUTIONS_MODE": {
    "category": "n8n",
    "is_secret": False,
    "is_required": False,
    "description": "Execution mode: 'regular' or 'queue'",
    "validation_regex": r"^(regular|queue)$"
},
"N8N_WORKER_CONCURRENCY": {
    "category": "n8n",
    "is_secret": False,
    "is_required": False,
    "description": "Max concurrent executions per worker (default: 10)"
},
"N8N_QUEUE_REDIS_HOST": {
    "category": "n8n",
    "is_secret": False,
    "is_required": False,
    "description": "Redis host for queue mode (default: redis)"
},
"N8N_QUEUE_REDIS_PORT": {
    "category": "n8n",
    "is_secret": False,
    "is_required": False,
    "description": "Redis port for queue mode (default: 6379)"
},
```

**Don't**:
- Don't mark as required (queue mode is optional)
- Don't add Redis password to schema (not used)

**Verify**: `grep -A5 "N8N_EXECUTIONS_MODE" management-ui/backend/app/core/env_manager.py`

---

### Task 9: Update CLAUDE.md with queue mode documentation

**Why**: Developers and users need documentation on how to enable and configure queue mode.

**Mirror**: `CLAUDE.md` existing documentation style

**Do**:
Add a new section after "Starting Services" (around line 20):

```markdown
## n8n Queue Mode (Horizontal Scaling)

Queue mode allows scaling n8n workflow executions across multiple workers.

### Enabling Queue Mode

1. Edit `.env` and set:
   ```bash
   N8N_EXECUTIONS_MODE=queue
   ```

2. Start with the queue profile:
   ```bash
   python start_services.py --profile gpu-nvidia --environment private
   docker compose -p localai --profile queue up -d
   ```

3. Scale workers as needed:
   ```bash
   docker compose -p localai --profile queue up -d --scale n8n-worker=3
   ```

### Queue Mode Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `N8N_EXECUTIONS_MODE` | `regular` | Set to `queue` to enable |
| `N8N_WORKER_CONCURRENCY` | `10` | Max concurrent executions per worker |
| `N8N_QUEUE_REDIS_HOST` | `redis` | Redis hostname |
| `N8N_QUEUE_REDIS_PORT` | `6379` | Redis port |
| `N8N_OFFLOAD_MANUAL` | `false` | Run manual executions on workers |

### Monitoring Workers

- Worker health: `http://localhost:5681/healthz`
- Worker readiness: `http://localhost:5681/healthz/readiness`
- Management UI shows worker status in the Workflow group
```

**Don't**:
- Don't document multi-main setup (requires license)
- Don't add emoji or excessive formatting

**Verify**: `grep -A20 "Queue Mode" CLAUDE.md`

---

## Validation Strategy

### Automated Checks

- [ ] `docker compose config` - Valid Docker Compose syntax
- [ ] `docker compose --profile queue config` - Queue profile resolves correctly
- [ ] `cd management-ui/backend && python -c "from app.core.service_dependencies import SERVICE_CONFIGS; print('OK')"` - Python imports work

### Manual Validation

#### Test 1: Queue Mode Disabled (Default Behavior)

```bash
# 1. Start services without queue profile
python start_services.py --profile cpu --environment private

# 2. Verify n8n works normally
curl http://localhost:5678/healthz

# 3. Verify n8n-worker is NOT running
docker ps | grep n8n-worker  # Should return nothing

# 4. Verify EXECUTIONS_MODE is regular
docker exec n8n printenv | grep EXECUTIONS_MODE  # Should be 'regular' or empty
```

#### Test 2: Queue Mode Enabled

```bash
# 1. Set queue mode in .env
echo "N8N_EXECUTIONS_MODE=queue" >> .env

# 2. Start with queue profile
python start_services.py --profile cpu --environment private
docker compose -p localai --profile queue up -d

# 3. Verify worker is running
docker ps | grep n8n-worker  # Should show running container

# 4. Check worker health
curl http://localhost:5681/healthz  # Should return OK

# 5. Check worker readiness (DB and Redis connected)
curl http://localhost:5681/healthz/readiness  # Should return OK

# 6. Verify both n8n and worker have queue mode
docker exec n8n printenv | grep EXECUTIONS_MODE  # Should be 'queue'
docker exec n8n-worker printenv | grep EXECUTIONS_MODE  # Should be 'queue'
```

#### Test 3: Worker Scaling

```bash
# Scale to 3 workers
docker compose -p localai --profile queue up -d --scale n8n-worker=3

# Verify 3 workers running
docker ps | grep n8n-worker | wc -l  # Should be 3

# All workers healthy
for i in 1 2 3; do
  docker exec localai-n8n-worker-$i wget -q --spider http://localhost:5681/healthz && echo "Worker $i healthy"
done
```

#### Test 4: Workflow Execution in Queue Mode

```bash
# 1. Access n8n UI at http://localhost:5678
# 2. Create a simple test workflow (e.g., Start -> Set -> End)
# 3. Execute the workflow manually
# 4. Check worker logs for "Worker started execution" and "finished execution"
docker logs n8n-worker 2>&1 | grep -i execution
```

### Edge Cases

- [ ] **Redis unavailable**: n8n-worker should fail health check and restart
  - Stop redis: `docker stop redis`
  - Check worker: `curl http://localhost:5681/healthz/readiness` should fail
  - Restart redis: `docker start redis`
  - Worker should recover automatically

- [ ] **Database unavailable**: Workers should fail readiness check
  - Similar test pattern as Redis

- [ ] **Encryption key mismatch**: Workflow execution should fail with decryption error
  - Intentionally set different key in worker
  - Execution should fail with clear error message

- [ ] **Shared volume access**: Both n8n and workers can access /data/shared
  - Create file in n8n: `docker exec n8n touch /data/shared/test.txt`
  - Verify in worker: `docker exec n8n-worker ls /data/shared/test.txt`

### Regression Check

- [ ] Existing n8n workflows still execute in regular mode (without queue profile)
- [ ] Management UI still shows n8n service correctly
- [ ] Service dependencies still resolve correctly
- [ ] All other services unaffected by changes

## Risks

1. **Redis connection issues**: Workers need reliable Redis connection. Mitigated by health checks and depends_on with condition.

2. **Encryption key desync**: All instances must share `N8N_ENCRYPTION_KEY`. Mitigated by using same env var in all services.

3. **Database connection pool exhaustion**: Multiple workers = more DB connections. May need to increase `POOLER_DEFAULT_POOL_SIZE` in `.env`.

4. **Volume permissions**: n8n_storage shared between instances. n8n uses `node` user (uid 1000). Should work with default Docker volume permissions.

5. **Profile confusion**: Users may not understand `--profile queue` requirement. Mitigated by documentation and making queue mode opt-in via env var.
