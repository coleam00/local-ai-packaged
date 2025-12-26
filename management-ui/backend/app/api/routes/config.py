from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from typing import Dict

from ...schemas.config import (
    ConfigResponse, ConfigUpdateRequest, ConfigValidationResponse,
    SecretGenerationResponse, BackupListResponse, BackupInfo,
    RestoreRequest, MessageResponse
)
from ...core.env_manager import EnvManager, ENV_SCHEMA
from ...core.secret_generator import generate_all_secrets, generate_missing_secrets
from ..deps import get_env_manager, get_current_user

router = APIRouter()


@router.get("", response_model=ConfigResponse)
async def get_config(
    env_manager: EnvManager = Depends(get_env_manager),
    _: dict = Depends(get_current_user)
):
    """Get current configuration with masked secrets."""
    config = env_manager.get_masked()
    raw_config = env_manager.load()
    errors = env_manager.validate(raw_config)

    return ConfigResponse(
        config=config,
        schema_info=ENV_SCHEMA,
        categories=env_manager.get_categories(),
        validation_errors=errors
    )


@router.get("/raw", response_model=Dict[str, str])
async def get_raw_config(
    env_manager: EnvManager = Depends(get_env_manager),
    _: dict = Depends(get_current_user)
):
    """Get raw configuration (secrets not masked). Use with caution."""
    return env_manager.load()


@router.put("", response_model=MessageResponse)
async def update_config(
    request: ConfigUpdateRequest,
    env_manager: EnvManager = Depends(get_env_manager),
    _: dict = Depends(get_current_user)
):
    """Update configuration."""
    # Validate first
    errors = env_manager.validate(request.config)
    if errors:
        # Still allow save but warn
        pass

    backup_path = env_manager.save(request.config, backup=True)

    return MessageResponse(
        message="Configuration saved successfully",
        backup_path=backup_path
    )


@router.post("/validate", response_model=ConfigValidationResponse)
async def validate_config(
    request: ConfigUpdateRequest,
    env_manager: EnvManager = Depends(get_env_manager),
    _: dict = Depends(get_current_user)
):
    """Validate configuration without saving."""
    errors = env_manager.validate(request.config)
    return ConfigValidationResponse(valid=len(errors) == 0, errors=errors)


@router.post("/generate-secrets", response_model=SecretGenerationResponse)
async def generate_secrets(
    only_missing: bool = True,
    env_manager: EnvManager = Depends(get_env_manager),
    _: dict = Depends(get_current_user)
):
    """Generate secure secrets."""
    if only_missing:
        current = env_manager.load()
        secrets = generate_missing_secrets(current)
    else:
        secrets = generate_all_secrets()

    return SecretGenerationResponse(
        secrets=secrets,
        generated_count=len(secrets)
    )


@router.get("/backups", response_model=BackupListResponse)
async def list_backups(
    env_manager: EnvManager = Depends(get_env_manager),
    _: dict = Depends(get_current_user)
):
    """List available configuration backups."""
    backups = env_manager.list_backups()
    return BackupListResponse(backups=[BackupInfo(**b) for b in backups])


@router.post("/restore", response_model=MessageResponse)
async def restore_backup(
    request: RestoreRequest,
    env_manager: EnvManager = Depends(get_env_manager),
    _: dict = Depends(get_current_user)
):
    """Restore configuration from a backup."""
    try:
        env_manager.restore_backup(request.filename)
        return MessageResponse(message=f"Restored from {request.filename}")
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup {request.filename} not found"
        )


@router.get("/download")
async def download_config(
    env_manager: EnvManager = Depends(get_env_manager),
    _: dict = Depends(get_current_user)
):
    """Download current .env file."""
    if not env_manager.env_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No configuration file found"
        )
    return FileResponse(
        env_manager.env_file,
        filename=".env",
        media_type="text/plain"
    )


@router.get("/schema")
async def get_schema(
    env_manager: EnvManager = Depends(get_env_manager),
    _: dict = Depends(get_current_user)
):
    """Get configuration schema."""
    return {
        "schema": ENV_SCHEMA,
        "categories": env_manager.get_categories()
    }
