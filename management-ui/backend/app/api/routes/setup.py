from fastapi import APIRouter, Depends, Body
from ...schemas.setup import (
    SetupStatusResponse, SetupConfigRequest, SetupProgressResponse,
    ServiceSelectionInfo, ServiceSelectionValidation
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
    _: dict = Depends(get_current_user)
):
    """Run the complete setup process."""
    result = await setup_service.run_full_setup(config)
    return result
