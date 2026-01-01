from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from ...schemas.setup import (
    SetupStatusResponse, SetupConfigRequest, SetupProgressResponse,
    ServiceSelectionInfo, ServiceSelectionValidation, StackConfigResponse,
    PortCheckResponse, PortValidation
)
from typing import Dict
from ...services.setup_service import SetupService
from ...core.secret_generator import generate_all_secrets
from ..deps import get_current_user
from ...config import settings
from ...database import get_db
from ...models.stack_config import StackConfig
from typing import List, Optional

router = APIRouter()


def get_setup_service() -> SetupService:
    return SetupService(settings.COMPOSE_BASE_PATH)


def get_stack_config(db: Session) -> Optional[StackConfig]:
    """Get current stack config from database."""
    return db.query(StackConfig).first()


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(
    setup_service: SetupService = Depends(get_setup_service),
    db: Session = Depends(get_db)
):
    """Check if setup is required (no auth required for this endpoint)."""
    status = setup_service.get_status()

    # Check if stack is configured in database
    stack_config = get_stack_config(db)
    status.stack_configured = stack_config is not None and stack_config.setup_completed

    # Setup is required if not configured OR if original conditions
    if not status.stack_configured:
        status.setup_required = True

    return status


@router.get("/stack-config", response_model=Optional[StackConfigResponse])
async def get_current_stack_config(
    db: Session = Depends(get_db)
):
    """Get current stack configuration (no auth - needed for dashboard filtering)."""
    config = get_stack_config(db)
    if not config:
        return None
    return StackConfigResponse(
        profile=config.profile,
        environment=config.environment,
        enabled_services=config.enabled_services,
        setup_completed=config.setup_completed
    )


@router.get("/preflight")
async def preflight_check(
    setup_service: SetupService = Depends(get_setup_service)
):
    """Check environment state before setup (no auth - used during initial setup)."""
    return setup_service.preflight_check()


@router.post("/preflight/fix")
async def fix_preflight_issue(
    fix_type: str,
    setup_service: SetupService = Depends(get_setup_service)
):
    """Fix a preflight issue (no auth - used during initial setup)."""
    return setup_service.fix_preflight_issue(fix_type)


@router.get("/services", response_model=List[ServiceSelectionInfo])
async def get_available_services(
    profile: str = "cpu",
    setup_service: SetupService = Depends(get_setup_service)
):
    """Get available services for selection (no auth - used during initial setup)."""
    return setup_service.get_available_services(profile)


@router.post("/validate-selection", response_model=ServiceSelectionValidation)
async def validate_service_selection(
    selected: List[str] = Body(..., embed=False),
    profile: str = "cpu",
    setup_service: SetupService = Depends(get_setup_service)
):
    """Validate a service selection and get auto-enabled dependencies."""
    result = setup_service.validate_service_selection(selected, profile)
    return ServiceSelectionValidation(**result)


@router.post("/generate-secrets")
async def generate_secrets_for_setup():
    """Generate all secrets for setup (no auth - used during initial setup)."""
    secrets = generate_all_secrets()
    return {"secrets": secrets}


@router.get("/check-ports", response_model=PortCheckResponse)
async def check_port_availability(
    enabled_services: str = "",  # Comma-separated list
    profile: str = "cpu",  # Selected GPU profile
    setup_service: SetupService = Depends(get_setup_service)
):
    """Check port availability for setup (no auth - used during initial setup)."""
    services = [s.strip() for s in enabled_services.split(",") if s.strip()] if enabled_services else None
    result = setup_service.check_port_availability(services, profile)
    return PortCheckResponse(**result)


@router.post("/validate-ports", response_model=PortValidation)
async def validate_port_configuration(
    port_config: Dict[str, Dict[str, int]] = Body(...),
    setup_service: SetupService = Depends(get_setup_service)
):
    """Validate custom port configuration (no auth - used during initial setup)."""
    result = setup_service.validate_port_configuration(port_config)
    return PortValidation(**result)


@router.post("/skip")
async def skip_setup(
    setup_service: SetupService = Depends(get_setup_service),
    db: Session = Depends(get_db)
):
    """Mark setup as complete without running the wizard.

    Use this when you've already configured the stack manually
    or want to skip the setup wizard entirely.
    Detects currently running services and uses those as enabled.
    """
    running_services = []

    # Get list of running service names from Docker
    try:
        containers = setup_service.docker_client.list_containers()
        running_services = [
            c["service"] for c in containers
            if c.get("status") == "running" and c.get("service")
        ]
    except Exception:
        pass  # If we can't detect, use empty list

    # Remove existing config if any
    db.query(StackConfig).delete()

    # Create config with detected running services
    stack_config = StackConfig(
        profile="cpu",
        environment="private",
        setup_completed=True
    )
    stack_config.enabled_services = running_services if running_services else []
    stack_config.port_overrides = {}
    db.add(stack_config)
    db.commit()

    return {
        "status": "skipped",
        "message": "Setup marked as complete",
        "detected_services": len(running_services)
    }


@router.post("/complete", response_model=SetupProgressResponse)
async def complete_setup(
    config: SetupConfigRequest,
    setup_service: SetupService = Depends(get_setup_service),
    db: Session = Depends(get_db)
):
    """Run the complete setup process."""
    result = await setup_service.run_full_setup(config)

    # Save stack config to database on success (both completed and config_complete)
    if result.status in ("completed", "config_complete"):
        # Get all services that should be enabled (including auto-enabled dependencies)
        validation = setup_service.validate_service_selection(
            config.enabled_services,
            config.profile.value
        )
        all_enabled = list(config.enabled_services)
        for svc_name in validation.get("auto_enabled", {}).keys():
            if svc_name not in all_enabled:
                all_enabled.append(svc_name)

        # Remove existing config if any
        db.query(StackConfig).delete()

        # Create new config
        stack_config = StackConfig(
            profile=config.profile.value,
            environment=config.environment.value,
            setup_completed=True
        )
        stack_config.enabled_services = all_enabled
        stack_config.port_overrides = config.port_overrides
        db.add(stack_config)
        db.commit()

    return result
