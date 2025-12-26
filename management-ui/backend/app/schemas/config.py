from pydantic import BaseModel
from typing import Dict, List, Optional, Any


class ConfigVariable(BaseModel):
    name: str
    value: str
    category: str
    is_secret: bool
    is_required: bool
    description: str
    validation_regex: Optional[str] = None
    has_error: bool = False
    error_message: Optional[str] = None


class ConfigSchema(BaseModel):
    variables: Dict[str, Dict[str, Any]]
    categories: Dict[str, List[str]]


class ConfigResponse(BaseModel):
    config: Dict[str, str]
    schema_info: Dict[str, Dict[str, Any]]
    categories: Dict[str, List[str]]
    validation_errors: List[Dict]


class ConfigUpdateRequest(BaseModel):
    config: Dict[str, str]


class ConfigValidationResponse(BaseModel):
    valid: bool
    errors: List[Dict]


class SecretGenerationResponse(BaseModel):
    secrets: Dict[str, str]
    generated_count: int


class BackupInfo(BaseModel):
    filename: str
    path: str
    created: str


class BackupListResponse(BaseModel):
    backups: List[BackupInfo]


class RestoreRequest(BaseModel):
    filename: str


class MessageResponse(BaseModel):
    message: str
    backup_path: Optional[str] = None
