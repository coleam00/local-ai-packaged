# Plan: AI Model Management

## Summary

Build a centralized model management interface that allows users to browse, download, and manage Ollama models from the Management UI. The feature includes a model catalog browser, one-click downloads with real-time progress via WebSocket, GPU VRAM estimation per model, disk storage tracking, and model cleanup capabilities. This replaces CLI-based model operations with a user-friendly interface.

The implementation follows existing patterns: a new backend service (`ollama_service.py`) with API routes (`models.py`), a dedicated frontend page (`Models.tsx`) with Zustand store, and WebSocket streaming for download progress (mirroring the log streaming pattern).

---

## External Research

### Ollama API Documentation
- [Ollama API Reference](https://github.com/ollama/ollama/blob/main/docs/api.md) - Official API docs
  - Key endpoints: `/api/tags` (list), `/api/pull` (download), `/api/delete` (remove), `/api/show` (details)

### Key API Endpoints

| Method | Endpoint | Purpose | Streaming |
|--------|----------|---------|-----------|
| GET | `/api/tags` | List installed models | No |
| POST | `/api/show` | Get model details (size, parameters, quantization) | No |
| POST | `/api/pull` | Download model from library | Yes (progress) |
| DELETE | `/api/delete` | Delete a model | No |

### VRAM Requirements (from research)
- **7B models (Q4)**: ~4-6 GB VRAM
- **13B models (Q4)**: ~8-10 GB VRAM
- **30B models (Q4)**: ~16-20 GB VRAM
- **70B models (Q4)**: ~35-40 GB VRAM
- FP16 roughly doubles these requirements
- KV cache adds ~0.5GB per 8K context for 8B models

Sources:
- [Ollama VRAM Requirements Guide](https://localllm.in/blog/ollama-vram-requirements-for-local-llms)
- [GPU Selection for LLMs](https://www.databasemart.com/blog/choosing-the-right-gpu-for-popluar-llms-on-ollama)

### Gotchas & Best Practices
1. **Pull operations stream JSON objects** - Each chunk contains `status`, `digest`, `total`, `completed` fields
2. **Cancelled pulls resume from where they left off** - Ollama handles partial downloads
3. **Multiple concurrent pulls share progress** - Same model pull from different clients merges
4. **Model size on disk differs from VRAM requirement** - Quantized models are smaller on disk
5. **Model names have tags** - `llama3.2:7b-instruct` vs `llama3.2:latest`

---

## Patterns to Mirror

### Backend Service Pattern
From `/opt/local-ai-packaged/management-ui/backend/app/services/docker_service.py`:

```python
# Service class structure
class DockerService:
    """Service layer for Docker operations."""

    def __init__(
        self,
        docker_client: DockerClient,
        parser: ComposeParser,
        graph: DependencyGraph
    ):
        self.docker = docker_client
        self.parser = parser
        self.graph = graph

    def list_services(self) -> List[ServiceInfo]:
        """List all services with their current status."""
        # ... implementation
```

### API Route Pattern
From `/opt/local-ai-packaged/management-ui/backend/app/api/routes/services.py`:

```python
router = APIRouter()

def get_docker_service(
    docker_client: DockerClient = Depends(get_docker_client),
    parser: ComposeParser = Depends(get_compose_parser),
    graph: DependencyGraph = Depends(get_dependency_graph)
) -> DockerService:
    return DockerService(docker_client, parser, graph)

@router.get("", response_model=ServiceListResponse)
async def list_services(
    docker_service: DockerService = Depends(get_docker_service),
    _: dict = Depends(get_current_user)  # Require auth
):
    """List all services with their current status."""
    services = docker_service.list_services()
    return ServiceListResponse(services=services, total=len(services))
```

### WebSocket Pattern
From `/opt/local-ai-packaged/management-ui/backend/app/api/websocket.py`:

```python
async def stream_service_logs(
    websocket: WebSocket,
    service_name: str,
    tail: int = 100
):
    """Stream logs for a specific service."""
    # ... setup ...
    try:
        async for log_line in async_log_generator():
            await websocket.send_json({
                "type": "log",
                "service": service_name,
                "content": log_line.strip()
            })
    except WebSocketDisconnect:
        pass
```

### Frontend Page Pattern
From `/opt/local-ai-packaged/management-ui/frontend/src/pages/Services.tsx`:

```tsx
export const Services: React.FC = () => {
  const {
    services,
    isLoading,
    error,
    actionInProgress,
    fetchServices,
    // ...
  } = useServicesStore();

  useEffect(() => {
    fetchServices();
    const interval = setInterval(fetchServices, 5000);
    return () => clearInterval(interval);
  }, [fetchServices]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        {/* ... */}
      </div>
      {/* Content */}
      {/* ... */}
    </div>
  );
};
```

### Zustand Store Pattern
From `/opt/local-ai-packaged/management-ui/frontend/src/store/servicesStore.ts`:

```typescript
interface ServicesState {
  services: ServiceInfo[];
  isLoading: boolean;
  error: string | null;
  actionInProgress: string | null;

  fetchServices: () => Promise<void>;
  startService: (name: string) => Promise<boolean>;
  // ...
}

export const useServicesStore = create<ServicesState>((set, get) => ({
  services: [],
  isLoading: false,
  error: null,
  actionInProgress: null,

  fetchServices: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await servicesApi.list();
      set({ services: response.services, isLoading: false });
    } catch (error) {
      // ... error handling
    }
  },
  // ...
}));
```

### API Client Pattern
From `/opt/local-ai-packaged/management-ui/frontend/src/api/services.ts`:

```typescript
export const servicesApi = {
  async list(): Promise<ServiceListResponse> {
    const response = await apiClient.get<ServiceListResponse>('/services');
    return response.data;
  },

  async start(name: string, options?: ServiceActionRequest): Promise<ServiceActionResponse> {
    const response = await apiClient.post<ServiceActionResponse>(
      `/services/${name}/start`,
      options || {}
    );
    return response.data;
  },
};
```

---

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `backend/app/schemas/model.py` | CREATE | Pydantic schemas for model data (ModelInfo, PullProgress, etc.) |
| `backend/app/services/ollama_service.py` | CREATE | Service layer for Ollama API operations |
| `backend/app/services/__init__.py` | UPDATE | Export OllamaService |
| `backend/app/api/routes/models.py` | CREATE | REST API endpoints for model operations |
| `backend/app/api/routes/__init__.py` | UPDATE | Register models router |
| `backend/app/api/websocket.py` | UPDATE | Add WebSocket handler for model pull progress |
| `frontend/src/types/model.ts` | CREATE | TypeScript types for models |
| `frontend/src/api/models.ts` | CREATE | API client for model endpoints |
| `frontend/src/api/websocket.ts` | UPDATE | Add WebSocket factory for model pulls |
| `frontend/src/hooks/useModelPull.ts` | CREATE | Hook for model download with progress |
| `frontend/src/store/modelsStore.ts` | CREATE | Zustand store for models state |
| `frontend/src/pages/Models.tsx` | CREATE | Main models page component |
| `frontend/src/components/models/ModelCard.tsx` | CREATE | Individual model display card |
| `frontend/src/components/models/ModelCatalog.tsx` | CREATE | Browsable model catalog |
| `frontend/src/components/models/PullProgress.tsx` | CREATE | Download progress display |
| `frontend/src/components/models/index.ts` | CREATE | Component exports |
| `frontend/src/App.tsx` | UPDATE | Add /models route |
| `frontend/src/components/layout/Sidebar.tsx` | UPDATE | Add Models navigation link |

---

## NOT Building

- Model fine-tuning or customization (out of scope)
- Model versioning or rollback
- Automatic model recommendations (Phase 2)
- Model benchmarking or performance testing
- Multi-Ollama instance support
- Model sharing between services (Open WebUI has its own model management)
- Ollama model library web scraping (use static popular models list + search)

---

## Tasks

### Task 1: Create Model Schemas

**Why**: Define data structures for model information and operations. Required before implementing service layer.

**File**: `management-ui/backend/app/schemas/model.py`

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum


class ModelInfo(BaseModel):
    """Information about an installed model."""
    name: str
    model: str  # Full model identifier with tag
    size: int  # Size in bytes
    digest: str  # Model digest/hash
    modified_at: str  # ISO timestamp
    details: Optional[Dict] = None  # Additional model details


class ModelDetails(BaseModel):
    """Detailed model information from /api/show."""
    modelfile: Optional[str] = None
    parameters: Optional[str] = None
    template: Optional[str] = None
    system: Optional[str] = None
    license: Optional[str] = None
    format: Optional[str] = None
    family: Optional[str] = None
    families: Optional[List[str]] = None
    parameter_size: Optional[str] = None  # e.g., "7B"
    quantization_level: Optional[str] = None  # e.g., "Q4_K_M"


class ModelListResponse(BaseModel):
    """Response for listing models."""
    models: List[ModelInfo]
    total: int
    total_size: int  # Total disk usage in bytes


class PullStatus(str, Enum):
    """Status of a model pull operation."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class PullProgress(BaseModel):
    """Progress update for model download."""
    status: PullStatus
    digest: Optional[str] = None
    total: int = 0
    completed: int = 0
    message: Optional[str] = None


class PullRequest(BaseModel):
    """Request to pull a model."""
    model: str  # Model name to pull


class PullResponse(BaseModel):
    """Response after initiating a pull."""
    success: bool
    message: str
    model: str


class DeleteResponse(BaseModel):
    """Response after deleting a model."""
    success: bool
    message: str
    model: str


class VramEstimate(BaseModel):
    """VRAM requirement estimate for a model."""
    model: str
    parameter_size: str  # e.g., "7B"
    quantization: str  # e.g., "Q4_K_M"
    estimated_vram_gb: float
    recommended_gpu: str  # e.g., "8GB+ VRAM (RTX 3070, etc.)"


class CatalogModel(BaseModel):
    """A model from the catalog (for browsing)."""
    name: str
    description: str
    tags: List[str]  # Available tags/versions
    parameter_sizes: List[str]  # e.g., ["7B", "13B", "70B"]
    recommended_tag: str  # Default recommended tag
    category: str  # e.g., "chat", "code", "vision"
    vram_requirements: Dict[str, float]  # tag -> estimated GB
```

**Verify**: `python -c "from app.schemas.model import *; print('OK')"`

---

### Task 2: Create Ollama Service

**Why**: Business logic layer for Ollama API operations. Mirrors DockerService pattern.

**File**: `management-ui/backend/app/services/ollama_service.py`

```python
import httpx
from typing import List, Dict, Optional, AsyncGenerator
from ..schemas.model import (
    ModelInfo, ModelDetails, ModelListResponse,
    PullProgress, PullStatus, VramEstimate, CatalogModel
)


# Static model catalog - popular models with metadata
MODEL_CATALOG: List[Dict] = [
    {
        "name": "llama3.2",
        "description": "Meta's latest Llama model, excellent for general tasks",
        "tags": ["1b", "3b", "latest"],
        "parameter_sizes": ["1B", "3B"],
        "recommended_tag": "3b",
        "category": "chat",
        "vram_requirements": {"1b": 1.5, "3b": 3.0}
    },
    {
        "name": "llama3.1",
        "description": "Powerful general-purpose model",
        "tags": ["8b", "70b", "405b", "latest"],
        "parameter_sizes": ["8B", "70B", "405B"],
        "recommended_tag": "8b",
        "category": "chat",
        "vram_requirements": {"8b": 5.0, "70b": 40.0, "405b": 200.0}
    },
    {
        "name": "mistral",
        "description": "Fast and efficient, great for quick responses",
        "tags": ["7b", "latest"],
        "parameter_sizes": ["7B"],
        "recommended_tag": "latest",
        "category": "chat",
        "vram_requirements": {"7b": 5.0, "latest": 5.0}
    },
    {
        "name": "codellama",
        "description": "Specialized for code generation and understanding",
        "tags": ["7b", "13b", "34b", "latest"],
        "parameter_sizes": ["7B", "13B", "34B"],
        "recommended_tag": "7b",
        "category": "code",
        "vram_requirements": {"7b": 5.0, "13b": 9.0, "34b": 20.0}
    },
    {
        "name": "deepseek-coder",
        "description": "Advanced coding model with strong performance",
        "tags": ["6.7b", "33b", "latest"],
        "parameter_sizes": ["6.7B", "33B"],
        "recommended_tag": "6.7b",
        "category": "code",
        "vram_requirements": {"6.7b": 5.0, "33b": 20.0}
    },
    {
        "name": "phi3",
        "description": "Microsoft's compact but capable model",
        "tags": ["mini", "medium", "latest"],
        "parameter_sizes": ["3.8B", "14B"],
        "recommended_tag": "mini",
        "category": "chat",
        "vram_requirements": {"mini": 3.0, "medium": 9.0}
    },
    {
        "name": "gemma2",
        "description": "Google's open model, efficient and capable",
        "tags": ["2b", "9b", "27b", "latest"],
        "parameter_sizes": ["2B", "9B", "27B"],
        "recommended_tag": "9b",
        "category": "chat",
        "vram_requirements": {"2b": 2.0, "9b": 6.0, "27b": 18.0}
    },
    {
        "name": "qwen2.5",
        "description": "Alibaba's latest model with multilingual support",
        "tags": ["0.5b", "1.5b", "3b", "7b", "14b", "32b", "72b", "latest"],
        "parameter_sizes": ["0.5B", "1.5B", "3B", "7B", "14B", "32B", "72B"],
        "recommended_tag": "7b",
        "category": "chat",
        "vram_requirements": {"0.5b": 0.5, "1.5b": 1.5, "3b": 3.0, "7b": 5.0, "14b": 10.0, "32b": 20.0, "72b": 45.0}
    },
    {
        "name": "llava",
        "description": "Vision-language model for image understanding",
        "tags": ["7b", "13b", "34b", "latest"],
        "parameter_sizes": ["7B", "13B", "34B"],
        "recommended_tag": "7b",
        "category": "vision",
        "vram_requirements": {"7b": 6.0, "13b": 10.0, "34b": 22.0}
    },
    {
        "name": "nomic-embed-text",
        "description": "Text embedding model for RAG applications",
        "tags": ["latest"],
        "parameter_sizes": ["137M"],
        "recommended_tag": "latest",
        "category": "embedding",
        "vram_requirements": {"latest": 0.5}
    },
]


class OllamaService:
    """Service layer for Ollama model operations."""

    def __init__(self, ollama_url: str = "http://ollama:11434"):
        self.ollama_url = ollama_url.rstrip("/")

    async def list_models(self) -> ModelListResponse:
        """List all installed models."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.ollama_url}/api/tags")
            response.raise_for_status()
            data = response.json()

        models = []
        total_size = 0
        for m in data.get("models", []):
            model_info = ModelInfo(
                name=m.get("name", "").split(":")[0],
                model=m.get("name", ""),
                size=m.get("size", 0),
                digest=m.get("digest", ""),
                modified_at=m.get("modified_at", ""),
                details=m.get("details")
            )
            models.append(model_info)
            total_size += m.get("size", 0)

        return ModelListResponse(
            models=models,
            total=len(models),
            total_size=total_size
        )

    async def get_model_details(self, model_name: str) -> Optional[ModelDetails]:
        """Get detailed information about a model."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.ollama_url}/api/show",
                    json={"name": model_name}
                )
                response.raise_for_status()
                data = response.json()

                return ModelDetails(
                    modelfile=data.get("modelfile"),
                    parameters=data.get("parameters"),
                    template=data.get("template"),
                    system=data.get("system"),
                    license=data.get("license"),
                    format=data.get("details", {}).get("format"),
                    family=data.get("details", {}).get("family"),
                    families=data.get("details", {}).get("families"),
                    parameter_size=data.get("details", {}).get("parameter_size"),
                    quantization_level=data.get("details", {}).get("quantization_level")
                )
            except httpx.HTTPStatusError:
                return None

    async def pull_model_stream(self, model_name: str) -> AsyncGenerator[PullProgress, None]:
        """Stream model download progress."""
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.ollama_url}/api/pull",
                json={"name": model_name, "stream": True}
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        import json
                        data = json.loads(line)
                        status_str = data.get("status", "")

                        # Map Ollama status to our enum
                        if "pulling" in status_str.lower():
                            status = PullStatus.DOWNLOADING
                        elif "verifying" in status_str.lower():
                            status = PullStatus.VERIFYING
                        elif "success" in status_str.lower():
                            status = PullStatus.COMPLETED
                        else:
                            status = PullStatus.DOWNLOADING

                        yield PullProgress(
                            status=status,
                            digest=data.get("digest"),
                            total=data.get("total", 0),
                            completed=data.get("completed", 0),
                            message=status_str
                        )
                    except Exception:
                        continue

    async def delete_model(self, model_name: str) -> bool:
        """Delete a model."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                "DELETE",
                f"{self.ollama_url}/api/delete",
                json={"name": model_name}
            )
            return response.status_code == 200

    def get_catalog(self, category: Optional[str] = None) -> List[CatalogModel]:
        """Get the model catalog for browsing."""
        models = []
        for m in MODEL_CATALOG:
            if category and m["category"] != category:
                continue
            models.append(CatalogModel(**m))
        return models

    def estimate_vram(self, model_name: str) -> Optional[VramEstimate]:
        """Estimate VRAM requirement for a model."""
        # Parse model name and tag
        parts = model_name.split(":")
        base_name = parts[0]
        tag = parts[1] if len(parts) > 1 else "latest"

        # Look up in catalog
        for m in MODEL_CATALOG:
            if m["name"] == base_name:
                vram = m["vram_requirements"].get(tag)
                if vram is None and tag == "latest":
                    # Use first available
                    vram = list(m["vram_requirements"].values())[0] if m["vram_requirements"] else None

                if vram:
                    # Recommend GPU based on VRAM
                    if vram <= 4:
                        gpu = "4GB+ VRAM (GTX 1650, etc.)"
                    elif vram <= 8:
                        gpu = "8GB+ VRAM (RTX 3060, RTX 4060)"
                    elif vram <= 12:
                        gpu = "12GB+ VRAM (RTX 3080, RTX 4070)"
                    elif vram <= 24:
                        gpu = "24GB+ VRAM (RTX 3090, RTX 4090)"
                    else:
                        gpu = "48GB+ VRAM (A6000, multi-GPU)"

                    return VramEstimate(
                        model=model_name,
                        parameter_size=m["parameter_sizes"][0] if m["parameter_sizes"] else "Unknown",
                        quantization="Q4 (default)",
                        estimated_vram_gb=vram,
                        recommended_gpu=gpu
                    )
        return None

    async def is_available(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
```

**Verify**: `python -c "from app.services.ollama_service import OllamaService; print('OK')"`

---

### Task 3: Update Services __init__.py

**Why**: Export the new OllamaService for use in routes.

**File**: `management-ui/backend/app/services/__init__.py`

```python
from .docker_service import DockerService
from .ollama_service import OllamaService

__all__ = ["DockerService", "OllamaService"]
```

**Verify**: `python -c "from app.services import OllamaService; print('OK')"`

---

### Task 4: Create Models API Routes

**Why**: REST endpoints for model operations. Follows existing route pattern.

**File**: `management-ui/backend/app/api/routes/models.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from ...schemas.model import (
    ModelListResponse, ModelDetails, PullRequest, PullResponse,
    DeleteResponse, VramEstimate, CatalogModel
)
from ...services.ollama_service import OllamaService
from ..deps import get_current_user
from ...config import settings

router = APIRouter()


def get_ollama_service() -> OllamaService:
    """Get OllamaService instance with configured URL."""
    # Use internal Docker network URL
    ollama_url = settings.OLLAMA_URL if hasattr(settings, 'OLLAMA_URL') else "http://ollama:11434"
    return OllamaService(ollama_url)


@router.get("", response_model=ModelListResponse)
async def list_models(
    ollama_service: OllamaService = Depends(get_ollama_service),
    _: dict = Depends(get_current_user)
):
    """List all installed models."""
    try:
        return await ollama_service.list_models()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to Ollama: {str(e)}"
        )


@router.get("/catalog", response_model=List[CatalogModel])
async def get_catalog(
    category: Optional[str] = None,
    ollama_service: OllamaService = Depends(get_ollama_service),
    _: dict = Depends(get_current_user)
):
    """Get the model catalog for browsing."""
    return ollama_service.get_catalog(category)


@router.get("/status")
async def get_ollama_status(
    ollama_service: OllamaService = Depends(get_ollama_service),
    _: dict = Depends(get_current_user)
):
    """Check if Ollama is available."""
    available = await ollama_service.is_available()
    return {"available": available}


@router.get("/{model_name:path}/details", response_model=Optional[ModelDetails])
async def get_model_details(
    model_name: str,
    ollama_service: OllamaService = Depends(get_ollama_service),
    _: dict = Depends(get_current_user)
):
    """Get detailed information about a model."""
    details = await ollama_service.get_model_details(model_name)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found"
        )
    return details


@router.get("/{model_name:path}/vram", response_model=Optional[VramEstimate])
async def get_vram_estimate(
    model_name: str,
    ollama_service: OllamaService = Depends(get_ollama_service),
    _: dict = Depends(get_current_user)
):
    """Get VRAM requirement estimate for a model."""
    estimate = ollama_service.estimate_vram(model_name)
    if not estimate:
        return None
    return estimate


@router.post("/pull", response_model=PullResponse)
async def initiate_pull(
    request: PullRequest,
    ollama_service: OllamaService = Depends(get_ollama_service),
    _: dict = Depends(get_current_user)
):
    """Initiate a model pull (actual progress via WebSocket)."""
    # Just verify Ollama is available
    available = await ollama_service.is_available()
    if not available:
        return PullResponse(
            success=False,
            message="Ollama is not available",
            model=request.model
        )
    return PullResponse(
        success=True,
        message=f"Pull initiated for {request.model}. Connect to WebSocket for progress.",
        model=request.model
    )


@router.delete("/{model_name:path}", response_model=DeleteResponse)
async def delete_model(
    model_name: str,
    ollama_service: OllamaService = Depends(get_ollama_service),
    _: dict = Depends(get_current_user)
):
    """Delete a model."""
    try:
        success = await ollama_service.delete_model(model_name)
        if success:
            return DeleteResponse(
                success=True,
                message=f"Model '{model_name}' deleted successfully",
                model=model_name
            )
        else:
            return DeleteResponse(
                success=False,
                message=f"Failed to delete model '{model_name}'",
                model=model_name
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

**Verify**: `python -c "from app.api.routes.models import router; print('OK')"`

---

### Task 5: Update Routes __init__.py

**Why**: Register the models router with the API.

**File**: `management-ui/backend/app/api/routes/__init__.py`

Add import and registration:

```python
from fastapi import APIRouter
from .auth import router as auth_router
from .services import router as services_router
from .config import router as config_router
from .logs import router as logs_router
from .setup import router as setup_router
from .models import router as models_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(services_router, prefix="/services", tags=["services"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(logs_router, prefix="/logs", tags=["logs"])
api_router.include_router(setup_router, prefix="/setup", tags=["setup"])
api_router.include_router(models_router, prefix="/models", tags=["models"])
```

**Verify**: Start backend and check `/api/models` endpoint is registered

---

### Task 6: Add WebSocket Handler for Model Pull

**Why**: Real-time progress updates during model download. Mirrors log streaming pattern.

**File**: `management-ui/backend/app/api/websocket.py`

Add new function after existing handlers:

```python
async def stream_model_pull(
    websocket: WebSocket,
    model_name: str
):
    """Stream model pull progress."""
    from ..services.ollama_service import OllamaService

    ollama_service = OllamaService()

    try:
        # Check if Ollama is available
        if not await ollama_service.is_available():
            await websocket.send_json({
                "type": "error",
                "message": "Ollama is not available"
            })
            return

        # Stream pull progress
        async for progress in ollama_service.pull_model_stream(model_name):
            await websocket.send_json({
                "type": "progress",
                "model": model_name,
                "status": progress.status.value,
                "digest": progress.digest,
                "total": progress.total,
                "completed": progress.completed,
                "message": progress.message,
                "percentage": round((progress.completed / progress.total * 100), 1) if progress.total > 0 else 0
            })

        # Send completion
        await websocket.send_json({
            "type": "complete",
            "model": model_name,
            "message": f"Model {model_name} pulled successfully"
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
```

**Also update** `management-ui/backend/app/api/routes/logs.py` to add the WebSocket endpoint (or create a new ws routes file):

Add to logs.py or create separate ws.py:

```python
@router.websocket("/ws/models/pull/{model_name}")
async def websocket_model_pull(
    websocket: WebSocket,
    model_name: str,
    token: str = None
):
    """WebSocket endpoint for streaming model pull progress."""
    from ..websocket import verify_ws_token, stream_model_pull

    if not token or not verify_ws_token(token):
        await websocket.close(code=4001)
        return

    await websocket.accept()
    await stream_model_pull(websocket, model_name)
```

**Verify**: WebSocket endpoint should be accessible at `/api/logs/ws/models/pull/{model_name}`

---

### Task 7: Create Frontend Types

**Why**: TypeScript type definitions for model data.

**File**: `management-ui/frontend/src/types/model.ts`

```typescript
export interface ModelInfo {
  name: string;
  model: string;
  size: number;
  digest: string;
  modified_at: string;
  details?: Record<string, unknown>;
}

export interface ModelDetails {
  modelfile?: string;
  parameters?: string;
  template?: string;
  system?: string;
  license?: string;
  format?: string;
  family?: string;
  families?: string[];
  parameter_size?: string;
  quantization_level?: string;
}

export interface ModelListResponse {
  models: ModelInfo[];
  total: number;
  total_size: number;
}

export type PullStatus = 'pending' | 'downloading' | 'verifying' | 'completed' | 'failed';

export interface PullProgress {
  status: PullStatus;
  digest?: string;
  total: number;
  completed: number;
  message?: string;
  percentage?: number;
}

export interface CatalogModel {
  name: string;
  description: string;
  tags: string[];
  parameter_sizes: string[];
  recommended_tag: string;
  category: string;
  vram_requirements: Record<string, number>;
}

export interface VramEstimate {
  model: string;
  parameter_size: string;
  quantization: string;
  estimated_vram_gb: number;
  recommended_gpu: string;
}

export interface DeleteResponse {
  success: boolean;
  message: string;
  model: string;
}
```

**Verify**: TypeScript compilation passes

---

### Task 8: Create Models API Client

**Why**: Frontend API calls for model operations. Mirrors services.ts pattern.

**File**: `management-ui/frontend/src/api/models.ts`

```typescript
import { apiClient } from './client';
import type {
  ModelListResponse,
  ModelDetails,
  CatalogModel,
  VramEstimate,
  DeleteResponse,
} from '../types/model';

export const modelsApi = {
  async list(): Promise<ModelListResponse> {
    const response = await apiClient.get<ModelListResponse>('/models');
    return response.data;
  },

  async getCatalog(category?: string): Promise<CatalogModel[]> {
    const params = category ? { category } : {};
    const response = await apiClient.get<CatalogModel[]>('/models/catalog', { params });
    return response.data;
  },

  async getStatus(): Promise<{ available: boolean }> {
    const response = await apiClient.get<{ available: boolean }>('/models/status');
    return response.data;
  },

  async getDetails(modelName: string): Promise<ModelDetails> {
    const response = await apiClient.get<ModelDetails>(
      `/models/${encodeURIComponent(modelName)}/details`
    );
    return response.data;
  },

  async getVramEstimate(modelName: string): Promise<VramEstimate | null> {
    const response = await apiClient.get<VramEstimate | null>(
      `/models/${encodeURIComponent(modelName)}/vram`
    );
    return response.data;
  },

  async deleteModel(modelName: string): Promise<DeleteResponse> {
    const response = await apiClient.delete<DeleteResponse>(
      `/models/${encodeURIComponent(modelName)}`
    );
    return response.data;
  },
};
```

**Verify**: TypeScript compilation passes

---

### Task 9: Update WebSocket Client for Model Pulls

**Why**: WebSocket factory for model pull progress streaming.

**File**: `management-ui/frontend/src/api/websocket.ts`

Add after existing exports:

```typescript
export interface ModelPullMessage {
  type: 'progress' | 'complete' | 'error';
  model?: string;
  status?: string;
  digest?: string;
  total?: number;
  completed?: number;
  message?: string;
  percentage?: number;
}

export function createModelPullWebSocket(
  modelName: string,
  onMessage: (msg: ModelPullMessage) => void,
  onError?: (error: Event) => void,
  onClose?: () => void
): WebSocket | null {
  const token = getAuthToken();
  if (!token) return null;

  const baseUrl = getWsBaseUrl();
  const url = `${baseUrl}/api/logs/ws/models/pull/${encodeURIComponent(modelName)}?token=${token}`;

  console.debug('Model pull WebSocket connecting to:', url);
  const ws = new WebSocket(url);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch {
      console.error('Failed to parse model pull message');
    }
  };

  ws.onerror = (error) => {
    console.error('Model pull WebSocket error:', error);
    onError?.(error);
  };

  ws.onclose = () => {
    onClose?.();
  };

  return ws;
}
```

**Verify**: TypeScript compilation passes

---

### Task 10: Create Model Pull Hook

**Why**: Encapsulate WebSocket connection logic for model downloads.

**File**: `management-ui/frontend/src/hooks/useModelPull.ts`

```typescript
import { useEffect, useRef, useState, useCallback } from 'react';
import { createModelPullWebSocket, type ModelPullMessage } from '../api/websocket';
import type { PullStatus } from '../types/model';

interface UseModelPullOptions {
  onComplete?: (modelName: string) => void;
  onError?: (error: string) => void;
}

interface ModelPullState {
  isConnected: boolean;
  isPulling: boolean;
  modelName: string | null;
  status: PullStatus | null;
  progress: number;
  message: string | null;
  error: string | null;
}

const initialState: ModelPullState = {
  isConnected: false,
  isPulling: false,
  modelName: null,
  status: null,
  progress: 0,
  message: null,
  error: null,
};

export function useModelPull(options: UseModelPullOptions = {}) {
  const [state, setState] = useState<ModelPullState>(initialState);
  const wsRef = useRef<WebSocket | null>(null);
  const { onComplete, onError } = options;

  const startPull = useCallback((modelName: string) => {
    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setState({
      ...initialState,
      isPulling: true,
      modelName,
      status: 'pending',
      message: `Initiating download of ${modelName}...`,
    });

    const ws = createModelPullWebSocket(
      modelName,
      (msg: ModelPullMessage) => {
        if (msg.type === 'progress') {
          setState((prev) => ({
            ...prev,
            status: msg.status as PullStatus,
            progress: msg.percentage || 0,
            message: msg.message || null,
          }));
        } else if (msg.type === 'complete') {
          setState((prev) => ({
            ...prev,
            isPulling: false,
            status: 'completed',
            progress: 100,
            message: msg.message || 'Download complete',
          }));
          onComplete?.(modelName);
        } else if (msg.type === 'error') {
          setState((prev) => ({
            ...prev,
            isPulling: false,
            status: 'failed',
            error: msg.message || 'Unknown error',
          }));
          onError?.(msg.message || 'Unknown error');
        }
      },
      () => {
        setState((prev) => ({
          ...prev,
          isPulling: false,
          isConnected: false,
          error: 'Connection error',
        }));
        onError?.('Connection error');
      },
      () => {
        setState((prev) => ({ ...prev, isConnected: false }));
      }
    );

    if (ws) {
      wsRef.current = ws;
      ws.onopen = () => setState((prev) => ({ ...prev, isConnected: true }));
    } else {
      setState((prev) => ({
        ...prev,
        isPulling: false,
        error: 'Not authenticated',
      }));
    }
  }, [onComplete, onError]);

  const cancelPull = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setState(initialState);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    ...state,
    startPull,
    cancelPull,
  };
}
```

**Verify**: TypeScript compilation passes

---

### Task 11: Create Models Store

**Why**: Zustand store for models state management. Mirrors servicesStore pattern.

**File**: `management-ui/frontend/src/store/modelsStore.ts`

```typescript
import { create } from 'zustand';
import { modelsApi } from '../api/models';
import type { ModelInfo, CatalogModel, VramEstimate } from '../types/model';

interface ModelsState {
  // Installed models
  models: ModelInfo[];
  totalSize: number;

  // Catalog
  catalog: CatalogModel[];
  catalogCategory: string | null;

  // UI State
  isLoading: boolean;
  error: string | null;
  ollamaAvailable: boolean;
  actionInProgress: string | null;

  // Selected model details
  selectedModel: string | null;
  selectedVram: VramEstimate | null;

  // Actions
  fetchModels: () => Promise<void>;
  fetchCatalog: (category?: string) => Promise<void>;
  checkOllamaStatus: () => Promise<boolean>;
  deleteModel: (modelName: string) => Promise<boolean>;
  getVramEstimate: (modelName: string) => Promise<void>;
  setSelectedModel: (modelName: string | null) => void;
  clearError: () => void;
}

export const useModelsStore = create<ModelsState>((set, get) => ({
  models: [],
  totalSize: 0,
  catalog: [],
  catalogCategory: null,
  isLoading: false,
  error: null,
  ollamaAvailable: false,
  actionInProgress: null,
  selectedModel: null,
  selectedVram: null,

  fetchModels: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await modelsApi.list();
      set({
        models: response.models,
        totalSize: response.total_size,
        isLoading: false,
        ollamaAvailable: true,
      });
    } catch (error: unknown) {
      const err = error as { response?: { status?: number; data?: { detail?: string } } };
      if (err.response?.status === 503) {
        set({
          error: 'Ollama is not available. Make sure the Ollama service is running.',
          isLoading: false,
          ollamaAvailable: false,
        });
      } else {
        set({
          error: err.response?.data?.detail || 'Failed to fetch models',
          isLoading: false,
        });
      }
    }
  },

  fetchCatalog: async (category?: string) => {
    try {
      const catalog = await modelsApi.getCatalog(category);
      set({ catalog, catalogCategory: category || null });
    } catch (error: unknown) {
      console.error('Failed to fetch catalog:', error);
    }
  },

  checkOllamaStatus: async () => {
    try {
      const status = await modelsApi.getStatus();
      set({ ollamaAvailable: status.available });
      return status.available;
    } catch {
      set({ ollamaAvailable: false });
      return false;
    }
  },

  deleteModel: async (modelName: string) => {
    set({ actionInProgress: modelName, error: null });
    try {
      const response = await modelsApi.deleteModel(modelName);
      if (response.success) {
        await get().fetchModels();
        set({ actionInProgress: null });
        return true;
      } else {
        set({
          error: response.message,
          actionInProgress: null,
        });
        return false;
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      set({
        error: err.response?.data?.detail || `Failed to delete ${modelName}`,
        actionInProgress: null,
      });
      return false;
    }
  },

  getVramEstimate: async (modelName: string) => {
    try {
      const estimate = await modelsApi.getVramEstimate(modelName);
      set({ selectedVram: estimate });
    } catch {
      set({ selectedVram: null });
    }
  },

  setSelectedModel: (modelName: string | null) => {
    set({ selectedModel: modelName, selectedVram: null });
    if (modelName) {
      get().getVramEstimate(modelName);
    }
  },

  clearError: () => set({ error: null }),
}));
```

**Verify**: TypeScript compilation passes

---

### Task 12: Create Model Card Component

**Why**: Reusable component for displaying installed model information.

**File**: `management-ui/frontend/src/components/models/ModelCard.tsx`

```typescript
import { Trash2, HardDrive, Clock, Info } from 'lucide-react';
import { Card } from '../common/Card';
import type { ModelInfo } from '../../types/model';

interface ModelCardProps {
  model: ModelInfo;
  isDeleting: boolean;
  onDelete: () => void;
  onShowDetails: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function ModelCard({ model, isDeleting, onDelete, onShowDetails }: ModelCardProps) {
  return (
    <Card className="hover:border-blue-500/50 transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-white truncate">{model.model}</h3>
          <p className="text-xs text-slate-500 truncate mt-0.5">{model.digest.substring(0, 12)}...</p>
        </div>
        <div className="flex items-center gap-2 ml-2">
          <button
            onClick={onShowDetails}
            className="p-1.5 rounded hover:bg-[#374151] transition-colors"
            title="View details"
          >
            <Info className="w-4 h-4 text-slate-400 hover:text-blue-400" />
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className="p-1.5 rounded hover:bg-red-500/20 transition-colors disabled:opacity-50"
            title="Delete model"
          >
            <Trash2 className={`w-4 h-4 ${isDeleting ? 'text-slate-500' : 'text-slate-400 hover:text-red-400'}`} />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs text-slate-400">
        <div className="flex items-center gap-1">
          <HardDrive className="w-3 h-3" />
          <span>{formatBytes(model.size)}</span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          <span>{formatDate(model.modified_at)}</span>
        </div>
      </div>
    </Card>
  );
}
```

**Verify**: TypeScript compilation passes

---

### Task 13: Create Catalog Component

**Why**: Browsable model catalog for discovering and downloading new models.

**File**: `management-ui/frontend/src/components/models/ModelCatalog.tsx`

```typescript
import { useState } from 'react';
import { Download, Cpu, Code, Eye, Database, ChevronDown } from 'lucide-react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import type { CatalogModel } from '../../types/model';

interface ModelCatalogProps {
  models: CatalogModel[];
  installedModels: string[];
  isPulling: boolean;
  pullingModel: string | null;
  onPull: (modelName: string) => void;
  onCategoryChange: (category: string | null) => void;
  selectedCategory: string | null;
}

const categories = [
  { id: null, name: 'All', icon: Database },
  { id: 'chat', name: 'Chat', icon: Cpu },
  { id: 'code', name: 'Code', icon: Code },
  { id: 'vision', name: 'Vision', icon: Eye },
  { id: 'embedding', name: 'Embedding', icon: Database },
];

function getCategoryIcon(category: string) {
  switch (category) {
    case 'chat': return Cpu;
    case 'code': return Code;
    case 'vision': return Eye;
    case 'embedding': return Database;
    default: return Cpu;
  }
}

export function ModelCatalog({
  models,
  installedModels,
  isPulling,
  pullingModel,
  onPull,
  onCategoryChange,
  selectedCategory,
}: ModelCatalogProps) {
  const [expandedModel, setExpandedModel] = useState<string | null>(null);

  const isInstalled = (modelName: string, tag: string) => {
    const fullName = `${modelName}:${tag}`;
    return installedModels.some((m) => m === fullName || (tag === 'latest' && m === modelName));
  };

  return (
    <div className="space-y-4">
      {/* Category filters */}
      <div className="flex items-center gap-2 flex-wrap">
        {categories.map((cat) => {
          const Icon = cat.icon;
          const isActive = selectedCategory === cat.id;
          return (
            <button
              key={cat.id || 'all'}
              onClick={() => onCategoryChange(cat.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors
                ${isActive
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50'
                  : 'bg-[#2d3748] text-slate-400 border border-transparent hover:border-[#4b5563]'
                }`}
            >
              <Icon className="w-4 h-4" />
              {cat.name}
            </button>
          );
        })}
      </div>

      {/* Model list */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {models.map((model) => {
          const Icon = getCategoryIcon(model.category);
          const isExpanded = expandedModel === model.name;

          return (
            <Card key={model.name} className="overflow-hidden">
              <div
                className="flex items-start justify-between cursor-pointer"
                onClick={() => setExpandedModel(isExpanded ? null : model.name)}
              >
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="p-2 bg-[#374151] rounded-lg mt-0.5">
                    <Icon className="w-5 h-5 text-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-white">{model.name}</h4>
                    <p className="text-sm text-slate-400 mt-0.5 line-clamp-2">{model.description}</p>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      {model.parameter_sizes.slice(0, 3).map((size) => (
                        <span
                          key={size}
                          className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-300 rounded"
                        >
                          {size}
                        </span>
                      ))}
                      {model.parameter_sizes.length > 3 && (
                        <span className="text-xs text-slate-500">
                          +{model.parameter_sizes.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <ChevronDown
                  className={`w-5 h-5 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                />
              </div>

              {/* Expanded content */}
              {isExpanded && (
                <div className="mt-4 pt-4 border-t border-[#374151]">
                  <div className="space-y-2">
                    {model.tags.map((tag) => {
                      const fullName = `${model.name}:${tag}`;
                      const installed = isInstalled(model.name, tag);
                      const vram = model.vram_requirements[tag];
                      const isRecommended = tag === model.recommended_tag;
                      const isPullingThis = pullingModel === fullName;

                      return (
                        <div
                          key={tag}
                          className="flex items-center justify-between py-2 px-3 bg-[#2d3748] rounded-lg"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-white font-mono">{fullName}</span>
                            {isRecommended && (
                              <span className="px-1.5 py-0.5 text-xs bg-green-500/20 text-green-400 rounded">
                                Recommended
                              </span>
                            )}
                            {installed && (
                              <span className="px-1.5 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded">
                                Installed
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3">
                            {vram && (
                              <span className="text-xs text-slate-500">{vram} GB VRAM</span>
                            )}
                            {!installed && (
                              <Button
                                size="sm"
                                variant="primary"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onPull(fullName);
                                }}
                                disabled={isPulling}
                              >
                                <Download className="w-3 h-3 mr-1" />
                                {isPullingThis ? 'Pulling...' : 'Pull'}
                              </Button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {models.length === 0 && (
        <div className="text-center py-8 text-slate-400">
          No models found in this category
        </div>
      )}
    </div>
  );
}
```

**Verify**: TypeScript compilation passes

---

### Task 14: Create Pull Progress Component

**Why**: Display real-time download progress with progress bar.

**File**: `management-ui/frontend/src/components/models/PullProgress.tsx`

```typescript
import { Download, X, CheckCircle, AlertCircle } from 'lucide-react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import type { PullStatus } from '../../types/model';

interface PullProgressProps {
  modelName: string;
  status: PullStatus;
  progress: number;
  message: string | null;
  error: string | null;
  onCancel: () => void;
}

export function PullProgress({
  modelName,
  status,
  progress,
  message,
  error,
  onCancel,
}: PullProgressProps) {
  const isComplete = status === 'completed';
  const isFailed = status === 'failed';
  const isActive = !isComplete && !isFailed;

  return (
    <Card className={`${isFailed ? 'border-red-500/50' : isComplete ? 'border-green-500/50' : 'border-blue-500/50'}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          {isComplete ? (
            <div className="p-2 bg-green-500/20 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-400" />
            </div>
          ) : isFailed ? (
            <div className="p-2 bg-red-500/20 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-400" />
            </div>
          ) : (
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <Download className="w-5 h-5 text-blue-400 animate-pulse" />
            </div>
          )}
          <div>
            <h4 className="font-medium text-white">{modelName}</h4>
            <p className="text-sm text-slate-400">
              {isComplete ? 'Download complete' : isFailed ? 'Download failed' : message || 'Downloading...'}
            </p>
          </div>
        </div>
        {isActive && (
          <Button variant="ghost" size="sm" onClick={onCancel}>
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>

      {/* Progress bar */}
      {!isComplete && !isFailed && (
        <div className="space-y-2">
          <div className="h-2 bg-[#374151] rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-slate-500">
            <span>{status === 'verifying' ? 'Verifying...' : 'Downloading...'}</span>
            <span>{progress.toFixed(1)}%</span>
          </div>
        </div>
      )}

      {/* Error message */}
      {isFailed && error && (
        <div className="mt-2 p-2 bg-red-500/10 rounded text-sm text-red-400">
          {error}
        </div>
      )}
    </Card>
  );
}
```

**Verify**: TypeScript compilation passes

---

### Task 15: Create Components Index

**Why**: Export all model components from single entry point.

**File**: `management-ui/frontend/src/components/models/index.ts`

```typescript
export { ModelCard } from './ModelCard';
export { ModelCatalog } from './ModelCatalog';
export { PullProgress } from './PullProgress';
```

**Verify**: TypeScript compilation passes

---

### Task 16: Create Models Page

**Why**: Main page component that ties everything together.

**File**: `management-ui/frontend/src/pages/Models.tsx`

```typescript
import { useEffect, useState } from 'react';
import { RefreshCw, AlertCircle, Box, HardDrive, Cpu } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { ModelCard, ModelCatalog, PullProgress } from '../components/models';
import { useModelsStore } from '../store/modelsStore';
import { useModelPull } from '../hooks/useModelPull';
import { ConfirmDeleteDialog } from '../components/common/ConfirmDeleteDialog';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export const Models: React.FC = () => {
  const {
    models,
    totalSize,
    catalog,
    catalogCategory,
    isLoading,
    error,
    ollamaAvailable,
    actionInProgress,
    fetchModels,
    fetchCatalog,
    checkOllamaStatus,
    deleteModel,
    clearError,
  } = useModelsStore();

  const [activeTab, setActiveTab] = useState<'installed' | 'catalog'>('installed');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const modelPull = useModelPull({
    onComplete: () => {
      fetchModels();
    },
    onError: (err) => {
      console.error('Pull failed:', err);
    },
  });

  useEffect(() => {
    checkOllamaStatus();
    fetchModels();
    fetchCatalog();

    // Poll for updates
    const interval = setInterval(() => {
      fetchModels();
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchModels, fetchCatalog, checkOllamaStatus]);

  const handleDelete = async (modelName: string) => {
    const success = await deleteModel(modelName);
    if (success) {
      setDeleteConfirm(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">AI Models</h2>
          <p className="text-slate-400 mt-1">
            Manage Ollama models for local AI inference
          </p>
        </div>
        <button
          onClick={() => {
            fetchModels();
            fetchCatalog();
          }}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 text-sm text-slate-400
                     hover:text-white hover:bg-[#1e293b] rounded-lg transition-colors
                     border border-[#374151] hover:border-[#4b5563]"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Ollama status warning */}
      {!ollamaAvailable && (
        <div className="flex items-center gap-3 p-4 bg-amber-900/20 border border-amber-700/30 rounded-lg">
          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-amber-400 font-medium">Ollama Not Available</p>
            <p className="text-amber-400/70 text-sm mt-1">
              Make sure the Ollama service is running. Go to Services to start it.
            </p>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-900/20 border border-red-700/30 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <p className="text-red-400 flex-1">{error}</p>
          <Button variant="ghost" size="sm" onClick={clearError} className="text-red-400">
            Dismiss
          </Button>
        </div>
      )}

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card variant="blue">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Box className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Installed Models</p>
              <p className="text-2xl font-bold text-white">{models.length}</p>
            </div>
          </div>
        </Card>

        <Card variant="green">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-500/20 rounded-lg">
              <HardDrive className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Storage Used</p>
              <p className="text-2xl font-bold text-white">{formatBytes(totalSize)}</p>
            </div>
          </div>
        </Card>

        <Card variant="purple">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <Cpu className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <p className="text-sm text-slate-400">Catalog Models</p>
              <p className="text-2xl font-bold text-white">{catalog.length}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Active pull progress */}
      {modelPull.isPulling && modelPull.modelName && (
        <PullProgress
          modelName={modelPull.modelName}
          status={modelPull.status!}
          progress={modelPull.progress}
          message={modelPull.message}
          error={modelPull.error}
          onCancel={modelPull.cancelPull}
        />
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-[#374151]">
        <button
          onClick={() => setActiveTab('installed')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
            activeTab === 'installed'
              ? 'text-blue-400 border-blue-400'
              : 'text-slate-400 border-transparent hover:text-white'
          }`}
        >
          Installed ({models.length})
        </button>
        <button
          onClick={() => setActiveTab('catalog')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
            activeTab === 'catalog'
              ? 'text-blue-400 border-blue-400'
              : 'text-slate-400 border-transparent hover:text-white'
          }`}
        >
          Model Catalog
        </button>
      </div>

      {/* Content */}
      {activeTab === 'installed' ? (
        <div className="space-y-4">
          {models.length === 0 ? (
            <Card>
              <div className="text-center py-8">
                <Box className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400 mb-4">No models installed yet</p>
                <Button variant="primary" onClick={() => setActiveTab('catalog')}>
                  Browse Model Catalog
                </Button>
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {models.map((model) => (
                <ModelCard
                  key={model.model}
                  model={model}
                  isDeleting={actionInProgress === model.model}
                  onDelete={() => setDeleteConfirm(model.model)}
                  onShowDetails={() => {
                    // TODO: Show details modal
                    console.log('Show details for', model.model);
                  }}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        <ModelCatalog
          models={catalog}
          installedModels={models.map((m) => m.model)}
          isPulling={modelPull.isPulling}
          pullingModel={modelPull.modelName}
          onPull={modelPull.startPull}
          onCategoryChange={(category) => fetchCatalog(category || undefined)}
          selectedCategory={catalogCategory}
        />
      )}

      {/* Delete confirmation */}
      {deleteConfirm && (
        <ConfirmDeleteDialog
          title="Delete Model"
          message={`Are you sure you want to delete "${deleteConfirm}"? This action cannot be undone.`}
          isOpen={!!deleteConfirm}
          onConfirm={() => handleDelete(deleteConfirm)}
          onCancel={() => setDeleteConfirm(null)}
        />
      )}
    </div>
  );
};
```

**Verify**: TypeScript compilation passes

---

### Task 17: Update App.tsx with Models Route

**Why**: Add the /models route to the application router.

**File**: `management-ui/frontend/src/App.tsx`

Add import at top:
```typescript
import { Models } from './pages/Models';
```

Add route inside MainLayout routes (after existing routes):
```typescript
<Route path="/models" element={<Models />} />
```

**Verify**: Navigate to /models in browser

---

### Task 18: Update Sidebar with Models Link

**Why**: Add navigation link to the new Models page.

**File**: `management-ui/frontend/src/components/layout/Sidebar.tsx`

Add import:
```typescript
import { Box } from 'lucide-react';  // or use existing import if already there
```

Add navigation item (after Services, before Dependencies):
```typescript
{
  to: '/models',
  icon: Box,  // or Cpu, or another appropriate icon
  label: 'AI Models',
},
```

**Verify**: Models link appears in sidebar and navigates correctly

---

### Task 19: Add httpx Dependency

**Why**: OllamaService uses httpx for async HTTP requests.

Add to `management-ui/backend/requirements.txt`:
```
httpx>=0.25.0
```

**Verify**: `pip install -r requirements.txt` succeeds

---

## Validation Strategy

### Automated Checks
- [ ] `cd management-ui/backend && python -c "from app.schemas.model import *; print('OK')"` - Schemas load
- [ ] `cd management-ui/backend && python -c "from app.services.ollama_service import OllamaService; print('OK')"` - Service loads
- [ ] `cd management-ui/backend && python -c "from app.api.routes.models import router; print('OK')"` - Routes load
- [ ] `cd management-ui/frontend && npm run build` - Frontend builds without errors
- [ ] `cd management-ui/frontend && npm run lint` - No lint errors

### Manual Validation

#### Backend API Tests
```bash
# Start backend (Ollama must be running)
cd management-ui/backend && python -m uvicorn app.main:app --reload

# Get auth token first (login)
TOKEN="your-jwt-token"

# List installed models
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/models

# Get catalog
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/models/catalog

# Check Ollama status
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/models/status

# Get model details
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/models/llama3.2:latest/details

# Get VRAM estimate
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/models/llama3.2:3b/vram

# Delete a model (careful!)
curl -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/models/test-model:latest
```

#### WebSocket Test
```javascript
// In browser console while authenticated
const ws = new WebSocket(`ws://localhost:8001/api/logs/ws/models/pull/phi3:mini?token=${localStorage.getItem('token')}`);
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.onclose = () => console.log('closed');
```

#### Frontend Tests
1. Navigate to /models page
2. Verify stats cards show (even if 0 models)
3. Switch between Installed and Catalog tabs
4. Filter catalog by category
5. Expand a catalog model to see tags
6. Click Pull on a model - verify progress bar appears
7. Wait for download completion - verify model appears in Installed tab
8. Click delete on a model - verify confirmation dialog
9. Confirm delete - verify model removed

### Edge Cases to Test
- [ ] Ollama not running - error message shown, no crash
- [ ] Empty model list - "No models" message shown
- [ ] Very large model (70B) - VRAM estimate shows correct warning
- [ ] Pull cancelled mid-download - UI recovers gracefully
- [ ] Network disconnect during pull - error shown
- [ ] Delete model that doesn't exist - error handled
- [ ] Multiple rapid refreshes - no race conditions

### Regression Check
- [ ] Services page still works
- [ ] Dashboard still works
- [ ] Log streaming still works
- [ ] Setup wizard still works
- [ ] All existing WebSocket connections unaffected

---

## Risks

1. **Ollama API changes**: The Ollama API is documented but could change. Mitigation: Follow documented endpoints, add version check.

2. **VRAM estimates are approximate**: Different quantizations and context lengths affect actual VRAM usage. Mitigation: Use conservative estimates, add disclaimer.

3. **Model catalog becomes stale**: Static list of models. Mitigation: Easy to update, could fetch from Ollama library in Phase 2.

4. **Large downloads may timeout**: Big models take a long time. Mitigation: httpx timeout=None for streaming, WebSocket keeps connection alive.

5. **Concurrent pull operations**: Ollama handles this, but UI might get confused. Mitigation: Disable pull button while any pull in progress.

---

## Plan File Info

**Created**: 2025-12-27
**Type**: Implementation Plan
**Status**: Ready for implementation
**Estimated Tasks**: 19
**Key Dependencies**: httpx, Ollama service running

To implement: `/implement .agents/plans/10-model-management.plan.md`
