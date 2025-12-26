# Stage 06: Configuration Management

## Summary
Add API endpoints and UI for editing .env configuration, generating secrets, and managing backups. After this stage, users can configure the stack through the UI.

## Prerequisites
- Stage 01-05 completed

## Deliverable
- Configuration API (get, update, validate, generate secrets)
- Config editor UI with sections
- Secret field masking/reveal
- Backup/restore functionality
- Validation error display

---

## Files to Create/Modify

### Backend
```
management-ui/backend/app/
├── schemas/
│   └── config.py                # NEW
└── api/routes/
    └── config.py                # NEW
```

### Frontend
```
management-ui/frontend/src/
├── api/
│   └── config.ts                # NEW
├── store/
│   └── configStore.ts           # NEW
├── components/
│   └── config/
│       ├── ConfigEditor.tsx     # NEW
│       ├── ConfigSection.tsx    # NEW
│       ├── SecretField.tsx      # NEW
│       └── BackupManager.tsx    # NEW
├── pages/
│   └── Configuration.tsx        # NEW
└── types/
    └── config.ts                # NEW
```

---

## Task 1: Create Config Schemas (Backend)

**File**: `management-ui/backend/app/schemas/config.py`

```python
from pydantic import BaseModel, Field
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
```

Update `management-ui/backend/app/schemas/__init__.py`:
```python
from .auth import *
from .service import *
from .config import *
```

---

## Task 2: Create Config Routes (Backend)

**File**: `management-ui/backend/app/api/routes/config.py`

```python
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
```

Update `management-ui/backend/app/api/routes/__init__.py`:
```python
from fastapi import APIRouter
from .auth import router as auth_router
from .services import router as services_router
from .config import router as config_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(services_router, prefix="/services", tags=["services"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
```

---

## Task 3: Create Config Types (Frontend)

**File**: `management-ui/frontend/src/types/config.ts`

```typescript
export interface ConfigVariable {
  name: string;
  value: string;
  category: string;
  is_secret: boolean;
  is_required: boolean;
  description: string;
  validation_regex?: string;
}

export interface ConfigSchema {
  [key: string]: {
    category: string;
    is_secret: boolean;
    is_required: boolean;
    description: string;
    validation_regex?: string;
    generate?: string;
  };
}

export interface ValidationError {
  variable: string;
  error: string;
  message: string;
}

export interface BackupInfo {
  filename: string;
  path: string;
  created: string;
}
```

---

## Task 4: Create Config API (Frontend)

**File**: `management-ui/frontend/src/api/config.ts`

```typescript
import { apiClient } from './client';
import { ConfigSchema, ValidationError, BackupInfo } from '../types/config';

export interface ConfigResponse {
  config: Record<string, string>;
  schema_info: ConfigSchema;
  categories: Record<string, string[]>;
  validation_errors: ValidationError[];
}

export const configApi = {
  async get(): Promise<ConfigResponse> {
    const response = await apiClient.get<ConfigResponse>('/config');
    return response.data;
  },

  async getRaw(): Promise<Record<string, string>> {
    const response = await apiClient.get<Record<string, string>>('/config/raw');
    return response.data;
  },

  async update(config: Record<string, string>): Promise<{ message: string; backup_path?: string }> {
    const response = await apiClient.put('/config', { config });
    return response.data;
  },

  async validate(config: Record<string, string>): Promise<{ valid: boolean; errors: ValidationError[] }> {
    const response = await apiClient.post('/config/validate', { config });
    return response.data;
  },

  async generateSecrets(onlyMissing: boolean = true): Promise<{ secrets: Record<string, string>; generated_count: number }> {
    const response = await apiClient.post(`/config/generate-secrets?only_missing=${onlyMissing}`);
    return response.data;
  },

  async listBackups(): Promise<{ backups: BackupInfo[] }> {
    const response = await apiClient.get('/config/backups');
    return response.data;
  },

  async restoreBackup(filename: string): Promise<{ message: string }> {
    const response = await apiClient.post('/config/restore', { filename });
    return response.data;
  },

  getDownloadUrl(): string {
    return '/api/config/download';
  },
};
```

---

## Task 5: Create Config Store (Frontend)

**File**: `management-ui/frontend/src/store/configStore.ts`

```typescript
import { create } from 'zustand';
import { configApi } from '../api/config';
import { ConfigSchema, ValidationError, BackupInfo } from '../types/config';

interface ConfigState {
  config: Record<string, string>;
  editedConfig: Record<string, string>;
  schema: ConfigSchema;
  categories: Record<string, string[]>;
  validationErrors: ValidationError[];
  backups: BackupInfo[];
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  hasChanges: boolean;

  fetchConfig: () => Promise<void>;
  fetchRawConfig: () => Promise<void>;
  updateField: (key: string, value: string) => void;
  saveConfig: () => Promise<boolean>;
  validateConfig: () => Promise<boolean>;
  generateSecrets: (onlyMissing?: boolean) => Promise<void>;
  applyGeneratedSecrets: (secrets: Record<string, string>) => void;
  fetchBackups: () => Promise<void>;
  restoreBackup: (filename: string) => Promise<boolean>;
  resetChanges: () => void;
  clearError: () => void;
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  config: {},
  editedConfig: {},
  schema: {},
  categories: {},
  validationErrors: [],
  backups: [],
  isLoading: false,
  isSaving: false,
  error: null,
  hasChanges: false,

  fetchConfig: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await configApi.get();
      set({
        config: response.config,
        editedConfig: { ...response.config },
        schema: response.schema_info,
        categories: response.categories,
        validationErrors: response.validation_errors,
        isLoading: false,
        hasChanges: false,
      });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to fetch configuration',
        isLoading: false,
      });
    }
  },

  fetchRawConfig: async () => {
    try {
      const rawConfig = await configApi.getRaw();
      set({
        config: rawConfig,
        editedConfig: { ...rawConfig },
        hasChanges: false,
      });
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to fetch raw configuration' });
    }
  },

  updateField: (key: string, value: string) => {
    const { editedConfig, config } = get();
    const newConfig = { ...editedConfig, [key]: value };
    const hasChanges = JSON.stringify(newConfig) !== JSON.stringify(config);
    set({ editedConfig: newConfig, hasChanges });
  },

  saveConfig: async () => {
    const { editedConfig } = get();
    set({ isSaving: true, error: null });
    try {
      await configApi.update(editedConfig);
      set({
        config: { ...editedConfig },
        isSaving: false,
        hasChanges: false,
      });
      return true;
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to save configuration',
        isSaving: false,
      });
      return false;
    }
  },

  validateConfig: async () => {
    const { editedConfig } = get();
    try {
      const result = await configApi.validate(editedConfig);
      set({ validationErrors: result.errors });
      return result.valid;
    } catch {
      return false;
    }
  },

  generateSecrets: async (onlyMissing = true) => {
    try {
      const result = await configApi.generateSecrets(onlyMissing);
      // Don't auto-apply, let user review first
      return result;
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to generate secrets' });
    }
  },

  applyGeneratedSecrets: (secrets: Record<string, string>) => {
    const { editedConfig } = get();
    const newConfig = { ...editedConfig, ...secrets };
    set({ editedConfig: newConfig, hasChanges: true });
  },

  fetchBackups: async () => {
    try {
      const response = await configApi.listBackups();
      set({ backups: response.backups });
    } catch (error: any) {
      console.error('Failed to fetch backups:', error);
    }
  },

  restoreBackup: async (filename: string) => {
    try {
      await configApi.restoreBackup(filename);
      await get().fetchConfig();
      return true;
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to restore backup' });
      return false;
    }
  },

  resetChanges: () => {
    const { config } = get();
    set({ editedConfig: { ...config }, hasChanges: false });
  },

  clearError: () => set({ error: null }),
}));
```

---

## Task 6: Create Config Components (Frontend)

**File**: `management-ui/frontend/src/components/config/SecretField.tsx`

```typescript
import React, { useState } from 'react';
import { Input } from '../common/Input';

interface SecretFieldProps {
  name: string;
  value: string;
  maskedValue: string;
  onChange: (value: string) => void;
  error?: string;
  description?: string;
}

export const SecretField: React.FC<SecretFieldProps> = ({
  name,
  value,
  maskedValue,
  onChange,
  error,
  description,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [showValue, setShowValue] = useState(false);

  const displayValue = isEditing ? value : maskedValue;

  return (
    <div className="mb-4">
      <label className="label flex justify-between">
        <span>{name}</span>
        {!isEditing && (
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="text-blue-600 text-sm hover:underline"
          >
            Edit
          </button>
        )}
      </label>

      {description && (
        <p className="text-xs text-gray-500 mb-1">{description}</p>
      )}

      <div className="relative">
        <input
          type={showValue ? 'text' : 'password'}
          value={displayValue}
          onChange={(e) => onChange(e.target.value)}
          disabled={!isEditing}
          className={`input pr-20 ${error ? 'border-red-500' : ''} ${!isEditing ? 'bg-gray-50' : ''}`}
        />

        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-2">
          {isEditing && (
            <>
              <button
                type="button"
                onClick={() => setShowValue(!showValue)}
                className="text-gray-500 hover:text-gray-700 text-sm"
              >
                {showValue ? 'Hide' : 'Show'}
              </button>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="text-green-600 hover:text-green-700 text-sm"
              >
                Done
              </button>
            </>
          )}
        </div>
      </div>

      {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
    </div>
  );
};
```

**File**: `management-ui/frontend/src/components/config/ConfigSection.tsx`

```typescript
import React from 'react';
import { Card } from '../common/Card';
import { Input } from '../common/Input';
import { SecretField } from './SecretField';
import { ConfigSchema, ValidationError } from '../../types/config';

interface ConfigSectionProps {
  title: string;
  variables: string[];
  config: Record<string, string>;
  maskedConfig: Record<string, string>;
  schema: ConfigSchema;
  errors: ValidationError[];
  onChange: (key: string, value: string) => void;
}

export const ConfigSection: React.FC<ConfigSectionProps> = ({
  title,
  variables,
  config,
  maskedConfig,
  schema,
  errors,
  onChange,
}) => {
  const getError = (varName: string) => {
    const error = errors.find((e) => e.variable === varName);
    return error?.message;
  };

  return (
    <Card title={title} className="mb-6">
      {variables.map((varName) => {
        const schemaInfo = schema[varName] || {};
        const isSecret = schemaInfo.is_secret;
        const value = config[varName] || '';
        const maskedValue = maskedConfig[varName] || '';
        const error = getError(varName);

        if (isSecret) {
          return (
            <SecretField
              key={varName}
              name={varName}
              value={value}
              maskedValue={maskedValue}
              onChange={(v) => onChange(varName, v)}
              error={error}
              description={schemaInfo.description}
            />
          );
        }

        return (
          <Input
            key={varName}
            label={varName}
            value={value}
            onChange={(e) => onChange(varName, e.target.value)}
            error={error}
          />
        );
      })}
    </Card>
  );
};
```

**File**: `management-ui/frontend/src/components/config/BackupManager.tsx`

```typescript
import React from 'react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { BackupInfo } from '../../types/config';

interface BackupManagerProps {
  backups: BackupInfo[];
  onRestore: (filename: string) => void;
  onRefresh: () => void;
}

export const BackupManager: React.FC<BackupManagerProps> = ({
  backups,
  onRestore,
  onRefresh,
}) => {
  return (
    <Card title="Backups">
      <div className="flex justify-between items-center mb-4">
        <p className="text-sm text-gray-600">
          {backups.length} backup(s) available
        </p>
        <Button variant="secondary" onClick={onRefresh} className="text-sm">
          Refresh
        </Button>
      </div>

      {backups.length === 0 ? (
        <p className="text-gray-500 text-sm">No backups yet</p>
      ) : (
        <ul className="space-y-2 max-h-60 overflow-y-auto">
          {backups.map((backup) => (
            <li
              key={backup.filename}
              className="flex justify-between items-center p-2 bg-gray-50 rounded"
            >
              <div>
                <p className="text-sm font-medium">{backup.filename}</p>
                <p className="text-xs text-gray-500">
                  {new Date(backup.created).toLocaleString()}
                </p>
              </div>
              <Button
                variant="secondary"
                onClick={() => onRestore(backup.filename)}
                className="text-sm"
              >
                Restore
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
};
```

**File**: `management-ui/frontend/src/components/config/ConfigEditor.tsx`

```typescript
import React, { useState } from 'react';
import { Button } from '../common/Button';
import { ConfigSection } from './ConfigSection';
import { BackupManager } from './BackupManager';
import { useConfigStore } from '../../store/configStore';
import { configApi } from '../../api/config';

export const ConfigEditor: React.FC = () => {
  const {
    config,
    editedConfig,
    schema,
    categories,
    validationErrors,
    backups,
    hasChanges,
    isSaving,
    updateField,
    saveConfig,
    validateConfig,
    fetchBackups,
    restoreBackup,
    resetChanges,
    applyGeneratedSecrets,
  } = useConfigStore();

  const [generatedSecrets, setGeneratedSecrets] = useState<Record<string, string> | null>(null);

  const handleGenerateSecrets = async () => {
    const result = await configApi.generateSecrets(true);
    if (result.generated_count > 0) {
      setGeneratedSecrets(result.secrets);
    } else {
      alert('All secrets are already configured!');
    }
  };

  const handleApplySecrets = () => {
    if (generatedSecrets) {
      applyGeneratedSecrets(generatedSecrets);
      setGeneratedSecrets(null);
    }
  };

  const handleSave = async () => {
    const isValid = await validateConfig();
    if (!isValid) {
      if (!confirm('Configuration has validation errors. Save anyway?')) {
        return;
      }
    }
    await saveConfig();
  };

  // Get all variables not in schema (custom vars)
  const customVars = Object.keys(editedConfig).filter(
    (key) => !schema[key] && !Object.values(categories).flat().includes(key)
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        {/* Action Bar */}
        <div className="flex justify-between items-center">
          <div className="flex gap-2">
            <Button
              variant="primary"
              onClick={handleSave}
              disabled={!hasChanges}
              isLoading={isSaving}
            >
              Save Changes
            </Button>
            {hasChanges && (
              <Button variant="secondary" onClick={resetChanges}>
                Reset
              </Button>
            )}
          </div>
          <Button variant="secondary" onClick={handleGenerateSecrets}>
            Generate Missing Secrets
          </Button>
        </div>

        {/* Generated Secrets Preview */}
        {generatedSecrets && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h4 className="font-medium mb-2">Generated Secrets Preview</h4>
            <p className="text-sm text-gray-600 mb-3">
              {Object.keys(generatedSecrets).length} secrets generated. Review and apply:
            </p>
            <div className="space-y-1 text-sm font-mono bg-white p-2 rounded max-h-40 overflow-y-auto">
              {Object.entries(generatedSecrets).map(([key, value]) => (
                <div key={key}>
                  <span className="text-gray-600">{key}=</span>
                  <span className="text-green-600">{value.substring(0, 20)}...</span>
                </div>
              ))}
            </div>
            <div className="mt-3 flex gap-2">
              <Button variant="primary" onClick={handleApplySecrets}>
                Apply All
              </Button>
              <Button variant="secondary" onClick={() => setGeneratedSecrets(null)}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Config Sections */}
        {Object.entries(categories).map(([category, vars]) => (
          <ConfigSection
            key={category}
            title={category.charAt(0).toUpperCase() + category.slice(1)}
            variables={vars}
            config={editedConfig}
            maskedConfig={config}
            schema={schema}
            errors={validationErrors}
            onChange={updateField}
          />
        ))}

        {/* Custom Variables */}
        {customVars.length > 0 && (
          <ConfigSection
            title="Other Variables"
            variables={customVars}
            config={editedConfig}
            maskedConfig={config}
            schema={{}}
            errors={[]}
            onChange={updateField}
          />
        )}
      </div>

      {/* Sidebar */}
      <div className="space-y-6">
        <BackupManager
          backups={backups}
          onRestore={restoreBackup}
          onRefresh={fetchBackups}
        />

        <div className="card">
          <h4 className="font-medium mb-2">Download</h4>
          <a
            href={configApi.getDownloadUrl()}
            download=".env"
            className="btn btn-secondary w-full text-center"
          >
            Download .env
          </a>
        </div>
      </div>
    </div>
  );
};
```

---

## Task 7: Create Configuration Page

**File**: `management-ui/frontend/src/pages/Configuration.tsx`

```typescript
import React, { useEffect } from 'react';
import { useConfigStore } from '../store/configStore';
import { ConfigEditor } from '../components/config/ConfigEditor';
import { Loading } from '../components/common/Loading';

export const Configuration: React.FC = () => {
  const { fetchConfig, fetchRawConfig, fetchBackups, isLoading, error, clearError } = useConfigStore();

  useEffect(() => {
    fetchConfig();
    fetchBackups();
  }, [fetchConfig, fetchBackups]);

  if (isLoading) {
    return <Loading message="Loading configuration..." />;
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Configuration</h2>
        <p className="text-gray-600">
          Manage environment variables and secrets
        </p>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 flex justify-between">
          <span>{error}</span>
          <button onClick={clearError} className="font-bold">&times;</button>
        </div>
      )}

      <ConfigEditor />
    </div>
  );
};
```

---

## Task 8: Update App Routes

Update `src/App.tsx`:
```typescript
import { Configuration } from './pages/Configuration';

// In routes:
<Route path="/config" element={<Configuration />} />
```

---

## Validation

### Test Backend API
```bash
TOKEN="your-token-here"

# Get config (masked)
curl http://localhost:9000/api/config -H "Authorization: Bearer $TOKEN" | jq

# Get raw config
curl http://localhost:9000/api/config/raw -H "Authorization: Bearer $TOKEN" | jq

# Generate secrets
curl -X POST "http://localhost:9000/api/config/generate-secrets?only_missing=true" \
  -H "Authorization: Bearer $TOKEN" | jq

# List backups
curl http://localhost:9000/api/config/backups -H "Authorization: Bearer $TOKEN" | jq
```

### Test UI
1. Navigate to Configuration page
2. View config sections
3. Click "Edit" on secret field
4. Modify a value
5. See "Save Changes" button activate
6. Click "Generate Missing Secrets"
7. Apply generated secrets
8. Save configuration
9. Verify backup was created
10. Test restore from backup

### Success Criteria
- [ ] Config page loads with all variables
- [ ] Secrets are masked by default
- [ ] Can edit and reveal secrets
- [ ] Save button activates on changes
- [ ] Reset discards unsaved changes
- [ ] Generate secrets works
- [ ] Can preview and apply generated secrets
- [ ] Backups are listed
- [ ] Can restore from backup
- [ ] Download .env works

---

## Next Stage
Proceed to `07-log-streaming.md` to add real-time log viewing.
