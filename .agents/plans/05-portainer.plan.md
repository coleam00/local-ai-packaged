# Plan: Portainer CE Integration (GitHub Issues #161, #137)

## Summary

Add Portainer CE as an optional Docker management service to the local-ai-packaged stack. Portainer will be opt-in via a new `portainer` profile, following the existing profile pattern used for Ollama GPU variants. The implementation includes the docker-compose service definition, Caddy reverse proxy routing, localhost port exposure for private mode, environment variable for hostname configuration, and Management UI awareness through service dependencies configuration.

## External Research

### Documentation
- [Portainer CE Docker Compose](https://docs.portainer.io/start/install-ce/server/docker/linux) - Official installation guide
- [Portainer Docker Hub](https://hub.docker.com/r/portainer/portainer-ce) - Image and configuration reference

### Key Findings
- **Image**: `portainer/portainer-ce:lts` (long-term support recommended over `latest`)
- **Ports**:
  - 9443: HTTPS web UI (primary access port with self-signed SSL)
  - 8000: TCP tunnel for Edge agents (optional, not needed for local management)
- **Volume**: Requires `/data` volume for persistent settings
- **Docker socket**: Must mount `/var/run/docker.sock` for container management
- **Security**: Docker socket mount gives root-level Docker access; mitigated by limiting network access and keeping Portainer updated

### Gotchas & Best Practices
- Use `portainer/portainer-ce:lts` instead of `latest` for stability
- Port 9443 uses HTTPS with self-signed certificate (Caddy will proxy to this)
- Edge agents (port 8000) not needed for local single-host deployment
- Docker socket mount is required and cannot be avoided for local Docker management

## Patterns to Mirror

### Service Definition Pattern (docker-compose.yml:321-343)
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

### Profile-Based Service Pattern (docker-compose.yml:345-359)
```yaml
ollama-gpu:
    profiles: ["gpu-nvidia"]
    <<: *service-ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Caddy Reverse Proxy Pattern (Caddyfile:23-26)
```
# Langfuse
{$LANGFUSE_HOSTNAME} {
    reverse_proxy langfuse-web:3000
}
```

### Environment Variable Pattern (Caddyfile:44-46)
```
{$MANAGEMENT_HOSTNAME:-":9009"} {
    reverse_proxy management-ui:9000
}
```

### Caddy Environment Config Pattern (docker-compose.yml:138-146)
```yaml
environment:
  - N8N_HOSTNAME=${N8N_HOSTNAME:-":8001"}
  - WEBUI_HOSTNAME=${WEBUI_HOSTNAME:-":8002"}
  - LANGFUSE_HOSTNAME=${LANGFUSE_HOSTNAME:-":8007"}
```

### Private Mode Port Pattern (docker-compose.override.private.yml:29-31)
```yaml
langfuse-web:
    ports:
      - 127.0.0.1:3000:3000
```

### Service URL Config Pattern (management-ui/frontend/src/utils/serviceUrls.ts:12-21)
```typescript
const SERVICE_URL_MAP: Record<string, ServiceUrlConfig> = {
  'n8n': { port: 5678, name: 'n8n' },
  'langfuse-web': { port: 3000, name: 'Langfuse' },
  'minio': { port: 9011, name: 'MinIO Console' },
};
```

### Service Dependencies Config Pattern (management-ui/backend/app/core/service_dependencies.py:296-304)
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

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `docker-compose.yml` | UPDATE | Add Portainer service definition with profile |
| `docker-compose.override.private.yml` | UPDATE | Expose port 9443 for localhost access |
| `Caddyfile` | UPDATE | Add reverse proxy routing for Portainer |
| `.env.example` | UPDATE | Add PORTAINER_HOSTNAME environment variable |
| `management-ui/frontend/src/utils/serviceUrls.ts` | UPDATE | Add Portainer URL mapping for web UI link |
| `management-ui/backend/app/core/service_dependencies.py` | UPDATE | Add Portainer service configuration |

## NOT Building

- Edge agent support (port 8000) - not needed for single-host local deployment
- Custom SSL certificates - using Portainer's self-signed cert behind Caddy is sufficient
- Authentication integration with other services - Portainer has its own auth
- Portainer Agent - only needed for managing remote Docker hosts
- Volume for Portainer data in named volumes section - will use named volume inline

## Tasks

### Task 1: Add Portainer service to docker-compose.yml

**Why**: Define the Portainer CE service with profile-based opt-in to match existing patterns.

**Mirror**: `docker-compose.yml:321-343` (searxng service structure)

**Do**:
Add after the `ollama-pull-llama-gpu-amd` service (end of file):

```yaml
  portainer:
    profiles: ["portainer"]
    container_name: portainer
    image: portainer/portainer-ce:lts
    restart: unless-stopped
    expose:
      - 9443/tcp
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - portainer_data:/data
    logging:
      driver: "json-file"
      options:
        max-size: "1m"
        max-file: "1"
```

Also add `portainer_data:` to the volumes section (after `langfuse_minio_data:`).

**Don't**:
- Don't expose port 8000 (Edge agents not needed)
- Don't add cap_drop (needs access to Docker)
- Don't add healthcheck (Portainer handles this internally)

**Verify**: `docker compose -f docker-compose.yml config --profiles portainer | grep -A 20 portainer:`

---

### Task 2: Add Portainer port to private override

**Why**: Expose Portainer web UI on localhost for private mode access.

**Mirror**: `docker-compose.override.private.yml:29-31` (langfuse-web pattern)

**Do**:
Add after `ollama-gpu-amd` section:

```yaml
  portainer:
    ports:
      - 127.0.0.1:9443:9443
```

**Don't**:
- Don't expose port 8000 (not needed)

**Verify**: `docker compose -f docker-compose.yml -f docker-compose.override.private.yml --profile portainer config | grep -A 5 "portainer:"`

---

### Task 3: Add PORTAINER_HOSTNAME to Caddy environment

**Why**: Enable Caddy to use the Portainer hostname environment variable.

**Mirror**: `docker-compose.yml:144` (LANGFUSE_HOSTNAME pattern)

**Do**:
In the `caddy` service `environment` section, add after `LANGFUSE_HOSTNAME`:

```yaml
      - PORTAINER_HOSTNAME=${PORTAINER_HOSTNAME:-":9443"}
```

**Don't**:
- Don't change the port pattern - Caddy needs this for localhost mode

**Verify**: `grep PORTAINER docker-compose.yml`

---

### Task 4: Add Portainer routing to Caddyfile

**Why**: Route requests through Caddy reverse proxy.

**Mirror**: `Caddyfile:23-26` (Langfuse pattern)

**Do**:
Add before the `import /etc/caddy/addons/*.conf` line:

```
# Portainer
{$PORTAINER_HOSTNAME} {
    reverse_proxy portainer:9443 {
        transport http {
            tls
            tls_insecure_skip_verify
        }
    }
}
```

Note: Portainer uses HTTPS internally (self-signed), so Caddy needs `tls_insecure_skip_verify` to proxy to it.

**Don't**:
- Don't try to proxy to port 9000 (that's the deprecated HTTP port)

**Verify**: `grep -A 6 "Portainer" Caddyfile`

---

### Task 5: Add PORTAINER_HOSTNAME to .env.example

**Why**: Document the environment variable for users.

**Mirror**: `.env.example:73-80` (hostname patterns)

**Do**:
Add in the Caddy Config section after `NEO4J_HOSTNAME`:

```
# PORTAINER_HOSTNAME=portainer.yourdomain.com
```

**Don't**:
- Don't set a default value (uses port-based localhost by default)

**Verify**: `grep PORTAINER .env.example`

---

### Task 6: Add Portainer to service URL mapping

**Why**: Enable web UI to show "Open" link for Portainer.

**Mirror**: `management-ui/frontend/src/utils/serviceUrls.ts:21` (minio pattern)

**Do**:
Add to `SERVICE_URL_MAP` object:

```typescript
  'portainer': { port: 9443, name: 'Portainer' },
```

Note: Uses HTTPS, but browser will handle the self-signed certificate warning.

**Don't**:
- Don't add path - Portainer root is the dashboard

**Verify**: `grep -i portainer management-ui/frontend/src/utils/serviceUrls.ts`

---

### Task 7: Add Portainer to service dependencies

**Why**: Management UI needs to know about Portainer for display and dependency tracking.

**Mirror**: `management-ui/backend/app/core/service_dependencies.py:296-304` (searxng pattern)

**Do**:
Add to `SERVICE_CONFIGS` dict in the Infrastructure section:

```python
    "portainer": ServiceConfig(
        name="portainer",
        display_name="Portainer",
        description="Docker container management UI",
        group="infrastructure",
        dependencies=[],
        profiles=["portainer"],
        default_enabled=False,
        category="optional"
    ),
```

**Don't**:
- Don't set `required=True` - this is opt-in
- Don't set `default_enabled=True` - users must opt-in via profile

**Verify**: `grep -A 10 '"portainer"' management-ui/backend/app/core/service_dependencies.py`

---

## Validation Strategy

### Automated Checks
- [ ] `docker compose -f docker-compose.yml config` - Compose file valid
- [ ] `docker compose -f docker-compose.yml -f docker-compose.override.private.yml config` - Override valid
- [ ] `docker compose -f docker-compose.yml --profile portainer config` - Profile recognized

### Manual Validation

#### 1. Service Starts Correctly
```bash
# Start with Portainer profile
python start_services.py --profile cpu --environment private
docker compose -p localai --profile portainer -f docker-compose.yml -f docker-compose.override.private.yml up -d portainer

# Verify container is running
docker ps | grep portainer

# Check logs for startup
docker logs portainer
```

#### 2. Web UI Accessible
```bash
# Check port binding
curl -k https://localhost:9443 -I

# Open in browser
# https://localhost:9443
# Should show Portainer setup wizard (first run) or login page
```

#### 3. Caddy Proxy Works
```bash
# Verify Caddy can reach Portainer
docker exec caddy wget -q --no-check-certificate -O - https://portainer:9443/api/status | head
```

#### 4. Management UI Shows Portainer
- Navigate to Management UI (http://localhost:9009)
- Check Services page - Portainer should appear in Infrastructure section
- Verify it shows as "not running" initially (profile not active)
- Check that clicking "Open" links to https://localhost:9443

### Edge Cases to Test
- [ ] Service remains off when profile not specified: `docker compose -f docker-compose.yml up -d` should NOT start Portainer
- [ ] Profile activation works: `docker compose -f docker-compose.yml --profile portainer up -d portainer` starts only Portainer
- [ ] Docker socket access works: Portainer can list containers in the localai project
- [ ] Self-signed certificate: Caddy proxies correctly with `tls_insecure_skip_verify`

### Regression Check
- [ ] Existing services still start: `python start_services.py --profile cpu`
- [ ] Management UI loads: http://localhost:9009
- [ ] Other service web UIs work: Open WebUI, n8n, Langfuse

## Risks

1. **Docker socket security**: Mounting `/var/run/docker.sock` gives Portainer full Docker access. Mitigated by:
   - Opt-in only via profile
   - Read-only mount (`:ro`)
   - Not enabled by default

2. **Self-signed certificate**: Portainer uses HTTPS with self-signed cert. Users will see browser warning on direct access. Caddy handles this for proxied access.

3. **Profile activation complexity**: Users need to add `--profile portainer` to their docker compose commands. This may require documenting clearly.

## Sources

- [Install Portainer CE with Docker on Linux](https://docs.portainer.io/start/install-ce/server/docker/linux) - Official documentation
- [Portainer Docker Hub](https://hub.docker.com/r/portainer/portainer-ce) - Image reference
- [Portainer Security Discussion](https://github.com/portainer/portainer/issues/5708) - Docker socket security considerations
