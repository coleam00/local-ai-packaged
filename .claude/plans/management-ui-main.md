# Plan: Stack Management UI for local-ai-packaged

> **This plan has been split into 10 staged implementation files.**
>
> See: `.claude/plans/management-ui/00-overview.md` for the full breakdown.
>
> Execute stages in order: `/implement .claude/plans/management-ui/01-backend-core.md`

## Summary

Build a modern web UI (FastAPI + React/Vite) as a Docker container that provides complete management of the local-ai-packaged stack. The UI will handle initial setup, service configuration, dependency-aware service control, real-time monitoring, and log streaming. It replaces `start_services.py` with a more robust API-driven approach.

## External Research

### Key Documentation
- [Docker SDK for Python](https://docker-py.readthedocs.io/) - Container management API
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/) - Real-time log streaming
- [React Flow](https://reactflow.dev/) - Dependency graph visualization
- [Zustand](https://zustand-demo.pmnd.rs/) - Lightweight React state management

### Best Practices Found
- Use docker-py for container status/logs, but `docker compose` CLI for orchestration (respects full compose spec)
- Multi-stage Docker builds reduce image from 1GB to ~50MB
- SQLite for UI state (self-contained, no circular dependencies)
- WebSocket for real-time updates, polling every 2s for status

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    management-ui container                   │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐ │
│  │ React/Vite   │◄──►│   FastAPI    │◄──►│  Docker SDK   │ │
│  │ (nginx:80)   │    │   (uvicorn)  │    │  + Compose    │ │
│  └──────────────┘    └──────────────┘    └───────────────┘ │
│                             │                               │
│                      ┌──────┴──────┐                       │
│                      │   SQLite    │                       │
│                      │  (auth/state)│                       │
│                      └─────────────┘                       │
└─────────────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
    /var/run/docker.sock    /config (mounted project dir)
```

---

## Service Dependency Graph (from docker-compose.yml)

```
TIER 1 (No dependencies - start first):
  vector, postgres, clickhouse, minio, redis, imgproxy,
  flowise, open-webui, qdrant, neo4j, caddy, searxng

TIER 2 (Database dependencies):
  db (Supabase) → depends on: vector (healthy)

TIER 3 (Supabase core):
  analytics → depends on: db (healthy)

TIER 4 (Supabase services):
  kong, auth, rest, realtime, meta, functions, supavisor, studio
  → all depend on: db + analytics (healthy)

  storage → depends on: db + rest + imgproxy

TIER 5 (Application layer):
  n8n-import (init container, runs once)
  n8n → depends on: n8n-import (completed_successfully)

  langfuse-worker, langfuse-web
  → depends on: postgres + minio + redis + clickhouse (all healthy)

PROFILE-BASED (mutually exclusive):
  ollama-cpu (profile: cpu)
  ollama-gpu (profile: gpu-nvidia)
  ollama-gpu-amd (profile: gpu-amd)
  → each has init container: ollama-pull-llama-*
```

---

## Files to Create

### Backend Structure
```
management-ui/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, CORS, lifespan
│   │   ├── config.py               # Settings from env vars
│   │   ├── database.py             # SQLite + SQLAlchemy
│   │   │
│   │   ├── api/
│   │   │   ├── deps.py             # Dependency injection
│   │   │   ├── routes/
│   │   │   │   ├── auth.py         # Login, logout, setup admin
│   │   │   │   ├── services.py     # Start/stop/restart/list
│   │   │   │   ├── config.py       # .env management
│   │   │   │   ├── logs.py         # Log streaming
│   │   │   │   ├── health.py       # Health endpoints
│   │   │   │   └── setup.py        # Initial setup wizard
│   │   │   └── websocket.py        # WS handlers for logs/status
│   │   │
│   │   ├── core/
│   │   │   ├── security.py         # JWT, password hashing
│   │   │   ├── docker_client.py    # docker-py wrapper
│   │   │   ├── compose_parser.py   # YAML parsing
│   │   │   ├── dependency_graph.py # Topological sort
│   │   │   ├── secret_generator.py # Key generation
│   │   │   └── env_manager.py      # .env file ops
│   │   │
│   │   ├── models/
│   │   │   ├── user.py             # User model
│   │   │   └── audit_log.py        # Action logging
│   │   │
│   │   ├── schemas/                # Pydantic models
│   │   └── services/               # Business logic
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── api/                    # API client
│   │   ├── components/
│   │   │   ├── layout/             # Header, Sidebar
│   │   │   ├── services/           # ServiceCard, DependencyGraph
│   │   │   ├── config/             # ConfigEditor, SecretField
│   │   │   ├── logs/               # LogViewer, LogStream
│   │   │   └── setup/              # Wizard steps
│   │   ├── hooks/                  # useAuth, useServices, useWebSocket
│   │   ├── pages/                  # Dashboard, Services, Config, Logs, Setup
│   │   ├── store/                  # Zustand state
│   │   └── types/
│   │
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── Dockerfile                      # Combined multi-stage
├── docker-compose.management.yml
└── nginx.conf
```

---

## Files to Modify

| File | Change |
|------|--------|
| `docker-compose.yml` | Add `include: ./docker-compose.management.yml` |
| `Caddyfile` | Add management UI reverse proxy route |
| `.env.example` | Add `MANAGEMENT_SECRET_KEY` variable |

---

## API Endpoints

### Authentication
```
POST /api/auth/login          # Username/password → JWT
POST /api/auth/logout
GET  /api/auth/me
POST /api/auth/setup          # First-run admin creation
```

### Services
```
GET    /api/services                    # List all with status
GET    /api/services/{name}             # Service details
POST   /api/services/{name}/start       # Start (resolves dependencies)
POST   /api/services/{name}/stop        # Stop (warns about dependents)
POST   /api/services/{name}/restart
GET    /api/services/dependencies       # Full graph for visualization
POST   /api/services/groups/{group}/start
```

### Configuration
```
GET    /api/config                      # All vars (secrets masked)
GET    /api/config/schema               # Validation rules
PUT    /api/config                      # Update .env
POST   /api/config/generate-secrets     # Generate all secrets
GET    /api/config/backup               # Download backup
POST   /api/config/restore              # Restore from backup
```

### Setup Wizard
```
GET  /api/setup/status         # Check if setup needed
POST /api/setup/complete       # Run full setup + start stack
```

### WebSocket
```
WS /ws/status                  # Real-time service status
WS /ws/logs/{service}          # Stream container logs
```

---

## Key Implementation Details

### 1. Docker Client (replaces start_services.py)

```python
# core/docker_client.py
class DockerClient:
    def __init__(self, project="localai", base_path="/config"):
        self.client = docker.from_env()
        self.project = project
        self.base_path = base_path

    def list_containers(self):
        return self.client.containers.list(
            all=True,
            filters={"label": f"com.docker.compose.project={self.project}"}
        )

    def compose_up(self, services=None, profile=None, environment="private"):
        cmd = self._build_compose_cmd(profile, environment)
        cmd.extend(["up", "-d"])
        if services:
            cmd.extend(services)
        return subprocess.run(cmd, cwd=self.base_path, capture_output=True)

    def stream_logs(self, service, tail=100):
        container = self.get_container(service)
        for log in container.logs(stream=True, tail=tail, follow=True):
            yield log.decode("utf-8", errors="replace")
```

### 2. Dependency Resolution

```python
# core/dependency_graph.py
class DependencyGraph:
    def get_start_order(self, services: List[str]) -> List[List[str]]:
        """Return batches for parallel starting."""
        # Topological sort with batching

    def get_dependents(self, service: str) -> Set[str]:
        """Services that depend on this one."""

    def get_dependencies(self, service: str) -> Set[str]:
        """Services this one depends on."""
```

### 3. Secret Generation

```python
# core/secret_generator.py
def generate_all_secrets() -> dict:
    jwt_secret = secrets.token_hex(32)
    return {
        "N8N_ENCRYPTION_KEY": secrets.token_hex(32),
        "POSTGRES_PASSWORD": generate_safe_password(24),
        "JWT_SECRET": jwt_secret,
        "ANON_KEY": generate_supabase_jwt("anon", jwt_secret),
        "SERVICE_ROLE_KEY": generate_supabase_jwt("service_role", jwt_secret),
        # ... all 15+ required secrets
    }
```

### 4. Frontend State (Zustand)

```typescript
// store/index.ts
interface AppState {
  services: Service[];
  fetchServices: () => Promise<void>;
  startService: (name: string) => Promise<void>;
  updateServiceStatus: (name: string, status: string) => void;
}
```

---

## Docker Deployment

### docker-compose.management.yml
```yaml
services:
  management-ui:
    build: ./management-ui
    container_name: localai-management
    ports:
      - "127.0.0.1:9000:9000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - .:/config:ro
      - ./.env:/config/.env:rw
      - management-data:/data
    environment:
      - DATABASE_URL=sqlite:////data/management.db
      - COMPOSE_BASE_PATH=/config
      - SECRET_KEY=${MANAGEMENT_SECRET_KEY:-changeme}
    networks:
      - localai_default
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/api/health"]

volumes:
  management-data:

networks:
  localai_default:
    external: true
```

---

## Implementation Tasks

### Phase 1: Backend Foundation
1. Create `management-ui/` directory structure
2. Implement `core/docker_client.py` - Docker SDK wrapper
3. Implement `core/compose_parser.py` - Parse docker-compose.yml
4. Implement `core/dependency_graph.py` - Topological sort
5. Implement `core/env_manager.py` - .env file operations
6. Implement `core/secret_generator.py` - All secret generation
7. Setup SQLite database with User model
8. Implement `core/security.py` - JWT auth

### Phase 2: API Routes
9. Implement `/api/auth/*` routes
10. Implement `/api/services/*` routes
11. Implement `/api/config/*` routes
12. Implement `/api/setup/*` routes
13. Implement `/api/health` route
14. Implement WebSocket handlers for logs/status

### Phase 3: Frontend
15. Setup Vite + React + TypeScript + Tailwind
16. Create API client with Axios
17. Implement auth pages (Login, first-run setup)
18. Implement Dashboard with service overview
19. Implement Services page with start/stop/restart
20. Implement DependencyGraph visualization (react-flow)
21. Implement Config editor with validation
22. Implement LogViewer with WebSocket streaming
23. Implement Setup Wizard (5 steps)

### Phase 4: Integration
24. Create combined Dockerfile (multi-stage)
25. Create docker-compose.management.yml
26. Update main docker-compose.yml to include management
27. Add Caddy route for management UI
28. Update .env.example

### Phase 5: Polish
29. Add service group management (start/stop groups)
30. Add config backup/restore
31. Add audit logging
32. Error handling and validation messages

---

## Validation Strategy

### Automated Checks
- [ ] Backend: `pytest` for API routes
- [ ] Frontend: `npm run type-check` + `npm run build`
- [ ] Container: `docker build` succeeds

### Manual Validation
1. Start management UI container alone
2. Verify login with admin credentials
3. Test service start/stop for individual services
4. Test dependency warning when stopping required service
5. Test log streaming via WebSocket
6. Test config editor saves correctly to .env
7. Run full setup wizard on fresh install
8. Verify all services start in correct order

### Edge Cases
- [ ] Services with no containers (not started yet)
- [ ] Container crashes during operation
- [ ] Invalid .env values (validation errors)
- [ ] Docker socket not accessible
- [ ] Supabase repo not cloned yet

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Docker socket access security | Bind only to 127.0.0.1, require auth |
| Circular dependency (UI needs DB) | Use SQLite, not Supabase for UI state |
| Compose file parsing edge cases | Use docker compose CLI for operations, parse YAML only for metadata |
| Secret exposure in logs | Mask secrets in API responses, never log values |

---

## NOT Building (Out of Scope)

- Kubernetes/Swarm support
- Multi-node orchestration
- Automated backups scheduling
- Email notifications
- Mobile app
- Metrics/Prometheus integration (Langfuse handles this)
