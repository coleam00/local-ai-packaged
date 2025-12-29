# Plan: Feature Ideas Analysis for Local-AI-Packaged

## Summary

This document analyzes the current services in the local-ai-packaged project and proposes actionable feature implementations based on:
1. Current service capabilities and architecture
2. Open GitHub issues and user requests
3. Industry best practices for self-hosted AI infrastructure management in 2025

This is a **research and analysis plan**, not an implementation plan. The output provides prioritized feature recommendations for user consideration.

---

## Current Services Analysis

### Core AI & LLM Services
| Service | Purpose | Internal Port | External Port (Private) |
|---------|---------|---------------|------------------------|
| Ollama | Local LLM inference (CPU/GPU) | 11434 | 8004 |
| Open WebUI | ChatGPT-like interface | 8080 | 8002 |
| Flowise | No-code AI agent builder | 3001 | 8003 |
| n8n | Workflow automation | 5678 | 8001 |

### Database & Storage
| Service | Purpose | Notes |
|---------|---------|-------|
| Supabase (full stack) | Database, Auth, API, Storage, Studio | 10+ sub-services |
| Qdrant | Vector database | Port 6333/6334 |
| Neo4j | Knowledge graph | Port 7687 (bolt), 7474 (browser) |
| Redis (Valkey) | In-memory cache | Internal |
| ClickHouse | Time-series analytics | For Langfuse |
| MinIO | S3-compatible storage | For Langfuse |

### Observability & Infrastructure
| Service | Purpose |
|---------|---------|
| Langfuse | LLM observability platform |
| Caddy | Reverse proxy with auto-TLS |
| SearXNG | Privacy-respecting metasearch |

### Management UI (In Development)
- Service monitoring and control
- Setup wizard with preflight checks
- Configuration editor
- Log streaming
- Dependency graph visualization

---

## GitHub Issues Analysis

### Open Feature Requests (Enhancement)
| # | Title | Priority | Complexity |
|---|-------|----------|------------|
| 161/137 | Add Portainer | Medium | Low |
| 159 | n8n worker service (queue mode) | High | Medium |
| 157 | Perplexica integration | Medium | Medium |
| 156 | Local storage paths instead of volumes | Medium | Medium |
| 164 | SWAG compatibility & security headers | Medium | Medium |
| 162 | PostgreSQL 18+ migration | Low | High |
| 152 | ComfyUI support | Medium | Medium |

### Recurring Bug Patterns
| Pattern | Issues | Root Cause |
|---------|--------|------------|
| Supabase startup issues | 173, 167, 165 | Complex dependencies, platform-specific |
| Service configuration | 174, 145, 138 | .env handling, first-run issues |
| Neo4j connectivity | 139, 138 | Password sync, network config |
| Langfuse failures | 166, 167 | ClickHouse/MinIO dependencies |

---

## Feature Recommendations

### Tier 1: High-Impact, Aligns with Existing Work (Implement First)

#### 1. Service Health Dashboard Enhancement
**Why**: The management UI already has basic service monitoring. Enhancing it addresses issues #167, #166, and provides visibility users need.

**Features**:
- Real-time health metrics (CPU, memory, network per container)
- Health history graphs (last 24 hours)
- Automatic health alerts/notifications
- Quick diagnostics for common issues
- Service restart recommendations based on error patterns

**Complexity**: Medium
**Value**: High - Directly addresses user pain points in GitHub issues

---

#### 2. First-Run Wizard Improvements
**Why**: Many issues (173, 167, 165, 144) stem from setup problems. Better first-run experience prevents support burden.

**Features**:
- Hardware detection (GPU type, available memory, disk space)
- Automatic service recommendations based on hardware
- Dependency pre-flight validation (Docker version, socket access)
- Common configuration presets (minimal, standard, full)
- Platform-specific guidance (Windows WSL2, Linux, macOS)
- .env validation with helpful error messages

**Complexity**: Medium
**Value**: High - Prevents most common issues

---

#### 3. n8n Queue Mode with Workers (Issue #159)
**Why**: Users requested this. n8n in queue mode scales better for production workflows.

**Features**:
- Add n8n-worker service profile
- Redis as queue backend (already available)
- Configurable worker count
- Health monitoring for workers
- Documentation for queue mode setup

**Complexity**: Medium
**Value**: High - Enables production-grade n8n usage

---

### Tier 2: Medium-Impact, Good User Value

#### 4. Portainer Integration (Issues #161, #137)
**Why**: Multiple users requested this. Provides advanced container management alongside the custom management UI.

**Features**:
- Optional Portainer service profile
- Pre-configured for the local-ai stack
- Disabled by default (users opt-in)
- Integration with Caddy routing

**Complexity**: Low
**Value**: Medium - Users familiar with Portainer can use it

---

#### 5. Backup & Restore System
**Why**: No current backup solution. Critical for production deployments.

**Features**:
- Automated volume backups
- Scheduled backup jobs
- S3/MinIO backup destination (already have MinIO)
- One-click restore
- Backup verification
- Configuration backup (already partially implemented)

**Complexity**: Medium-High
**Value**: High - Essential for production use

---

#### 6. ComfyUI Integration (Issue #152)
**Why**: ComfyUI is popular for image generation. Natural fit alongside Ollama.

**Features**:
- ComfyUI service with GPU profile
- Shared model storage with Ollama
- Caddy reverse proxy routing
- Management UI integration

**Complexity**: Medium
**Value**: Medium-High - Popular for AI image workflows

---

#### 7. Local Storage Path Support (Issue #156)
**Why**: Users want to use local directories instead of Docker volumes for easier access.

**Features**:
- Environment variable toggles for bind mounts
- Path validation in setup wizard
- Migration tool (volumes to local paths)
- Documentation for path-based setup

**Complexity**: Medium
**Value**: Medium - Power user feature

---

### Tier 3: Nice-to-Have, Lower Priority

#### 8. Perplexica Integration (Issue #157)
**Why**: AI-powered search/answer complements the existing stack.

**Features**:
- Perplexica service definition
- Integration with SearXNG backend
- Ollama connection for local LLM

**Complexity**: Medium
**Value**: Medium

---

#### 9. Service Templates/Presets
**Why**: Simplify selection for different use cases.

**Presets**:
- **Minimal AI**: Ollama + Open WebUI only
- **Developer**: + n8n + Flowise + Supabase
- **Full Stack**: Everything enabled
- **Knowledge Base**: + Neo4j + Qdrant
- **Custom**: User selection

**Complexity**: Low
**Value**: Medium - Better UX for new users

---

#### 10. Multi-Instance Support
**Why**: Some users want multiple Ollama instances or test environments.

**Features**:
- Named environment profiles
- Port range allocation
- Instance isolation
- Resource quotas per instance

**Complexity**: High
**Value**: Low-Medium - Advanced use case

---

### Tier 4: Future Considerations

#### 11. Cluster Mode / Multi-Node
**Why**: Scale beyond single machine for production.

**Features**:
- Docker Swarm support
- Kubernetes helm charts (separate project)
- Load balancing configuration

**Complexity**: Very High
**Value**: Medium - Enterprise feature

---

#### 12. AI Model Management
**Why**: Centralize model handling across Ollama, Flowise, etc.

**Features**:
- Model catalog browser
- One-click model downloads
- Model storage management
- GPU VRAM estimation per model

**Complexity**: High
**Value**: High - Great UX improvement

---

## Implementation Prioritization Matrix

| Feature | User Demand | Complexity | Strategic Value | Priority Score |
|---------|-------------|------------|-----------------|----------------|
| Service Health Dashboard | High | Medium | High | **9/10** |
| First-Run Wizard Improvements | High | Medium | High | **9/10** |
| n8n Queue Mode (Issue #159) | Direct | Medium | Medium | **8/10** |
| Backup & Restore | Medium | Medium-High | High | **8/10** |
| Portainer (Issues #161, #137) | Direct | Low | Medium | **7/10** |
| ComfyUI (Issue #152) | Direct | Medium | Medium | **7/10** |
| Local Storage Paths (#156) | Direct | Medium | Medium | **6/10** |
| Service Presets | Medium | Low | Medium | **6/10** |
| Perplexica (#157) | Direct | Medium | Low | **5/10** |
| Model Management | Low | High | High | **5/10** |
| Multi-Instance | Low | High | Low | **3/10** |

---

## Quick Wins (Can Implement This Week)

These require minimal changes and address real user needs:

### 1. Portainer Service Profile
```yaml
# Add to docker-compose.yml
portainer:
  image: portainer/portainer-ce:latest
  container_name: portainer
  restart: unless-stopped
  profiles: ["portainer"]
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - portainer_data:/data
  ports:
    - "127.0.0.1:9443:9443"
```

### 2. Service Presets in Management UI
Add preset selection to the setup wizard - purely frontend change using existing service selection logic.

### 3. Hardware Detection in Setup
Add system info API endpoint that returns:
- GPU availability (nvidia-smi / rocm-smi detection)
- Available RAM
- Disk space
- Docker version

---

## Addressing Common Bug Patterns

Many GitHub issues stem from predictable problems. Proactive solutions:

| Problem Pattern | Solution |
|----------------|----------|
| Supabase startup failures | Dependency-aware startup with health checks |
| .env configuration errors | Validation API with specific error messages |
| Neo4j password issues | First-run detection and guided reset |
| Platform-specific issues | Platform detection in setup wizard |
| Port conflicts | Port availability check before startup |

These could be implemented as **preflight checks** in the existing setup wizard.

---

## External Research References

### Self-Hosted AI Best Practices 2025
- [Self-hosting AI models guide](https://northflank.com/blog/self-hosting-ai-models-guide) - Infrastructure patterns
- [Solo AI Startup Infrastructure](https://www.nucamp.co/blog/solo-ai-tech-entrepreneur-2025-setting-up-a-selfhosted-solo-ai-startup-infrastructure-best-practices) - Best practices
- [AI Infrastructure Guide](https://www.beehivesoftware.com/ai-infrastructure-guide/) - Complete guide

### Container Orchestration
- [Docker Compose Guide 2025](https://dokploy.com/blog/how-to-deploy-apps-with-docker-compose-in-2025) - Modern patterns
- [Container Orchestration Tools](https://www.devopsschool.com/blog/top-10-container-orchestration-tools-in-2025-features-pros-cons-comparison/) - Tool comparison
- [Portainer Documentation](https://docs.portainer.io/user/docker/dashboard) - Dashboard features

---

## Recommended Next Steps

1. **Immediate**: Pick 1-2 features from Tier 1 and create detailed implementation plans
2. **Short-term**: Implement quick wins (Portainer, presets, hardware detection)
3. **Medium-term**: Address recurring bug patterns through better preflight checks
4. **Long-term**: Consider model management and multi-node features

---

## Questions for User Decision

Before implementation, consider:

1. **Which tier of features is most valuable to you right now?**
   - Tier 1: Core improvements (health, setup, n8n workers)
   - Tier 2: New capabilities (Portainer, backup, ComfyUI)
   - Tier 3: Nice-to-haves (presets, Perplexica)

2. **For Portainer**: Do you want it as opt-in (profile-based) or should it replace the custom management UI?

3. **For n8n workers**: What's your expected workflow volume? This affects worker configuration.

4. **For backup**: What backup destination is preferred? (Local, S3, MinIO, external NAS)

5. **Any features NOT listed that you'd like explored?**

---

## Plan File Info

**Created**: 2025-12-27
**Type**: Research/Analysis (not implementation)
**Status**: Ready for user review

To implement any specific feature, create a focused implementation plan with:
```
/exp-piv-loop:plan <specific feature description>
```
