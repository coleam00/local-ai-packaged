# Plan: ComfyUI Integration (GitHub Issue #152)

## Summary

Add ComfyUI as a new service to the local-ai-packaged stack for node-based image generation. ComfyUI will follow the established GPU profile pattern (cpu, gpu-nvidia, gpu-amd), integrate with the Caddy reverse proxy, and appear in the Management UI. The implementation mirrors the existing Ollama service pattern for GPU variants and follows the established patterns for service cards, logs, and dependency configuration.

## External Research

### Documentation
- [ComfyUI GitHub](https://github.com/comfyanonymous/ComfyUI) - Official repository
- [joepitt91/comfyui-docker](https://github.com/joepitt91/comfyui-docker) - Reference Docker images supporting CPU, NVIDIA, AMD, Intel
- [ai-dock/comfyui](https://github.com/ai-dock/comfyui) - Production-ready Docker images

### Key Findings

1. **Default Port**: ComfyUI runs on port **8188** by default
2. **GPU Support**:
   - NVIDIA: Standard CUDA container with nvidia runtime
   - AMD: ROCm-based image (~23GB, large dependencies)
   - CPU: Works but significantly slower
3. **Docker Images**:
   - `joepitt91/comfyui:nvidia` - NVIDIA GPU
   - `joepitt91/comfyui:cpu` - CPU only
   - AMD requires local build due to size constraints
4. **WebSocket Requirement**: ComfyUI uses WebSocket connections for `/ws` and `/queue/join` endpoints - Caddy handles this natively
5. **Volume Structure**:
   - `/app/models` - Model storage (checkpoints, LoRAs, VAEs)
   - `/app/input` - Input images
   - `/app/output` - Generated images
   - `/app/custom_nodes` - Custom node extensions

### Gotchas & Best Practices
- ComfyUI requires 6GB+ VRAM minimum for practical use
- WebSocket connections are critical - reverse proxy must support upgrades
- First startup can take several minutes to initialize
- Model storage should be persistent and potentially shared with Ollama for efficiency

## Patterns to Mirror

### GPU Profile Pattern (from docker-compose.yml:345-386)
```yaml
# FROM: docker-compose.yml:345-386
# This is how Ollama handles GPU profiles:

ollama-cpu:
  profiles: ["cpu"]
  <<: *service-ollama

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

ollama-gpu-amd:
  profiles: ["gpu-amd"]
  <<: *service-ollama
  image: ollama/ollama:rocm
  devices:
    - "/dev/kfd"
    - "/dev/dri"
```

### YAML Anchor Pattern (from docker-compose.yml:32-44)
```yaml
# FROM: docker-compose.yml:32-44
# This is how base service config is defined:

x-ollama: &service-ollama
  image: ollama/ollama:latest
  container_name: ollama
  restart: unless-stopped
  expose:
    - 11434/tcp
  environment:
    - OLLAMA_CONTEXT_LENGTH=8192
  volumes:
    - ollama_storage:/root/.ollama
```

### Caddy Reverse Proxy Pattern (from Caddyfile:13-16)
```
# FROM: Caddyfile:13-16
# This is how services are exposed via Caddy:

# Open WebUI
{$WEBUI_HOSTNAME} {
    reverse_proxy open-webui:8080
}
```

### Override Files Pattern (from docker-compose.override.private.yml:56-66)
```yaml
# FROM: docker-compose.override.private.yml:56-66
# This is how GPU variants expose ports:

ollama-cpu:
  ports:
    - 127.0.0.1:11434:11434

ollama-gpu:
  ports:
    - 127.0.0.1:11434:11434

ollama-gpu-amd:
  ports:
    - 127.0.0.1:11434:11434
```

### Service URL Mapping (from management-ui/frontend/src/utils/serviceUrls.ts:12-29)
```typescript
// FROM: management-ui/frontend/src/utils/serviceUrls.ts:12-29
// This is how services map to ports in the UI:

const SERVICE_URL_MAP: Record<string, ServiceUrlConfig> = {
  // Direct port access (from docker-compose.override.private.yml)
  'n8n': { port: 5678, name: 'n8n' },
  'open-webui': { port: 8080, name: 'Open WebUI' },
  'flowise': { port: 3001, name: 'Flowise' },
  // ...
};
```

### Service Config Pattern (from management-ui/backend/app/core/service_dependencies.py:149-197)
```python
# FROM: management-ui/backend/app/core/service_dependencies.py:149-197
# This is how services are configured for the UI:

"ollama-cpu": ServiceConfig(
    name="ollama-cpu",
    display_name="Ollama (CPU)",
    description="Local LLM inference on CPU",
    group="core_ai",
    dependencies=[],
    profiles=["cpu"],
    default_enabled=True,
    category="optional"
),
```

### Dependency Graph Groups (from management-ui/backend/app/core/dependency_graph.py:17-22)
```python
# FROM: management-ui/backend/app/core/dependency_graph.py:17-22
# This is how services are grouped:

"core_ai": {
    "name": "AI Services",
    "services": ["ollama-cpu", "ollama-gpu", "ollama-gpu-amd",
                 "open-webui", "flowise"],
    "description": "Core AI inference and interfaces"
},
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `docker-compose.yml` | UPDATE | Add ComfyUI service definitions with GPU profiles |
| `docker-compose.override.private.yml` | UPDATE | Expose ComfyUI port 8188 to localhost |
| `docker-compose.override.public.yml` | UPDATE | Close ComfyUI port for public deployment (if needed) |
| `Caddyfile` | UPDATE | Add reverse proxy entry for ComfyUI |
| `.env.example` | UPDATE | Add COMFYUI_HOSTNAME variable |
| `management-ui/backend/app/core/service_dependencies.py` | UPDATE | Add ComfyUI service configs |
| `management-ui/backend/app/core/dependency_graph.py` | UPDATE | Add ComfyUI to core_ai group |
| `management-ui/frontend/src/utils/serviceUrls.ts` | UPDATE | Add ComfyUI URL mapping |

## NOT Building

- Model sharing with Ollama (different model formats - Stable Diffusion vs LLMs)
- Custom node auto-installation mechanism
- ComfyUI Manager integration (can be added manually by users)
- API key authentication (ComfyUI doesn't support it natively)
- Multiple ComfyUI instances
- Model download automation

## Tasks

### Task 1: Add Docker volumes for ComfyUI storage

**Why**: ComfyUI needs persistent storage for models, outputs, and custom nodes. Following the pattern of other services, we define named volumes.

**Mirror**: `docker-compose.yml:4-17` (volume definitions)

**Do**:
Add to the `volumes:` section in docker-compose.yml:
```yaml
volumes:
  # ... existing volumes ...
  comfyui_models:
  comfyui_output:
  comfyui_input:
  comfyui_custom_nodes:
```

**Don't**:
- Don't use bind mounts (inconsistent with project pattern)
- Don't share volumes with Ollama (incompatible model formats)

**Verify**: `grep -A 20 "^volumes:" docker-compose.yml | grep comfyui`

---

### Task 2: Add ComfyUI YAML anchor and base service definition

**Why**: Following the Ollama pattern, we define a reusable base configuration that all GPU variants inherit from.

**Mirror**: `docker-compose.yml:32-44` (x-ollama anchor)

**Do**:
Add after the x-init-ollama anchor (around line 55):
```yaml
x-comfyui: &service-comfyui
  image: joepitt91/comfyui:cpu
  container_name: comfyui
  restart: unless-stopped
  expose:
    - 8188/tcp
  environment:
    - COMFYUI_PORT=8188
    - MAX_UPLOAD_MB=${COMFYUI_MAX_UPLOAD_MB:-100}
  volumes:
    - comfyui_models:/app/models
    - comfyui_output:/app/output
    - comfyui_input:/app/input
    - comfyui_custom_nodes:/app/custom_nodes
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

**Don't**:
- Don't add healthcheck (ComfyUI doesn't have a standard health endpoint)
- Don't set GPU reservations in base config

**Verify**: `grep -A 15 "x-comfyui:" docker-compose.yml`

---

### Task 3: Add ComfyUI profile-based services

**Why**: Like Ollama, ComfyUI needs separate service definitions for CPU, NVIDIA, and AMD GPU profiles.

**Mirror**: `docker-compose.yml:345-386` (Ollama GPU profiles)

**Do**:
Add to the `services:` section, after the Ollama services:
```yaml
comfyui-cpu:
  profiles: ["cpu"]
  <<: *service-comfyui

comfyui-gpu:
  profiles: ["gpu-nvidia"]
  <<: *service-comfyui
  image: joepitt91/comfyui:nvidia
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

comfyui-gpu-amd:
  profiles: ["gpu-amd"]
  <<: *service-comfyui
  image: rocm/pytorch:rocm6.2_ubuntu22.04_py3.10_pytorch_release_2.3.0
  devices:
    - "/dev/kfd"
    - "/dev/dri"
  command: >
    bash -c "pip install comfyui && python -m comfyui --listen 0.0.0.0 --port 8188"
```

Note: AMD image uses ROCm PyTorch base and installs ComfyUI at runtime since no pre-built AMD image is readily available.

**Don't**:
- Don't add to the "none" profile (ComfyUI isn't available as external service like Ollama)

**Verify**: `docker compose config --profiles cpu | grep comfyui`

---

### Task 4: Update docker-compose.override.private.yml for port exposure

**Why**: In private mode, ComfyUI port needs to be exposed to localhost for direct access.

**Mirror**: `docker-compose.override.private.yml:56-66` (Ollama port exposure)

**Do**:
Add after the Ollama port definitions:
```yaml
comfyui-cpu:
  ports:
    - 127.0.0.1:8188:8188

comfyui-gpu:
  ports:
    - 127.0.0.1:8188:8188

comfyui-gpu-amd:
  ports:
    - 127.0.0.1:8188:8188
```

**Don't**:
- Don't expose to 0.0.0.0 (security risk)

**Verify**: `grep -A 2 "comfyui" docker-compose.override.private.yml`

---

### Task 5: Add Caddy reverse proxy configuration

**Why**: ComfyUI needs to be accessible through Caddy for consistent access patterns and optional TLS termination.

**Mirror**: `Caddyfile:13-16` (Open WebUI reverse proxy)

**Do**:
Add after the Neo4j block (around line 42):
```
# ComfyUI
{$COMFYUI_HOSTNAME:-":8009"} {
    reverse_proxy comfyui:8188
}
```

**Don't**:
- Don't add special WebSocket handling (Caddy handles it automatically)
- Don't add authentication (ComfyUI handles it internally if needed)

**Verify**: `grep -A 3 "ComfyUI" Caddyfile`

---

### Task 6: Update .env.example with ComfyUI variables

**Why**: Users need documentation for configuring ComfyUI hostname and optional settings.

**Mirror**: `.env.example:73-81` (hostname configuration)

**Do**:
Add after the NEO4J_HOSTNAME line (around line 80):
```
# COMFYUI_HOSTNAME=comfyui.yourdomain.com

############
# Optional ComfyUI Config
############
# COMFYUI_MAX_UPLOAD_MB=100
```

**Don't**:
- Don't add secrets (ComfyUI doesn't need them in basic setup)

**Verify**: `grep COMFYUI .env.example`

---

### Task 7: Update Caddy environment in docker-compose.yml

**Why**: Caddy needs the COMFYUI_HOSTNAME environment variable to configure the reverse proxy.

**Mirror**: `docker-compose.yml:137-146` (Caddy environment)

**Do**:
Add to the caddy service environment section:
```yaml
environment:
  # ... existing vars ...
  - COMFYUI_HOSTNAME=${COMFYUI_HOSTNAME:-":8009"}
```

**Don't**:
- Don't forget the default port for localhost mode

**Verify**: `grep -A 15 "caddy:" docker-compose.yml | grep COMFYUI`

---

### Task 8: Update service_dependencies.py with ComfyUI configs

**Why**: The Management UI needs service configuration to display ComfyUI in the services list with proper grouping and profiles.

**Mirror**: `management-ui/backend/app/core/service_dependencies.py:149-197` (Ollama configs)

**Do**:
Add after the flowise config (around line 197):
```python
"comfyui-cpu": ServiceConfig(
    name="comfyui-cpu",
    display_name="ComfyUI (CPU)",
    description="Node-based image generation on CPU",
    group="core_ai",
    dependencies=[],
    profiles=["cpu"],
    default_enabled=False,
    category="optional"
),
"comfyui-gpu": ServiceConfig(
    name="comfyui-gpu",
    display_name="ComfyUI (NVIDIA GPU)",
    description="Node-based image generation with NVIDIA CUDA",
    group="core_ai",
    dependencies=[],
    profiles=["gpu-nvidia"],
    default_enabled=False,
    category="optional"
),
"comfyui-gpu-amd": ServiceConfig(
    name="comfyui-gpu-amd",
    display_name="ComfyUI (AMD GPU)",
    description="Node-based image generation with AMD ROCm",
    group="core_ai",
    dependencies=[],
    profiles=["gpu-amd"],
    default_enabled=False,
    category="optional"
),
```

Note: `default_enabled=False` because ComfyUI is resource-intensive and not everyone needs it.

**Don't**:
- Don't add dependencies on Ollama (they're independent services)

**Verify**: `grep -A 5 "comfyui" management-ui/backend/app/core/service_dependencies.py`

---

### Task 9: Update dependency_graph.py SERVICE_GROUPS

**Why**: ComfyUI services need to be added to the core_ai group for proper UI grouping.

**Mirror**: `management-ui/backend/app/core/dependency_graph.py:17-22` (core_ai group)

**Do**:
Update the core_ai services list:
```python
"core_ai": {
    "name": "AI Services",
    "services": ["ollama-cpu", "ollama-gpu", "ollama-gpu-amd",
                 "open-webui", "flowise",
                 "comfyui-cpu", "comfyui-gpu", "comfyui-gpu-amd"],
    "description": "Core AI inference and interfaces"
},
```

**Don't**:
- Don't create a separate group (image generation is part of AI services)

**Verify**: `grep -A 5 "core_ai" management-ui/backend/app/core/dependency_graph.py | grep comfyui`

---

### Task 10: Update serviceUrls.ts for UI URL mapping

**Why**: The Management UI needs to know how to generate the "Open" link for ComfyUI.

**Mirror**: `management-ui/frontend/src/utils/serviceUrls.ts:12-29` (SERVICE_URL_MAP)

**Do**:
Add to SERVICE_URL_MAP:
```typescript
// Image Generation
'comfyui-cpu': { port: 8188, name: 'ComfyUI' },
'comfyui-gpu': { port: 8188, name: 'ComfyUI' },
'comfyui-gpu-amd': { port: 8188, name: 'ComfyUI' },
```

Note: All variants point to the same port since only one runs at a time based on profile.

**Don't**:
- Don't add path suffix (ComfyUI serves UI at root)

**Verify**: `grep comfyui management-ui/frontend/src/utils/serviceUrls.ts`

---

## Validation Strategy

### Automated Checks
- [ ] `docker compose config --profiles cpu` - Validates compose syntax for CPU profile
- [ ] `docker compose config --profiles gpu-nvidia` - Validates compose syntax for NVIDIA profile
- [ ] `docker compose config --profiles gpu-amd` - Validates compose syntax for AMD profile
- [ ] Caddy config validation (caddy validate) - Validates Caddyfile syntax

### Manual Validation Steps

**1. Start with CPU profile:**
```bash
python start_services.py --profile cpu --environment private
docker compose -p localai ps | grep comfyui
```
Expected: comfyui-cpu container running

**2. Access ComfyUI:**
```bash
curl -s http://localhost:8188 | head -20
```
Expected: HTML response with ComfyUI interface

**3. Access via Caddy:**
```bash
curl -s http://localhost:8009 | head -20
```
Expected: Same HTML response proxied through Caddy

**4. Check Management UI:**
- Navigate to http://localhost:9009
- Login and go to Services page
- Verify "ComfyUI (CPU)" appears in AI Services group
- Verify start/stop/restart buttons work
- Verify "Open" link works when running
- Verify logs link works when running

**5. Test GPU profile (if NVIDIA available):**
```bash
python start_services.py --profile gpu-nvidia --environment private
docker compose -p localai ps | grep comfyui
nvidia-smi | grep comfyui  # Should show GPU usage
```

### Edge Cases to Test
- [ ] Starting ComfyUI with insufficient disk space for models
- [ ] Switching between CPU and GPU profiles (only one should run)
- [ ] ComfyUI with no models installed (should still show interface)
- [ ] Large file upload (test MAX_UPLOAD_MB setting)
- [ ] WebSocket connection for workflow execution

### Regression Check
- [ ] Existing Ollama services still work with all profiles
- [ ] Open WebUI can still connect to Ollama
- [ ] Other services (n8n, Flowise, etc.) unaffected
- [ ] Management UI service list doesn't break

## Risks

1. **AMD Image Size**: The ROCm-based image is very large (~23GB). Consider documenting this and suggesting local builds.

2. **First Startup Time**: ComfyUI may take several minutes on first startup to initialize. The Management UI might show "starting" for a while.

3. **Resource Contention**: Running ComfyUI alongside Ollama on the same GPU could cause VRAM issues. Consider documenting this limitation.

4. **No Pre-built AMD Image**: Using runtime installation for AMD is slower and less reliable. May want to track if joepitt91 adds AMD support.

5. **Model Storage Size**: Stable Diffusion models are 2-8GB each. Users may need to manage disk space carefully.

## Alternative AMD Implementation

If the runtime AMD installation proves unreliable, consider using the ai-dock image instead:

```yaml
comfyui-gpu-amd:
  profiles: ["gpu-amd"]
  image: ghcr.io/ai-dock/comfyui:rocm-pytorch-latest
  container_name: comfyui
  restart: unless-stopped
  expose:
    - 8188/tcp
  devices:
    - "/dev/kfd"
    - "/dev/dri"
  volumes:
    - comfyui_models:/opt/ComfyUI/models
    - comfyui_output:/opt/ComfyUI/output
    - comfyui_input:/opt/ComfyUI/input
    - comfyui_custom_nodes:/opt/ComfyUI/custom_nodes
```

Note: ai-dock uses different paths - adjust volume mounts accordingly.
