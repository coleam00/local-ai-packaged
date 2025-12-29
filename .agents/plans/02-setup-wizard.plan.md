# Plan: First-Run Wizard Improvements - Hardware Detection and Configuration Presets

## Summary

Enhance the existing setup wizard with hardware auto-detection (GPU type, RAM, disk space), platform detection (WSL2, Linux native, macOS), automatic service recommendations based on detected hardware, configuration presets (minimal, standard, full), and comprehensive Docker preflight validation. This addresses GitHub issues #170, #144, #133, #165, #163 where users experience setup failures.

The approach extends the existing `PreflightStep` component with hardware detection capabilities and adds a new `HardwareStep` before the profile selection to automatically recommend the best configuration. The backend will use `psutil` for cross-platform RAM/disk detection, subprocess calls to `nvidia-smi`/`rocm-smi` for GPU detection, and platform.system()/platform.release() for OS detection.

## External Research

### Documentation
- [psutil - Cross-platform RAM/disk detection](https://psutil.readthedocs.io/) - Use `psutil.virtual_memory()` and `psutil.disk_usage()` for cross-platform resource detection
- [nvidia-smi Manual](https://docs.nvidia.com/deploy/nvidia-smi/index.html) - Query `nvidia-smi --query-gpu=name,memory.total --format=csv` for GPU info
- [AMD SMI Documentation](https://rocm.docs.amd.com/projects/amdsmi/en/latest/) - Use `rocm-smi --showmeminfo vram` for AMD GPU detection
- [Docker SDK for Python](https://docker-py.readthedocs.io/) - Use `client.version()` to check Docker version, `client.ping()` for socket access
- [Python platform module](https://docs.python.org/3/library/platform.html) - Use `platform.system()`, `platform.release()` for OS detection

### Gotchas & Best Practices
- WSL2 detection: Check if `platform.release().lower()` contains `microsoft-standard-wsl` (WSL2) or `-microsoft` (WSL1)
- `psutil.virtual_memory().available` is more accurate than `.free` on Linux/macOS (accounts for cached memory)
- nvidia-smi may not be in PATH on Windows - check common locations like `C:\Program Files\NVIDIA Corporation\NVSMI\`
- Docker socket access issues are common - check both `/var/run/docker.sock` and named pipe on Windows
- AMD ROCm requires specific driver installation - `rocm-smi` won't exist without it
- Minimum Docker version for compose v2: 20.10.0+ (Docker Compose V2 is required)

## Patterns to Mirror

### Preflight Check Pattern
```python
# FROM: management-ui/backend/app/services/setup_service.py:121-191
# This is how preflight checks are structured:
def preflight_check(self) -> dict:
    """Check environment state before setup."""
    issues = []
    warnings = []
    can_proceed = True

    # Check condition
    if some_condition:
        issues.append({
            "type": "issue_type",
            "message": "Human-readable message",
            "fix": "fix_action_name"
        })
        can_proceed = False

    return {
        "can_proceed": can_proceed,
        "issues": issues,
        "warnings": warnings
    }
```

### Step Component Pattern
```typescript
// FROM: management-ui/frontend/src/components/setup/PreflightStep.tsx:12-40
// This is how setup step components with async checks work:
interface PreflightStepProps {
  onReady: (ready: boolean) => void;
}

export const PreflightStep: React.FC<PreflightStepProps> = ({ onReady }) => {
  const [check, setCheck] = useState<PreflightCheck | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const runCheck = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await setupApi.preflightCheck();
      setCheck(result);
      onReady(result.can_proceed && result.issues.length === 0);
    } catch (e) {
      setError('Failed to run check');
      onReady(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runCheck();
  }, []);
  // ...
};
```

### API Route Pattern
```python
# FROM: management-ui/backend/app/api/routes/setup.py:63-69
@router.get("/preflight")
async def preflight_check(
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Check environment state before setup."""
    return setup_service.preflight_check()
```

### Schema Pattern
```python
# FROM: management-ui/backend/app/schemas/setup.py:1-26
from pydantic import BaseModel
from typing import List, Dict, Optional

class ResponseModel(BaseModel):
    field: str
    optional_field: Optional[str] = None
    list_field: List[str] = []
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `backend/app/core/hardware_detector.py` | CREATE | Centralized hardware detection logic (GPU, RAM, disk, platform) |
| `backend/app/schemas/setup.py` | UPDATE | Add HardwareInfo and PresetConfig schemas |
| `backend/app/services/setup_service.py` | UPDATE | Add hardware detection and preset methods, enhance preflight |
| `backend/app/api/routes/setup.py` | UPDATE | Add /hardware and /presets endpoints |
| `backend/requirements.txt` | UPDATE | Add psutil dependency |
| `frontend/src/api/setup.ts` | UPDATE | Add hardware and presets API types and methods |
| `frontend/src/components/setup/HardwareStep.tsx` | CREATE | New step for hardware display and preset selection |
| `frontend/src/components/setup/PreflightStep.tsx` | UPDATE | Enhance with Docker version/socket validation display |
| `frontend/src/components/setup/SetupWizard.tsx` | UPDATE | Add hardware step, update step flow |

## NOT Building

- GPU benchmarking or performance testing
- Real-time hardware monitoring during setup
- Automatic driver installation
- Custom preset creation/saving
- Hardware compatibility database lookups
- Automatic service port conflict detection (beyond Docker socket)
- Multi-GPU detection (will detect first GPU only for simplicity)
- Apple Silicon (M1/M2/M3) GPU detection (macOS uses CPU profile anyway)

## Tasks

### Task 1: Add psutil dependency

**Why**: Required for cross-platform RAM and disk space detection.

**File**: `management-ui/backend/requirements.txt`

**Do**:
Add to requirements.txt:
```
psutil>=5.9.0
```

**Don't**:
- Don't add GPU-specific libraries (nvidia-ml-py, amdsmi) - use subprocess to avoid installation issues

**Verify**: `pip install -r requirements.txt && python -c "import psutil; print(psutil.virtual_memory().total)"`

---

### Task 2: Create Hardware Detector Module

**Why**: Centralized hardware detection makes it reusable and testable.

**Mirror**: `backend/app/core/docker_client.py` structure

**File**: `management-ui/backend/app/core/hardware_detector.py`

**Do**:
```python
"""
Hardware detection for setup wizard.
Detects GPU, RAM, disk space, and platform type.
"""
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class GPUInfo:
    """Detected GPU information."""
    type: str  # 'nvidia', 'amd', 'none'
    name: Optional[str] = None
    vram_mb: Optional[int] = None
    driver_version: Optional[str] = None
    cuda_version: Optional[str] = None


@dataclass
class SystemInfo:
    """System hardware information."""
    platform: str  # 'linux', 'macos', 'windows', 'wsl1', 'wsl2'
    platform_display: str  # Human-readable name
    ram_total_gb: float
    ram_available_gb: float
    disk_total_gb: float
    disk_free_gb: float
    cpu_cores: int
    gpu: GPUInfo


class HardwareDetector:
    """Detects system hardware for setup recommendations."""

    def detect_platform(self) -> tuple[str, str]:
        """
        Detect the running platform.
        Returns: (platform_id, platform_display_name)
        """
        system = platform.system()

        if system == 'Darwin':
            # Get macOS version
            mac_version = platform.mac_ver()[0]
            return 'macos', f'macOS {mac_version}'

        elif system == 'Windows':
            win_version = platform.release()
            return 'windows', f'Windows {win_version}'

        elif system == 'Linux':
            release = platform.release().lower()

            # Check for WSL
            if 'microsoft-standard-wsl' in release:
                return 'wsl2', 'Windows WSL2'
            elif 'microsoft' in release:
                return 'wsl1', 'Windows WSL1'

            # Try to get distro info
            try:
                with open('/etc/os-release') as f:
                    lines = f.read()
                    for line in lines.split('\n'):
                        if line.startswith('PRETTY_NAME='):
                            distro = line.split('=')[1].strip('"')
                            return 'linux', distro
            except Exception:
                pass

            return 'linux', 'Linux'

        return system.lower(), system

    def detect_nvidia_gpu(self) -> Optional[GPUInfo]:
        """Detect NVIDIA GPU using nvidia-smi."""
        nvidia_smi = shutil.which('nvidia-smi')

        # Check common Windows locations
        if not nvidia_smi and platform.system() == 'Windows':
            common_paths = [
                r'C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe',
                r'C:\Windows\System32\nvidia-smi.exe',
            ]
            for path in common_paths:
                if Path(path).exists():
                    nvidia_smi = path
                    break

        if not nvidia_smi:
            return None

        try:
            # Query GPU name and memory
            result = subprocess.run(
                [nvidia_smi, '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return None

            output = result.stdout.strip()
            if not output:
                return None

            # Parse first GPU only
            parts = output.split('\n')[0].split(',')
            name = parts[0].strip() if len(parts) > 0 else None
            vram_mb = int(float(parts[1].strip())) if len(parts) > 1 else None
            driver = parts[2].strip() if len(parts) > 2 else None

            # Try to get CUDA version
            cuda_version = None
            try:
                cuda_result = subprocess.run(
                    [nvidia_smi],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in cuda_result.stdout.split('\n'):
                    if 'CUDA Version' in line:
                        cuda_version = line.split('CUDA Version:')[1].split()[0].strip()
                        break
            except Exception:
                pass

            return GPUInfo(
                type='nvidia',
                name=name,
                vram_mb=vram_mb,
                driver_version=driver,
                cuda_version=cuda_version
            )
        except Exception:
            return None

    def detect_amd_gpu(self) -> Optional[GPUInfo]:
        """Detect AMD GPU using rocm-smi."""
        rocm_smi = shutil.which('rocm-smi')

        if not rocm_smi:
            # Check common locations
            if Path('/opt/rocm/bin/rocm-smi').exists():
                rocm_smi = '/opt/rocm/bin/rocm-smi'

        if not rocm_smi:
            return None

        try:
            # Get GPU name
            result = subprocess.run(
                [rocm_smi, '--showproductname'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return None

            # Parse output for GPU name
            name = None
            for line in result.stdout.split('\n'):
                if 'Card series' in line or 'GPU' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        name = parts[1].strip()
                        break

            # Get VRAM
            vram_mb = None
            try:
                vram_result = subprocess.run(
                    [rocm_smi, '--showmeminfo', 'vram'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                for line in vram_result.stdout.split('\n'):
                    if 'Total Memory' in line:
                        # Parse memory value (usually in MB or bytes)
                        parts = line.split(':')
                        if len(parts) > 1:
                            mem_str = parts[1].strip().split()[0]
                            vram_mb = int(mem_str) // (1024 * 1024)  # Convert bytes to MB
            except Exception:
                pass

            return GPUInfo(
                type='amd',
                name=name or 'AMD GPU',
                vram_mb=vram_mb
            )
        except Exception:
            return None

    def detect_gpu(self) -> GPUInfo:
        """Detect any available GPU."""
        # Try NVIDIA first
        nvidia = self.detect_nvidia_gpu()
        if nvidia:
            return nvidia

        # Try AMD
        amd = self.detect_amd_gpu()
        if amd:
            return amd

        # No GPU detected
        return GPUInfo(type='none')

    def detect_resources(self) -> Dict[str, float]:
        """Detect RAM and disk space."""
        result = {
            'ram_total_gb': 0.0,
            'ram_available_gb': 0.0,
            'disk_total_gb': 0.0,
            'disk_free_gb': 0.0,
            'cpu_cores': 1
        }

        if not HAS_PSUTIL:
            return result

        try:
            # RAM
            mem = psutil.virtual_memory()
            result['ram_total_gb'] = round(mem.total / (1024 ** 3), 1)
            result['ram_available_gb'] = round(mem.available / (1024 ** 3), 1)

            # Disk - check root or C: drive
            if platform.system() == 'Windows':
                disk_path = 'C:\\'
            else:
                disk_path = '/'

            disk = psutil.disk_usage(disk_path)
            result['disk_total_gb'] = round(disk.total / (1024 ** 3), 1)
            result['disk_free_gb'] = round(disk.free / (1024 ** 3), 1)

            # CPU cores
            result['cpu_cores'] = psutil.cpu_count(logical=False) or psutil.cpu_count() or 1

        except Exception:
            pass

        return result

    def detect_all(self) -> SystemInfo:
        """Run full hardware detection."""
        platform_id, platform_display = self.detect_platform()
        gpu = self.detect_gpu()
        resources = self.detect_resources()

        return SystemInfo(
            platform=platform_id,
            platform_display=platform_display,
            ram_total_gb=resources['ram_total_gb'],
            ram_available_gb=resources['ram_available_gb'],
            disk_total_gb=resources['disk_total_gb'],
            disk_free_gb=resources['disk_free_gb'],
            cpu_cores=resources['cpu_cores'],
            gpu=gpu
        )

    def get_recommended_profile(self, info: SystemInfo) -> str:
        """Get recommended GPU profile based on hardware."""
        if info.gpu.type == 'nvidia':
            return 'gpu-nvidia'
        elif info.gpu.type == 'amd':
            return 'gpu-amd'
        else:
            return 'cpu'

    def get_recommended_preset(self, info: SystemInfo) -> str:
        """
        Get recommended configuration preset based on hardware.

        Presets:
        - minimal: <8GB RAM or <20GB disk - Core services only
        - standard: 8-16GB RAM - Standard services (default)
        - full: >16GB RAM and >50GB disk - All services including observability
        """
        ram = info.ram_total_gb
        disk = info.disk_free_gb

        if ram < 8 or disk < 20:
            return 'minimal'
        elif ram >= 16 and disk >= 50:
            return 'full'
        else:
            return 'standard'

    def get_platform_guidance(self, platform_id: str) -> Dict[str, Any]:
        """Get platform-specific setup guidance."""
        guidance = {
            'wsl2': {
                'title': 'Windows WSL2 Detected',
                'tips': [
                    'Ensure Docker Desktop is running with WSL2 backend enabled',
                    'GPU passthrough requires NVIDIA Container Toolkit in WSL2',
                    'Performance is best with files stored in the Linux filesystem (~/ not /mnt/c/)',
                ],
                'warnings': [
                    'Docker commands may fail if Docker Desktop is not running',
                    'File operations on /mnt/c/ are slower than native Linux paths',
                ],
                'docs_url': 'https://docs.docker.com/desktop/wsl/'
            },
            'wsl1': {
                'title': 'Windows WSL1 Detected (Upgrade Recommended)',
                'tips': [
                    'WSL2 offers significantly better Docker performance',
                    'GPU passthrough is not available in WSL1',
                ],
                'warnings': [
                    'WSL1 has limited Docker support - consider upgrading to WSL2',
                ],
                'docs_url': 'https://learn.microsoft.com/en-us/windows/wsl/install'
            },
            'linux': {
                'title': 'Native Linux Detected',
                'tips': [
                    'Ensure Docker daemon is running: sudo systemctl start docker',
                    'Add your user to docker group to avoid sudo: sudo usermod -aG docker $USER',
                    'For NVIDIA GPU: Install NVIDIA Container Toolkit',
                ],
                'warnings': [],
                'docs_url': 'https://docs.docker.com/engine/install/'
            },
            'macos': {
                'title': 'macOS Detected',
                'tips': [
                    'Docker Desktop for Mac is required',
                    'GPU acceleration is not available - using CPU profile',
                    'Increase Docker memory allocation in Docker Desktop settings if needed',
                ],
                'warnings': [
                    'Local LLM inference will use CPU only (no GPU acceleration on macOS Docker)',
                ],
                'docs_url': 'https://docs.docker.com/desktop/install/mac-install/'
            },
            'windows': {
                'title': 'Native Windows Detected',
                'tips': [
                    'Docker Desktop for Windows is required',
                    'WSL2 backend is recommended for better performance',
                ],
                'warnings': [
                    'Consider running inside WSL2 for better Docker performance',
                ],
                'docs_url': 'https://docs.docker.com/desktop/install/windows-install/'
            }
        }

        return guidance.get(platform_id, {
            'title': 'Platform Detected',
            'tips': [],
            'warnings': [],
            'docs_url': 'https://docs.docker.com/get-docker/'
        })
```

**Don't**:
- Don't use nvidia-ml-py/pynvml library (avoid installation complexity)
- Don't detect multiple GPUs (out of scope, first GPU is sufficient)
- Don't auto-install drivers

**Verify**: `python -c "from app.core.hardware_detector import HardwareDetector; print(HardwareDetector().detect_all())"`

---

### Task 3: Update Setup Schemas for Hardware Detection

**Why**: Need typed responses for hardware info and presets.

**Mirror**: `backend/app/schemas/setup.py` existing patterns

**File**: `management-ui/backend/app/schemas/setup.py`

**Do**:
Add after existing schemas:
```python
class GPUInfoResponse(BaseModel):
    type: str  # 'nvidia', 'amd', 'none'
    name: Optional[str] = None
    vram_mb: Optional[int] = None
    driver_version: Optional[str] = None
    cuda_version: Optional[str] = None


class PlatformGuidance(BaseModel):
    title: str
    tips: List[str]
    warnings: List[str]
    docs_url: str


class HardwareInfoResponse(BaseModel):
    platform: str
    platform_display: str
    ram_total_gb: float
    ram_available_gb: float
    disk_total_gb: float
    disk_free_gb: float
    cpu_cores: int
    gpu: GPUInfoResponse
    recommended_profile: str
    recommended_preset: str
    platform_guidance: PlatformGuidance


class PresetConfig(BaseModel):
    id: str  # 'minimal', 'standard', 'full'
    name: str
    description: str
    min_ram_gb: int
    min_disk_gb: int
    services: List[str]  # Service names to enable


class DockerValidation(BaseModel):
    docker_installed: bool
    docker_version: Optional[str] = None
    docker_version_ok: bool = False
    socket_accessible: bool = False
    compose_v2: bool = False
    errors: List[str]
    warnings: List[str]
```

Also update the existing PreflightCheck to include docker validation fields.

**Don't**:
- Don't duplicate existing schema patterns

**Verify**: `python -c "from app.schemas.setup import HardwareInfoResponse; print('OK')"`

---

### Task 4: Update Setup Service with Hardware Detection

**Why**: Backend needs to expose hardware detection and presets functionality.

**Mirror**: `backend/app/services/setup_service.py:121-191` (preflight_check pattern)

**File**: `management-ui/backend/app/services/setup_service.py`

**Do**:
Add imports at top:
```python
from ..core.hardware_detector import HardwareDetector, SystemInfo
```

Add new methods to `SetupService` class:

```python
    def detect_hardware(self) -> dict:
        """Detect system hardware and return recommendations."""
        detector = HardwareDetector()
        info = detector.detect_all()
        guidance = detector.get_platform_guidance(info.platform)

        return {
            "platform": info.platform,
            "platform_display": info.platform_display,
            "ram_total_gb": info.ram_total_gb,
            "ram_available_gb": info.ram_available_gb,
            "disk_total_gb": info.disk_total_gb,
            "disk_free_gb": info.disk_free_gb,
            "cpu_cores": info.cpu_cores,
            "gpu": {
                "type": info.gpu.type,
                "name": info.gpu.name,
                "vram_mb": info.gpu.vram_mb,
                "driver_version": info.gpu.driver_version,
                "cuda_version": info.gpu.cuda_version,
            },
            "recommended_profile": detector.get_recommended_profile(info),
            "recommended_preset": detector.get_recommended_preset(info),
            "platform_guidance": guidance
        }

    def get_presets(self) -> list:
        """Get available configuration presets."""
        from .service_dependencies import SERVICE_CONFIGS

        # Define preset service lists
        core_services = ["open-webui", "flowise"]
        standard_services = core_services + ["n8n", "qdrant", "searxng"]
        full_services = standard_services + ["neo4j", "langfuse-web", "langfuse-worker"]

        return [
            {
                "id": "minimal",
                "name": "Minimal",
                "description": "Essential AI services only. Best for systems with limited resources.",
                "min_ram_gb": 4,
                "min_disk_gb": 10,
                "services": core_services
            },
            {
                "id": "standard",
                "name": "Standard (Recommended)",
                "description": "Core AI services plus workflow automation and vector database.",
                "min_ram_gb": 8,
                "min_disk_gb": 25,
                "services": standard_services
            },
            {
                "id": "full",
                "name": "Full",
                "description": "All services including graph database and LLM observability.",
                "min_ram_gb": 16,
                "min_disk_gb": 50,
                "services": full_services
            }
        ]

    def validate_docker(self) -> dict:
        """Validate Docker installation and accessibility."""
        errors = []
        warnings = []

        docker_installed = False
        docker_version = None
        docker_version_ok = False
        socket_accessible = False
        compose_v2 = False

        # Check Docker installed
        docker_path = shutil.which('docker')
        if not docker_path:
            errors.append("Docker is not installed or not in PATH")
        else:
            docker_installed = True

            # Check Docker version
            try:
                result = subprocess.run(
                    ['docker', 'version', '--format', '{{.Server.Version}}'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    docker_version = result.stdout.strip()
                    # Parse version - need at least 20.10.0
                    parts = docker_version.split('.')
                    if len(parts) >= 2:
                        major = int(parts[0])
                        minor = int(parts[1].split('-')[0])
                        docker_version_ok = (major > 20) or (major == 20 and minor >= 10)

                    if not docker_version_ok:
                        errors.append(f"Docker version {docker_version} is too old. Need 20.10.0+")
                else:
                    # Could be permission issue
                    if 'permission denied' in result.stderr.lower():
                        errors.append("Docker socket permission denied. Run: sudo usermod -aG docker $USER")
                    else:
                        errors.append(f"Failed to get Docker version: {result.stderr}")
            except subprocess.TimeoutExpired:
                errors.append("Docker command timed out - Docker daemon may not be running")
            except Exception as e:
                errors.append(f"Failed to check Docker: {str(e)}")

            # Check socket accessibility via ping
            try:
                self.docker_client.client.ping()
                socket_accessible = True
            except Exception as e:
                err_str = str(e).lower()
                if 'permission denied' in err_str:
                    errors.append("Docker socket permission denied. Add user to docker group or run with sudo")
                elif 'connection refused' in err_str or 'not running' in err_str:
                    errors.append("Docker daemon is not running. Start Docker Desktop or run: sudo systemctl start docker")
                else:
                    errors.append(f"Cannot connect to Docker: {str(e)[:100]}")

            # Check Docker Compose v2
            try:
                result = subprocess.run(
                    ['docker', 'compose', 'version'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    compose_v2 = True
                else:
                    warnings.append("Docker Compose V2 not found. Some features may not work.")
            except Exception:
                warnings.append("Could not verify Docker Compose V2")

        return {
            "docker_installed": docker_installed,
            "docker_version": docker_version,
            "docker_version_ok": docker_version_ok,
            "socket_accessible": socket_accessible,
            "compose_v2": compose_v2,
            "errors": errors,
            "warnings": warnings
        }
```

Also add `import shutil` to the imports if not present.

Update `preflight_check` method to include Docker validation:
```python
    def preflight_check(self) -> dict:
        """Check environment state before setup."""
        issues = []
        warnings = []
        can_proceed = True

        # Docker validation first
        docker_check = self.validate_docker()
        for err in docker_check["errors"]:
            issues.append({
                "type": "docker_error",
                "message": err,
                "fix": "install_docker" if "not installed" in err.lower() else "fix_docker"
            })
            can_proceed = False

        for warn in docker_check["warnings"]:
            warnings.append({
                "type": "docker_warning",
                "message": warn,
                "fix": None
            })

        # ... rest of existing preflight checks ...
```

**Don't**:
- Don't break existing methods
- Don't add GPU library dependencies

**Verify**: Run backend and test `/setup/hardware` endpoint

---

### Task 5: Add Hardware and Presets API Routes

**Why**: Frontend needs API endpoints to fetch hardware info and presets.

**Mirror**: `backend/app/api/routes/setup.py:63-69` pattern

**File**: `management-ui/backend/app/api/routes/setup.py`

**Do**:
Add new imports:
```python
from ...schemas.setup import HardwareInfoResponse, PresetConfig, DockerValidation
```

Add new endpoints after existing routes:
```python
@router.get("/hardware", response_model=HardwareInfoResponse)
async def detect_hardware(
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Detect system hardware and get recommendations."""
    return setup_service.detect_hardware()


@router.get("/presets", response_model=List[PresetConfig])
async def get_presets(
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Get available configuration presets."""
    return setup_service.get_presets()


@router.get("/docker-validation", response_model=DockerValidation)
async def validate_docker(
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Validate Docker installation and accessibility."""
    return setup_service.validate_docker()
```

**Don't**:
- Don't change existing endpoint signatures

**Verify**: `curl http://localhost:8000/api/setup/hardware`

---

### Task 6: Update Frontend Setup API

**Why**: Frontend needs TypeScript types and API methods for new endpoints.

**Mirror**: `frontend/src/api/setup.ts` existing patterns

**File**: `management-ui/frontend/src/api/setup.ts`

**Do**:
Add new interfaces after existing ones:
```typescript
export interface GPUInfo {
  type: 'nvidia' | 'amd' | 'none';
  name: string | null;
  vram_mb: number | null;
  driver_version: string | null;
  cuda_version: string | null;
}

export interface PlatformGuidance {
  title: string;
  tips: string[];
  warnings: string[];
  docs_url: string;
}

export interface HardwareInfo {
  platform: string;
  platform_display: string;
  ram_total_gb: number;
  ram_available_gb: number;
  disk_total_gb: number;
  disk_free_gb: number;
  cpu_cores: number;
  gpu: GPUInfo;
  recommended_profile: string;
  recommended_preset: string;
  platform_guidance: PlatformGuidance;
}

export interface PresetConfig {
  id: string;
  name: string;
  description: string;
  min_ram_gb: number;
  min_disk_gb: number;
  services: string[];
}

export interface DockerValidation {
  docker_installed: boolean;
  docker_version: string | null;
  docker_version_ok: boolean;
  socket_accessible: boolean;
  compose_v2: boolean;
  errors: string[];
  warnings: string[];
}
```

Add new methods to `setupApi` object:
```typescript
  async detectHardware(): Promise<HardwareInfo> {
    const response = await apiClient.get<HardwareInfo>('/setup/hardware');
    return response.data;
  },

  async getPresets(): Promise<PresetConfig[]> {
    const response = await apiClient.get<PresetConfig[]>('/setup/presets');
    return response.data;
  },

  async validateDocker(): Promise<DockerValidation> {
    const response = await apiClient.get<DockerValidation>('/setup/docker-validation');
    return response.data;
  },
```

**Don't**:
- Don't duplicate existing types

**Verify**: TypeScript compilation succeeds

---

### Task 7: Create HardwareStep Component

**Why**: Display detected hardware and allow preset selection before profile selection.

**Mirror**: `frontend/src/components/setup/PreflightStep.tsx` structure

**File**: `management-ui/frontend/src/components/setup/HardwareStep.tsx`

**Do**:
```typescript
import React, { useEffect, useState } from 'react';
import { setupApi } from '../../api/setup';
import type { HardwareInfo, PresetConfig } from '../../api/setup';
import {
  Cpu, HardDrive, MemoryStick, Monitor, Server,
  CheckCircle, AlertTriangle, Info, ExternalLink, Loader2
} from 'lucide-react';
import { Card } from '../common/Card';

interface HardwareStepProps {
  onReady: (ready: boolean) => void;
  onProfileChange: (profile: string) => void;
  onPresetChange: (preset: string, services: string[]) => void;
}

export const HardwareStep: React.FC<HardwareStepProps> = ({
  onReady,
  onProfileChange,
  onPresetChange
}) => {
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [presets, setPresets] = useState<PresetConfig[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const detect = async () => {
      setLoading(true);
      setError(null);
      try {
        const [hw, presetList] = await Promise.all([
          setupApi.detectHardware(),
          setupApi.getPresets()
        ]);
        setHardware(hw);
        setPresets(presetList);

        // Auto-select recommended preset and profile
        setSelectedPreset(hw.recommended_preset);
        onProfileChange(hw.recommended_profile);

        const preset = presetList.find(p => p.id === hw.recommended_preset);
        if (preset) {
          onPresetChange(hw.recommended_preset, preset.services);
        }

        onReady(true);
      } catch (e) {
        setError('Failed to detect hardware');
        onReady(false);
      } finally {
        setLoading(false);
      }
    };
    detect();
  }, []);

  const handlePresetSelect = (presetId: string) => {
    setSelectedPreset(presetId);
    const preset = presets.find(p => p.id === presetId);
    if (preset) {
      onPresetChange(presetId, preset.services);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-blue-400 animate-spin mb-4" />
        <p className="text-gray-400">Detecting hardware...</p>
      </div>
    );
  }

  if (error || !hardware) {
    return (
      <div className="text-center py-8">
        <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
        <p className="text-gray-400">{error || 'Failed to detect hardware'}</p>
      </div>
    );
  }

  const { gpu, platform_guidance: guidance } = hardware;

  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-2">System Detected</h3>
      <p className="text-gray-400 mb-6">
        We've analyzed your system. Review the details and choose a configuration preset.
      </p>

      {/* Platform info banner */}
      <div className="mb-6 p-4 bg-blue-900/20 border border-blue-700/50 rounded-lg">
        <div className="flex items-start gap-3">
          <Monitor className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-medium text-blue-300">{guidance.title}</h4>
            {guidance.tips.length > 0 && (
              <ul className="mt-2 text-sm text-blue-400/80 space-y-1">
                {guidance.tips.map((tip, i) => (
                  <li key={i}>• {tip}</li>
                ))}
              </ul>
            )}
            {guidance.warnings.length > 0 && (
              <div className="mt-2 text-sm text-yellow-400 space-y-1">
                {guidance.warnings.map((warn, i) => (
                  <p key={i} className="flex items-start gap-1">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    {warn}
                  </p>
                ))}
              </div>
            )}
            <a
              href={guidance.docs_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-2 text-sm text-blue-400 hover:text-blue-300"
            >
              <ExternalLink className="w-3 h-3" />
              Platform documentation
            </a>
          </div>
        </div>
      </div>

      {/* Hardware specs grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-3 bg-gray-800 rounded-lg">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <MemoryStick className="w-4 h-4" />
            RAM
          </div>
          <div className="font-medium text-white">{hardware.ram_total_gb} GB</div>
          <div className="text-xs text-gray-500">{hardware.ram_available_gb} GB available</div>
        </div>

        <div className="p-3 bg-gray-800 rounded-lg">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <HardDrive className="w-4 h-4" />
            Disk
          </div>
          <div className="font-medium text-white">{hardware.disk_free_gb} GB free</div>
          <div className="text-xs text-gray-500">of {hardware.disk_total_gb} GB</div>
        </div>

        <div className="p-3 bg-gray-800 rounded-lg">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Cpu className="w-4 h-4" />
            CPU
          </div>
          <div className="font-medium text-white">{hardware.cpu_cores} cores</div>
        </div>

        <div className="p-3 bg-gray-800 rounded-lg">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Server className="w-4 h-4" />
            GPU
          </div>
          {gpu.type === 'none' ? (
            <>
              <div className="font-medium text-gray-400">None detected</div>
              <div className="text-xs text-gray-500">Using CPU mode</div>
            </>
          ) : (
            <>
              <div className="font-medium text-white truncate" title={gpu.name || gpu.type}>
                {gpu.name || gpu.type.toUpperCase()}
              </div>
              <div className="text-xs text-gray-500">
                {gpu.vram_mb ? `${Math.round(gpu.vram_mb / 1024)} GB VRAM` : gpu.type.toUpperCase()}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Recommended profile badge */}
      <div className="mb-4 flex items-center gap-2 text-sm">
        <CheckCircle className="w-4 h-4 text-green-400" />
        <span className="text-gray-400">Recommended profile:</span>
        <span className="px-2 py-0.5 bg-green-900/50 text-green-400 rounded font-medium">
          {hardware.recommended_profile === 'gpu-nvidia' ? 'NVIDIA GPU' :
           hardware.recommended_profile === 'gpu-amd' ? 'AMD GPU' : 'CPU'}
        </span>
      </div>

      {/* Preset selection */}
      <h4 className="font-medium text-white mb-3">Choose Configuration Preset</h4>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {presets.map((preset) => {
          const isRecommended = preset.id === hardware.recommended_preset;
          const isSelected = preset.id === selectedPreset;
          const meetsRequirements =
            hardware.ram_total_gb >= preset.min_ram_gb &&
            hardware.disk_free_gb >= preset.min_disk_gb;

          return (
            <Card
              key={preset.id}
              className={`cursor-pointer transition-all relative ${
                isSelected
                  ? 'ring-2 ring-blue-500 border-blue-500'
                  : meetsRequirements
                    ? 'hover:border-gray-500'
                    : 'opacity-50 cursor-not-allowed'
              }`}
              onClick={() => meetsRequirements && handlePresetSelect(preset.id)}
            >
              {isRecommended && (
                <span className="absolute -top-2 -right-2 px-2 py-0.5 bg-green-600 text-white text-xs rounded-full">
                  Recommended
                </span>
              )}
              <h5 className="font-medium text-white mb-1">{preset.name}</h5>
              <p className="text-sm text-gray-400 mb-2">{preset.description}</p>
              <div className="text-xs text-gray-500">
                Requires: {preset.min_ram_gb}GB RAM, {preset.min_disk_gb}GB disk
              </div>
              {!meetsRequirements && (
                <div className="text-xs text-yellow-400 mt-1 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  Insufficient resources
                </div>
              )}
            </Card>
          );
        })}
      </div>

      <div className="mt-4 p-3 bg-gray-800 rounded-lg flex items-start gap-2">
        <Info className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-gray-400">
          You can customize individual services in the next step. Presets are starting points
          based on your system resources.
        </p>
      </div>
    </div>
  );
};
```

**Don't**:
- Don't block on hardware detection failures (allow manual selection)
- Don't show technical error details to users

**Verify**: Component renders without TypeScript errors

---

### Task 8: Update PreflightStep with Enhanced Docker Validation Display

**Why**: Show users clear Docker validation status with helpful fix suggestions.

**Mirror**: Existing `PreflightStep.tsx` issue display pattern

**File**: `management-ui/frontend/src/components/setup/PreflightStep.tsx`

**Do**:
Add Docker-specific UI elements. After the existing issues/warnings sections, add a Docker validation summary section:

Update imports:
```typescript
import { CheckCircle, AlertTriangle, XCircle, Loader2, Wrench, Terminal } from 'lucide-react';
```

Add Docker validation display after the warnings section but before the re-check button:
```typescript
      {/* Docker validation details */}
      {check && (
        <div className="mt-4 p-4 bg-gray-800 rounded-lg">
          <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
            <Terminal className="w-4 h-4" />
            Docker Status
          </h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="flex items-center gap-2">
              {check.docker_installed ? (
                <CheckCircle className="w-4 h-4 text-green-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
              <span className="text-gray-400">Docker installed</span>
            </div>
            <div className="flex items-center gap-2">
              {check.socket_accessible ? (
                <CheckCircle className="w-4 h-4 text-green-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
              <span className="text-gray-400">Docker accessible</span>
            </div>
            <div className="flex items-center gap-2">
              {check.docker_version_ok ? (
                <CheckCircle className="w-4 h-4 text-green-400" />
              ) : check.docker_version ? (
                <AlertTriangle className="w-4 h-4 text-yellow-400" />
              ) : (
                <XCircle className="w-4 h-4 text-gray-600" />
              )}
              <span className="text-gray-400">
                {check.docker_version ? `v${check.docker_version}` : 'Version unknown'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {check.compose_v2 ? (
                <CheckCircle className="w-4 h-4 text-green-400" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-yellow-400" />
              )}
              <span className="text-gray-400">Compose V2</span>
            </div>
          </div>
        </div>
      )}
```

Note: This requires the backend to return Docker validation info as part of the preflight check. The existing `preflight_check` already includes these fields based on our Task 4 updates.

**Don't**:
- Don't change existing fix button logic
- Don't auto-fix Docker issues (too risky)

**Verify**: Visual inspection shows Docker status grid

---

### Task 9: Update SetupWizard to Include Hardware Step

**Why**: Need to integrate HardwareStep into the wizard flow and pass preset selections.

**Mirror**: Current SetupWizard step management

**File**: `management-ui/frontend/src/components/setup/SetupWizard.tsx`

**Do**:
Add import:
```typescript
import { HardwareStep } from './HardwareStep';
```

Update STEPS array to include hardware step:
```typescript
const STEPS = ['preflight', 'hardware', 'profile', 'services', 'environment', 'secrets', 'confirm'] as const;
const STEP_LABELS = ['Check', 'Hardware', 'Profile', 'Services', 'Environment', 'Secrets', 'Confirm'];
```

Add state for hardware readiness:
```typescript
const [hardwareReady, setHardwareReady] = useState(false);
```

Add hardware case to `canProceed`:
```typescript
case 'hardware':
  return hardwareReady;
```

Add hardware case to `renderStep`:
```typescript
case 'hardware':
  return (
    <HardwareStep
      onReady={setHardwareReady}
      onProfileChange={(profile) => setConfig({ ...config, profile })}
      onPresetChange={(preset, services) => setConfig({
        ...config,
        enabled_services: services
      })}
    />
  );
```

**Don't**:
- Don't remove existing step logic
- Don't change the confirm step

**Verify**: Navigate through wizard, hardware step appears after preflight

---

## Validation Strategy

### Automated Checks
- [ ] `cd management-ui/backend && pip install -r requirements.txt` - Dependencies install
- [ ] `cd management-ui/backend && python -c "from app.core.hardware_detector import HardwareDetector; print('OK')"` - Hardware detector imports
- [ ] `cd management-ui/frontend && npm run build` - Frontend builds
- [ ] `cd management-ui/frontend && npm run lint` - No lint errors

### New Tests to Write

| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `backend/tests/test_hardware_detector.py` | `test_detect_platform` | Platform detection returns valid values |
| `backend/tests/test_hardware_detector.py` | `test_detect_resources` | RAM/disk values are numeric and reasonable |
| `backend/tests/test_hardware_detector.py` | `test_recommended_profile` | Profile recommendation based on GPU type |
| `backend/tests/test_hardware_detector.py` | `test_recommended_preset` | Preset recommendation based on resources |

### Manual/E2E Validation

```bash
# Test hardware detection endpoint
curl -X GET http://localhost:8000/api/setup/hardware \
  -H "Authorization: Bearer <token>"

# Test presets endpoint
curl -X GET http://localhost:8000/api/setup/presets \
  -H "Authorization: Bearer <token>"

# Test Docker validation endpoint
curl -X GET http://localhost:8000/api/setup/docker-validation \
  -H "Authorization: Bearer <token>"
```

1. **GPU detection test**:
   - On NVIDIA system: Verify `gpu.type` is `nvidia` and `recommended_profile` is `gpu-nvidia`
   - On AMD system: Verify `gpu.type` is `amd` and `recommended_profile` is `gpu-amd`
   - On CPU-only system: Verify `gpu.type` is `none` and `recommended_profile` is `cpu`

2. **Platform detection test**:
   - On WSL2: Verify `platform` is `wsl2` and guidance mentions Docker Desktop
   - On native Linux: Verify `platform` is `linux`
   - On macOS: Verify `platform` is `macos` and warnings mention no GPU

3. **Preset selection test**:
   - System with 6GB RAM: Verify `recommended_preset` is `minimal`
   - System with 12GB RAM: Verify `recommended_preset` is `standard`
   - System with 32GB RAM: Verify `recommended_preset` is `full`

4. **Wizard flow test**:
   - Complete wizard from start
   - Verify hardware step shows before profile
   - Verify preset selection updates services list
   - Verify profile can be changed manually after auto-recommendation

### Edge Cases

- [ ] nvidia-smi not in PATH but GPU exists - should still detect via common paths
- [ ] Docker not running - should show clear error with fix suggestion
- [ ] psutil not installed - should gracefully return 0 values
- [ ] WSL1 detected - should show upgrade warning
- [ ] Very low disk space (<5GB) - should warn but allow proceed
- [ ] rocm-smi exists but no AMD GPU - should handle gracefully

### Regression Check

- [ ] Existing preflight checks still work
- [ ] Existing service selection still works
- [ ] Profile selection can still be changed manually
- [ ] Setup completion still works end-to-end
- [ ] Skipping hardware step doesn't break wizard

## Risks

1. **Hardware detection accuracy**: Different systems may have nvidia-smi in unexpected locations. Mitigate by checking multiple paths and allowing manual override.

2. **psutil installation**: Some systems may have issues installing psutil. Mitigate by making it a soft dependency with graceful fallback.

3. **Docker daemon detection**: Various error conditions from Docker daemon. Mitigate by catching all exceptions and providing clear guidance.

4. **WSL detection edge cases**: Some custom Linux kernels may contain "microsoft" string. Mitigate by checking multiple indicators.

5. **Performance**: Hardware detection may be slow on some systems. Mitigate by running detection once and caching results.
