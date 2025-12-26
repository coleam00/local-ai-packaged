# Stage 09: Setup Wizard

## Summary
Add a guided setup wizard for first-time configuration. Users can select profile, environment, services, generate secrets, and start the stack with one flow.

## Prerequisites
- Stage 01-08 completed

## Deliverable
- Multi-step setup wizard
- Profile selection (CPU/GPU)
- Environment selection (private/public)
- Service selection with dependencies
- Secret generation
- Stack startup orchestration

---

## Files to Create/Modify

### Backend
```
management-ui/backend/app/
├── schemas/
│   └── setup.py                 # NEW
├── services/
│   └── setup_service.py         # NEW
└── api/routes/
    └── setup.py                 # NEW
```

### Frontend
```
management-ui/frontend/src/
├── components/
│   └── setup/
│       ├── SetupWizard.tsx      # NEW
│       ├── ProfileStep.tsx      # NEW
│       ├── EnvironmentStep.tsx  # NEW
│       ├── ServicesStep.tsx     # NEW
│       ├── SecretsStep.tsx      # NEW
│       └── ConfirmStep.tsx      # NEW
└── pages/
    └── SetupWizard.tsx          # NEW
```

---

## Task 1: Create Setup Schemas (Backend)

**File**: `management-ui/backend/app/schemas/setup.py`

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum

class Profile(str, Enum):
    CPU = "cpu"
    GPU_NVIDIA = "gpu-nvidia"
    GPU_AMD = "gpu-amd"
    NONE = "none"

class Environment(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"

class SetupStatusResponse(BaseModel):
    setup_required: bool
    has_env_file: bool
    has_secrets: bool
    supabase_cloned: bool
    services_running: int
    missing_secrets: List[str]

class SetupConfigRequest(BaseModel):
    profile: Profile = Profile.CPU
    environment: Environment = Environment.PRIVATE
    enabled_services: List[str] = []
    secrets: Dict[str, str] = {}
    hostnames: Dict[str, str] = {}  # For public environment

class SetupStepResult(BaseModel):
    step: str
    status: str  # started, completed, failed
    message: Optional[str] = None
    error: Optional[str] = None

class SetupProgressResponse(BaseModel):
    status: str  # in_progress, completed, failed
    current_step: str
    steps: List[SetupStepResult]
    message: Optional[str] = None
    error: Optional[str] = None

class ServiceSelectionInfo(BaseModel):
    name: str
    group: str
    description: str
    required: bool
    dependencies: List[str]
    profiles: List[str]
    default_enabled: bool
```

---

## Task 2: Create Setup Service (Backend)

**File**: `management-ui/backend/app/services/setup_service.py`

```python
import os
import subprocess
import shutil
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from ..core.docker_client import DockerClient
from ..core.env_manager import EnvManager
from ..core.secret_generator import generate_all_secrets, generate_missing_secrets
from ..core.compose_parser import ComposeParser
from ..core.dependency_graph import DependencyGraph
from ..schemas.setup import (
    SetupStatusResponse, SetupConfigRequest, SetupProgressResponse,
    SetupStepResult, ServiceSelectionInfo
)

class SetupService:
    """Handles initial setup and stack orchestration."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.docker_client = DockerClient(base_path=str(base_path))
        self.env_manager = EnvManager(str(base_path))

    def get_status(self) -> SetupStatusResponse:
        """Check current setup status."""
        has_env = self.env_manager.env_file_exists()
        supabase_cloned = (self.base_path / "supabase" / "docker").exists()

        # Check for missing secrets
        missing_secrets = []
        if has_env:
            env = self.env_manager.load()
            errors = self.env_manager.validate(env)
            missing_secrets = [e["variable"] for e in errors if e["error"] in ("required", "placeholder")]

        # Count running services
        try:
            containers = self.docker_client.list_containers()
            running = sum(1 for c in containers if c.get("status") == "running")
        except:
            running = 0

        setup_required = not has_env or len(missing_secrets) > 0 or not supabase_cloned

        return SetupStatusResponse(
            setup_required=setup_required,
            has_env_file=has_env,
            has_secrets=len(missing_secrets) == 0,
            supabase_cloned=supabase_cloned,
            services_running=running,
            missing_secrets=missing_secrets
        )

    def get_available_services(self) -> List[ServiceSelectionInfo]:
        """Get list of services available for selection."""
        try:
            parser = ComposeParser(str(self.base_path))
            graph = DependencyGraph(parser)
        except Exception:
            return []

        services = []
        for name, svc_def in parser.services.items():
            # Skip init containers
            if "import" in name or "pull-llama" in name:
                continue

            services.append(ServiceSelectionInfo(
                name=name,
                group=graph.get_service_group(name),
                description=f"From {svc_def.compose_file}",
                required=name in ("db", "kong", "vector"),  # Core Supabase
                dependencies=list(svc_def.depends_on.keys()),
                profiles=svc_def.profiles,
                default_enabled=len(svc_def.profiles) == 0  # No profile = always enabled
            ))

        return services

    async def clone_supabase_repo(self) -> SetupStepResult:
        """Clone/update Supabase repository."""
        supabase_dir = self.base_path / "supabase"

        try:
            if not supabase_dir.exists():
                # Clone with sparse checkout
                subprocess.run([
                    "git", "clone", "--filter=blob:none", "--no-checkout",
                    "https://github.com/supabase/supabase.git",
                    str(supabase_dir)
                ], check=True, capture_output=True)

                subprocess.run(
                    ["git", "sparse-checkout", "init", "--cone"],
                    cwd=supabase_dir, check=True, capture_output=True
                )
                subprocess.run(
                    ["git", "sparse-checkout", "set", "docker"],
                    cwd=supabase_dir, check=True, capture_output=True
                )
                subprocess.run(
                    ["git", "checkout", "master"],
                    cwd=supabase_dir, check=True, capture_output=True
                )
            else:
                subprocess.run(
                    ["git", "pull"],
                    cwd=supabase_dir, check=True, capture_output=True
                )

            return SetupStepResult(
                step="clone_supabase",
                status="completed",
                message="Supabase repository ready"
            )
        except Exception as e:
            return SetupStepResult(
                step="clone_supabase",
                status="failed",
                error=str(e)
            )

    def prepare_env_file(self, config: SetupConfigRequest) -> SetupStepResult:
        """Prepare .env file with secrets and hostnames."""
        try:
            # Start with existing or default config
            if self.env_manager.env_file_exists():
                env = self.env_manager.load()
            else:
                # Load from example if exists
                if self.env_manager.env_example.exists():
                    with open(self.env_manager.env_example) as f:
                        env = {}
                        for line in f:
                            if "=" in line and not line.strip().startswith("#"):
                                key, _, val = line.partition("=")
                                env[key.strip()] = val.strip()
                else:
                    env = {}

            # Apply provided secrets
            env.update(config.secrets)

            # Generate any missing secrets
            missing = generate_missing_secrets(env)
            env.update(missing)

            # Apply hostnames if public environment
            if config.environment == "public":
                env.update(config.hostnames)

            # Save
            self.env_manager.save(env, backup=True)

            return SetupStepResult(
                step="prepare_env",
                status="completed",
                message=f"Configuration saved with {len(missing)} generated secrets"
            )
        except Exception as e:
            return SetupStepResult(
                step="prepare_env",
                status="failed",
                error=str(e)
            )

    def generate_searxng_secret(self) -> SetupStepResult:
        """Generate SearXNG secret key."""
        try:
            settings_base = self.base_path / "searxng" / "settings-base.yml"
            settings_file = self.base_path / "searxng" / "settings.yml"

            if not settings_file.exists() and settings_base.exists():
                shutil.copy(settings_base, settings_file)

            if settings_file.exists():
                import secrets
                secret_key = secrets.token_hex(32)
                content = settings_file.read_text()
                if "ultrasecretkey" in content:
                    content = content.replace("ultrasecretkey", secret_key)
                    settings_file.write_text(content)

            return SetupStepResult(
                step="searxng_secret",
                status="completed",
                message="SearXNG secret generated"
            )
        except Exception as e:
            return SetupStepResult(
                step="searxng_secret",
                status="failed",
                error=str(e)
            )

    async def start_stack(
        self,
        profile: str,
        environment: str,
        enabled_services: Optional[List[str]] = None
    ) -> SetupStepResult:
        """Start the full stack."""
        try:
            # Stop existing containers first
            self.docker_client.compose_down(profile=profile)

            # Start Supabase
            supabase_cmd = [
                "docker", "compose", "-p", "localai",
                "-f", "supabase/docker/docker-compose.yml"
            ]
            if environment == "public":
                supabase_cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
            supabase_cmd.extend(["up", "-d"])

            subprocess.run(supabase_cmd, cwd=self.base_path, check=True, capture_output=True)

            # Wait for Supabase to be ready
            await asyncio.sleep(10)

            # Start local AI services
            result = self.docker_client.compose_up(
                services=enabled_services,
                profile=profile,
                environment=environment
            )

            if result.returncode == 0:
                return SetupStepResult(
                    step="start_stack",
                    status="completed",
                    message="Stack started successfully"
                )
            else:
                return SetupStepResult(
                    step="start_stack",
                    status="failed",
                    error=result.stderr
                )

        except Exception as e:
            return SetupStepResult(
                step="start_stack",
                status="failed",
                error=str(e)
            )

    async def run_full_setup(self, config: SetupConfigRequest) -> SetupProgressResponse:
        """Run the complete setup process."""
        steps = []

        # Step 1: Clone Supabase
        result = await self.clone_supabase_repo()
        steps.append(result)
        if result.status == "failed":
            return SetupProgressResponse(
                status="failed",
                current_step="clone_supabase",
                steps=steps,
                error=result.error
            )

        # Step 2: Prepare environment
        result = self.prepare_env_file(config)
        steps.append(result)
        if result.status == "failed":
            return SetupProgressResponse(
                status="failed",
                current_step="prepare_env",
                steps=steps,
                error=result.error
            )

        # Step 3: SearXNG secret
        result = self.generate_searxng_secret()
        steps.append(result)
        # Non-fatal if fails

        # Step 4: Start stack
        result = await self.start_stack(
            profile=config.profile.value,
            environment=config.environment.value,
            enabled_services=config.enabled_services if config.enabled_services else None
        )
        steps.append(result)

        if result.status == "failed":
            return SetupProgressResponse(
                status="failed",
                current_step="start_stack",
                steps=steps,
                error=result.error
            )

        return SetupProgressResponse(
            status="completed",
            current_step="done",
            steps=steps,
            message="Setup completed successfully!"
        )
```

---

## Task 3: Create Setup Routes (Backend)

**File**: `management-ui/backend/app/api/routes/setup.py`

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from ...schemas.setup import (
    SetupStatusResponse, SetupConfigRequest, SetupProgressResponse,
    ServiceSelectionInfo
)
from ...services.setup_service import SetupService
from ...core.secret_generator import generate_all_secrets
from ..deps import get_current_user
from ...config import settings
from typing import List

router = APIRouter()

def get_setup_service() -> SetupService:
    return SetupService(settings.COMPOSE_BASE_PATH)

@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(
    setup_service: SetupService = Depends(get_setup_service)
):
    """Check if setup is required (no auth required for this endpoint)."""
    return setup_service.get_status()

@router.get("/services", response_model=List[ServiceSelectionInfo])
async def get_available_services(
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Get available services for selection."""
    return setup_service.get_available_services()

@router.post("/generate-secrets")
async def generate_secrets_for_setup(
    _: dict = Depends(get_current_user)
):
    """Generate all secrets for setup."""
    secrets = generate_all_secrets()
    return {"secrets": secrets}

@router.post("/complete", response_model=SetupProgressResponse)
async def complete_setup(
    config: SetupConfigRequest,
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Run the complete setup process."""
    result = await setup_service.run_full_setup(config)
    return result
```

Update routes `__init__.py`:
```python
from .setup import router as setup_router

api_router.include_router(setup_router, prefix="/setup", tags=["setup"])
```

---

## Task 4: Create Setup Wizard Components (Frontend)

**File**: `management-ui/frontend/src/components/setup/ProfileStep.tsx`

```typescript
import React from 'react';
import { Card } from '../common/Card';

interface ProfileStepProps {
  value: string;
  onChange: (value: string) => void;
}

const profiles = [
  {
    id: 'cpu',
    name: 'CPU Only',
    description: 'Run Ollama on CPU. Works everywhere but slower inference.',
    icon: '💻',
  },
  {
    id: 'gpu-nvidia',
    name: 'NVIDIA GPU',
    description: 'Use NVIDIA CUDA for fast inference. Requires NVIDIA GPU.',
    icon: '🎮',
  },
  {
    id: 'gpu-amd',
    name: 'AMD GPU',
    description: 'Use AMD ROCm for inference. Requires AMD GPU.',
    icon: '🔴',
  },
  {
    id: 'none',
    name: 'External Ollama',
    description: 'Use an external Ollama instance. Skip local Ollama.',
    icon: '🌐',
  },
];

export const ProfileStep: React.FC<ProfileStepProps> = ({ value, onChange }) => {
  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Select Hardware Profile</h3>
      <p className="text-gray-600 mb-6">
        Choose how you want to run the local AI models.
      </p>

      <div className="grid grid-cols-2 gap-4">
        {profiles.map((profile) => (
          <Card
            key={profile.id}
            className={`cursor-pointer transition-all ${
              value === profile.id
                ? 'ring-2 ring-blue-500 border-blue-500'
                : 'hover:shadow-md'
            }`}
            onClick={() => onChange(profile.id)}
          >
            <div className="flex items-start gap-3">
              <span className="text-2xl">{profile.icon}</span>
              <div>
                <h4 className="font-medium">{profile.name}</h4>
                <p className="text-sm text-gray-600">{profile.description}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/setup/EnvironmentStep.tsx`

```typescript
import React from 'react';
import { Card } from '../common/Card';

interface EnvironmentStepProps {
  value: string;
  onChange: (value: string) => void;
}

export const EnvironmentStep: React.FC<EnvironmentStepProps> = ({ value, onChange }) => {
  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Select Environment</h3>
      <p className="text-gray-600 mb-6">
        Choose how services will be accessible.
      </p>

      <div className="grid grid-cols-2 gap-4">
        <Card
          className={`cursor-pointer ${value === 'private' ? 'ring-2 ring-blue-500' : ''}`}
          onClick={() => onChange('private')}
        >
          <h4 className="font-medium">🏠 Private (Recommended)</h4>
          <p className="text-sm text-gray-600 mt-2">
            Services bind to localhost only. Access via local ports.
            Best for development and personal use.
          </p>
          <p className="text-xs text-gray-500 mt-2">
            Access: http://localhost:8001, :8002, etc.
          </p>
        </Card>

        <Card
          className={`cursor-pointer ${value === 'public' ? 'ring-2 ring-blue-500' : ''}`}
          onClick={() => onChange('public')}
        >
          <h4 className="font-medium">🌍 Public</h4>
          <p className="text-sm text-gray-600 mt-2">
            Services behind Caddy reverse proxy with HTTPS.
            Requires domain names and opens ports 80/443.
          </p>
          <p className="text-xs text-gray-500 mt-2">
            Access: https://n8n.yourdomain.com, etc.
          </p>
        </Card>
      </div>
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/setup/SecretsStep.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { Button } from '../common/Button';
import { apiClient } from '../../api/client';

interface SecretsStepProps {
  secrets: Record<string, string>;
  onChange: (secrets: Record<string, string>) => void;
}

export const SecretsStep: React.FC<SecretsStepProps> = ({ secrets, onChange }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const response = await apiClient.post('/setup/generate-secrets');
      onChange(response.data.secrets);
      setGenerated(true);
    } catch (e) {
      console.error('Failed to generate secrets:', e);
    } finally {
      setIsGenerating(false);
    }
  };

  const secretCount = Object.keys(secrets).length;

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Generate Secrets</h3>
      <p className="text-gray-600 mb-6">
        Secure secrets are required for encryption and authentication.
        We'll generate cryptographically secure values for you.
      </p>

      <div className="bg-gray-50 rounded-lg p-6 text-center">
        {!generated ? (
          <>
            <p className="mb-4">Click to generate all required secrets:</p>
            <Button onClick={handleGenerate} isLoading={isGenerating}>
              🔐 Generate Secrets
            </Button>
          </>
        ) : (
          <>
            <p className="text-green-600 font-medium mb-2">
              ✅ {secretCount} secrets generated successfully!
            </p>
            <p className="text-sm text-gray-600">
              These will be saved to your .env file.
            </p>

            <div className="mt-4 text-left bg-white rounded p-3 max-h-40 overflow-y-auto">
              {Object.keys(secrets).slice(0, 5).map((key) => (
                <div key={key} className="text-xs font-mono text-gray-600">
                  {key}: ****{secrets[key].slice(-8)}
                </div>
              ))}
              {secretCount > 5 && (
                <div className="text-xs text-gray-500 mt-1">
                  ...and {secretCount - 5} more
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/setup/ConfirmStep.tsx`

```typescript
import React from 'react';
import { Card } from '../common/Card';

interface ConfirmStepProps {
  config: {
    profile: string;
    environment: string;
    secrets: Record<string, string>;
  };
}

export const ConfirmStep: React.FC<ConfirmStepProps> = ({ config }) => {
  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">Confirm Setup</h3>
      <p className="text-gray-600 mb-6">
        Review your configuration before starting the stack.
      </p>

      <Card className="space-y-4">
        <div>
          <span className="text-gray-500">Profile:</span>
          <span className="ml-2 font-medium">{config.profile}</span>
        </div>
        <div>
          <span className="text-gray-500">Environment:</span>
          <span className="ml-2 font-medium">{config.environment}</span>
        </div>
        <div>
          <span className="text-gray-500">Secrets:</span>
          <span className="ml-2 font-medium">
            {Object.keys(config.secrets).length} configured
          </span>
        </div>
      </Card>

      <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">
          ⚠️ This will start all Docker containers. Make sure Docker is running
          and you have enough disk space and memory available.
        </p>
      </div>
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/setup/SetupWizard.tsx`

```typescript
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { ProfileStep } from './ProfileStep';
import { EnvironmentStep } from './EnvironmentStep';
import { SecretsStep } from './SecretsStep';
import { ConfirmStep } from './ConfirmStep';
import { apiClient } from '../../api/client';

const STEPS = ['profile', 'environment', 'secrets', 'confirm'];

interface SetupConfig {
  profile: string;
  environment: string;
  secrets: Record<string, string>;
  enabled_services: string[];
}

export const SetupWizard: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<SetupConfig>({
    profile: 'cpu',
    environment: 'private',
    secrets: {},
    enabled_services: [],
  });

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await apiClient.post('/setup/complete', config);

      if (response.data.status === 'completed') {
        navigate('/');
      } else {
        setError(response.data.error || 'Setup failed');
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Setup failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const canProceed = () => {
    switch (STEPS[currentStep]) {
      case 'secrets':
        return Object.keys(config.secrets).length > 0;
      default:
        return true;
    }
  };

  const renderStep = () => {
    switch (STEPS[currentStep]) {
      case 'profile':
        return (
          <ProfileStep
            value={config.profile}
            onChange={(profile) => setConfig({ ...config, profile })}
          />
        );
      case 'environment':
        return (
          <EnvironmentStep
            value={config.environment}
            onChange={(environment) => setConfig({ ...config, environment })}
          />
        );
      case 'secrets':
        return (
          <SecretsStep
            secrets={config.secrets}
            onChange={(secrets) => setConfig({ ...config, secrets })}
          />
        );
      case 'confirm':
        return <ConfirmStep config={config} />;
      default:
        return null;
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress */}
      <div className="flex justify-center mb-8">
        {STEPS.map((step, index) => (
          <div key={step} className="flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                index <= currentStep
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}
            >
              {index + 1}
            </div>
            {index < STEPS.length - 1 && (
              <div
                className={`w-16 h-1 ${
                  index < currentStep ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <Card className="mb-6">{renderStep()}</Card>

      {/* Error */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-between">
        <Button
          variant="secondary"
          onClick={handleBack}
          disabled={currentStep === 0 || isSubmitting}
        >
          Back
        </Button>

        {currentStep < STEPS.length - 1 ? (
          <Button onClick={handleNext} disabled={!canProceed()}>
            Next
          </Button>
        ) : (
          <Button onClick={handleComplete} isLoading={isSubmitting}>
            🚀 Start Stack
          </Button>
        )}
      </div>
    </div>
  );
};
```

---

## Task 5: Create Setup Wizard Page

**File**: `management-ui/frontend/src/pages/SetupWizard.tsx`

```typescript
import React from 'react';
import { SetupWizard } from '../components/setup/SetupWizard';

export const SetupWizardPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-100 py-12 px-4">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold">Stack Setup</h1>
        <p className="text-gray-600 mt-2">
          Configure and start your local AI stack
        </p>
      </div>

      <SetupWizard />
    </div>
  );
};
```

Add route and link from sidebar.

---

## Validation

### Test Setup Flow
1. Delete .env file to trigger setup
2. Login as admin
3. Navigate to setup wizard
4. Complete each step
5. Verify stack starts

### Success Criteria
- [ ] Setup status correctly detects missing config
- [ ] Profile selection works
- [ ] Environment selection works
- [ ] Secrets generate successfully
- [ ] Confirm step shows correct summary
- [ ] Stack starts after completion
- [ ] Errors display properly if something fails

---

## Next Stage
Proceed to `10-docker-packaging.md` to containerize the management UI.
