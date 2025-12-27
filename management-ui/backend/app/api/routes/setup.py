from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from ...schemas.setup import (
    SetupStatusResponse, SetupConfigRequest, SetupProgressResponse,
    ServiceSelectionInfo, ServiceSelectionValidation, StackConfigResponse
)
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
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Get current stack configuration."""
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
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Check environment state before setup."""
    return setup_service.preflight_check()


@router.post("/preflight/fix")
async def fix_preflight_issue(
    fix_type: str,
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Fix a preflight issue."""
    return setup_service.fix_preflight_issue(fix_type)


@router.get("/services", response_model=List[ServiceSelectionInfo])
async def get_available_services(
    profile: str = "cpu",
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Get available services for selection."""
    return setup_service.get_available_services(profile)


@router.post("/validate-selection", response_model=ServiceSelectionValidation)
async def validate_service_selection(
    selected: List[str] = Body(..., embed=False),
    profile: str = "cpu",
    setup_service: SetupService = Depends(get_setup_service),
    _: dict = Depends(get_current_user)
):
    """Validate a service selection and get auto-enabled dependencies."""
    result = setup_service.validate_service_selection(selected, profile)
    return ServiceSelectionValidation(**result)


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
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user)
):
    """Run the complete setup process."""
    result = await setup_service.run_full_setup(config)

    # Save stack config to database on success
    if result.status == "completed":
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
        db.add(stack_config)
        db.commit()

    return result
