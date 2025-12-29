# Plan: Service Templates/Presets

## Summary

Add pre-defined service combination presets to the setup wizard's ServicesStep component, allowing users to quickly select common service configurations. The implementation will add a preset selection UI as the first interaction in the services step, with options for Minimal, Developer, Knowledge Base, Full Stack, and Custom presets. The approach follows the existing card-based selection patterns from ProfileStep and EnvironmentStep, keeping presets as frontend-only configuration (no backend changes needed).

## External Research

### Best Practices for Preset/Template UIs
- **Progressive disclosure**: Show presets first, then details on selection
- **Clear naming and descriptions**: Users should understand what each preset provides at a glance
- **Customization path**: Always allow modification after preset selection
- **Visual hierarchy**: Use icons/colors to differentiate preset tiers

### Relevant Patterns from Similar Projects
- Docker Desktop templates: Shows service groups with expand/collapse
- VS Code profile templates: Card grid with icons and descriptions
- Terraform modules: Preset configurations with override capability

## Patterns to Mirror

### ProfileStep Card Selection Pattern (frontend/src/components/setup/ProfileStep.tsx:10-76)
```tsx
// FROM: management-ui/frontend/src/components/setup/ProfileStep.tsx:10-39
// This is how option cards are structured:
const profiles = [
  {
    id: 'cpu',
    name: 'CPU Only',
    description: 'Run Ollama on CPU. Works everywhere but slower inference.',
    Icon: Cpu,
    color: 'text-blue-400',
  },
  // ...more profiles
];

// Selection card rendering pattern:
<Card
  key={profile.id}
  className={`cursor-pointer transition-all ${
    isSelected
      ? 'ring-2 ring-blue-500 border-blue-500'
      : 'hover:border-gray-500'
  }`}
  onClick={() => onChange(profile.id)}
>
  <div className="flex items-start gap-3">
    <Icon className={`w-6 h-6 ${profile.color} flex-shrink-0`} />
    <div>
      <h4 className="font-medium text-white">{profile.name}</h4>
      <p className="text-sm text-gray-400 mt-1">{profile.description}</p>
    </div>
  </div>
</Card>
```

### ServicesStep Component Structure (frontend/src/components/setup/ServicesStep.tsx)
```tsx
// FROM: management-ui/frontend/src/components/setup/ServicesStep.tsx:24-52
// Current component structure - presets will integrate before service groups
export const ServicesStep: React.FC<ServicesStepProps> = ({ profile, value, onChange }) => {
  const [services, setServices] = useState<ServiceInfo[]>([]);
  const [validation, setValidation] = useState<SelectionValidation | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['core_ai', 'workflow']));

  // Fetch services when profile changes
  useEffect(() => {
    const fetchServices = async () => {
      // ... fetch and set default selection
      const defaults = data
        .filter(s => s.default_enabled && s.available_for_profile && !s.required)
        .map(s => s.name);
      onChange(defaults);
    };
    fetchServices();
  }, [profile]);
  // ...
};
```

### Service Config Definition (backend/app/core/service_dependencies.py)
```python
# FROM: management-ui/backend/app/core/service_dependencies.py:9-21
# Reference for understanding service structure:
@dataclass
class ServiceConfig:
    name: str
    display_name: str
    description: str
    group: str
    dependencies: List[str] = field(default_factory=list)
    required: bool = False
    default_enabled: bool = True
    profiles: List[str] = field(default_factory=list)
    category: str = "optional"
```

### SetupWizard State Management (frontend/src/components/setup/SetupWizard.tsx:18-24)
```tsx
// FROM: management-ui/frontend/src/components/setup/SetupWizard.tsx:18-24
interface SetupConfig {
  profile: string;
  environment: string;
  secrets: Record<string, string>;
  enabled_services: string[];
}
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `management-ui/frontend/src/components/setup/presets.ts` | CREATE | Define preset configurations as TypeScript constants |
| `management-ui/frontend/src/components/setup/ServicesStep.tsx` | UPDATE | Add preset selection UI, integrate with existing service selection |
| `management-ui/frontend/src/components/setup/index.ts` | UPDATE | Export the presets if needed elsewhere |

## NOT Building

- **Backend preset storage**: Presets are simple enough to be frontend constants; no API needed
- **Preset persistence**: Not saving last-used preset preference
- **Custom preset creation/saving**: Users cannot save their own presets (v1 scope)
- **Per-profile presets**: Same presets apply regardless of GPU profile (services filter by profile)
- **Preset preview thumbnails**: No visual service topology diagrams

## Tasks

### Task 1: CREATE presets.ts with preset definitions

**Why**: Centralize preset definitions in a dedicated file for maintainability and type safety.

**Mirror**: `management-ui/frontend/src/components/setup/ProfileStep.tsx:10-39` (constant definition pattern)

**Do**:
Create `/opt/local-ai-packaged/management-ui/frontend/src/components/setup/presets.ts`:

```typescript
import { Zap, Code, BookOpen, Layers, Settings } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface ServicePreset {
  id: string;
  name: string;
  description: string;
  services: string[];  // Service names to enable
  Icon: LucideIcon;
  color: string;
  badge?: string;  // Optional badge like "Recommended"
}

// Service names must match those in backend SERVICE_CONFIGS
export const SERVICE_PRESETS: ServicePreset[] = [
  {
    id: 'minimal',
    name: 'Minimal',
    description: 'Just Ollama and Open WebUI for local AI chat. Lightweight and fast to start.',
    services: ['open-webui'],  // Ollama is profile-based, handled separately
    Icon: Zap,
    color: 'text-green-400',
  },
  {
    id: 'developer',
    name: 'Developer',
    description: 'Includes n8n workflow automation, Flowise visual builder, and Supabase backend.',
    services: [
      'open-webui',
      'flowise',
      'n8n',
      // Supabase optional services
      'auth', 'rest', 'realtime', 'storage', 'imgproxy', 'meta', 'functions', 'studio', 'supavisor',
    ],
    Icon: Code,
    color: 'text-blue-400',
    badge: 'Recommended',
  },
  {
    id: 'knowledge-base',
    name: 'Knowledge Base',
    description: 'Adds Qdrant vector DB and Neo4j graph DB for RAG and knowledge graph applications.',
    services: [
      'open-webui',
      'flowise',
      'n8n',
      'qdrant',
      'neo4j',
      // Supabase optional services
      'auth', 'rest', 'realtime', 'storage', 'imgproxy', 'meta', 'functions', 'studio', 'supavisor',
    ],
    Icon: BookOpen,
    color: 'text-purple-400',
  },
  {
    id: 'full-stack',
    name: 'Full Stack',
    description: 'Everything enabled: all databases, Langfuse observability, SearXNG search, and more.',
    services: [
      'open-webui',
      'flowise',
      'n8n',
      'qdrant',
      'neo4j',
      // Supabase optional services
      'auth', 'rest', 'realtime', 'storage', 'imgproxy', 'meta', 'functions', 'studio', 'supavisor',
      // Langfuse stack
      'langfuse-web', 'langfuse-worker',
      // Infrastructure
      'searxng',
    ],
    Icon: Layers,
    color: 'text-orange-400',
  },
  {
    id: 'custom',
    name: 'Custom',
    description: 'Start from scratch and manually select which services to run.',
    services: [],  // Empty - user selects manually
    Icon: Settings,
    color: 'text-gray-400',
  },
];

/**
 * Get services for a preset, filtering by what's available for the current profile.
 * This ensures profile-specific services (like ollama-cpu vs ollama-gpu) are handled correctly.
 */
export function getPresetServices(
  presetId: string,
  availableServices: Array<{ name: string; available_for_profile: boolean; required: boolean }>
): string[] {
  const preset = SERVICE_PRESETS.find(p => p.id === presetId);
  if (!preset || preset.id === 'custom') {
    return [];
  }

  // Filter preset services to only include those available for current profile
  const availableNames = new Set(
    availableServices
      .filter(s => s.available_for_profile && !s.required)
      .map(s => s.name)
  );

  return preset.services.filter(name => availableNames.has(name));
}
```

**Don't**:
- Include profile-specific services (ollama-cpu, ollama-gpu) in presets - they're handled by profile selection
- Include required services - they're always included automatically
- Add backend dependencies to presets - the validation system handles those

**Verify**: `cd /opt/local-ai-packaged/management-ui/frontend && npm run build 2>&1 | head -50`

---

### Task 2: UPDATE ServicesStep.tsx to add preset selection UI

**Why**: Integrate preset selection as the primary interaction before individual service selection.

**Mirror**:
- Card grid from `ProfileStep.tsx:49-74`
- State management from `ServicesStep.tsx:24-52`

**Do**:
Update `/opt/local-ai-packaged/management-ui/frontend/src/components/setup/ServicesStep.tsx`:

1. Add imports for presets:
```typescript
import { SERVICE_PRESETS, getPresetServices, type ServicePreset } from './presets';
import { Card } from '../common/Card';
import { Pencil } from 'lucide-react';
```

2. Add state for selected preset and customization mode:
```typescript
const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
const [isCustomizing, setIsCustomizing] = useState(false);
```

3. Add preset selection handler:
```typescript
const handlePresetSelect = (presetId: string) => {
  setSelectedPreset(presetId);

  if (presetId === 'custom') {
    setIsCustomizing(true);
    // Start with nothing selected for custom
    onChange([]);
  } else {
    setIsCustomizing(false);
    // Apply preset services
    const presetServices = getPresetServices(presetId, services);
    onChange(presetServices);
  }
};

const handleCustomize = () => {
  setIsCustomizing(true);
  // Keep current selection when customizing
};
```

4. Add preset selection UI before service groups. Structure the component as:
   - If no preset selected: Show preset cards grid
   - If preset selected and not customizing: Show preset summary with "Customize" button
   - If customizing or preset is 'custom': Show existing service groups

5. Add UI sections:

**Preset Selection Grid** (when no preset or selecting):
```tsx
{!selectedPreset && (
  <div className="mb-6">
    <h3 className="text-lg font-semibold text-white mb-2">Choose a Configuration</h3>
    <p className="text-gray-400 mb-4">
      Select a preset or customize your own service selection.
    </p>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {SERVICE_PRESETS.map((preset) => {
        const Icon = preset.Icon;
        return (
          <Card
            key={preset.id}
            className={`cursor-pointer transition-all hover:border-gray-500`}
            onClick={() => handlePresetSelect(preset.id)}
          >
            <div className="flex items-start gap-3">
              <Icon className={`w-6 h-6 ${preset.color} flex-shrink-0`} />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="font-medium text-white">{preset.name}</h4>
                  {preset.badge && (
                    <span className="text-xs px-1.5 py-0.5 bg-blue-900/50 text-blue-400 rounded">
                      {preset.badge}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-400 mt-1">{preset.description}</p>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  </div>
)}
```

**Preset Summary** (when preset selected and not customizing):
```tsx
{selectedPreset && selectedPreset !== 'custom' && !isCustomizing && (
  <div className="mb-6">
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <button
          onClick={() => setSelectedPreset(null)}
          className="text-sm text-blue-400 hover:text-blue-300"
        >
          Change preset
        </button>
      </div>
      <button
        onClick={handleCustomize}
        className="flex items-center gap-1 text-sm text-gray-400 hover:text-white"
      >
        <Pencil className="w-4 h-4" />
        Customize
      </button>
    </div>

    {(() => {
      const preset = SERVICE_PRESETS.find(p => p.id === selectedPreset);
      if (!preset) return null;
      const Icon = preset.Icon;
      return (
        <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
          <div className="flex items-center gap-3 mb-3">
            <Icon className={`w-6 h-6 ${preset.color}`} />
            <div>
              <h4 className="font-medium text-white">{preset.name} Configuration</h4>
              <p className="text-sm text-gray-400">{preset.description}</p>
            </div>
          </div>
          <div className="text-sm text-gray-400">
            <span className="text-white font-medium">{value.length}</span> services selected
            {validation?.auto_enabled && Object.keys(validation.auto_enabled).length > 0 && (
              <span className="ml-2">
                + <span className="text-purple-400">{Object.keys(validation.auto_enabled).length}</span> dependencies
              </span>
            )}
          </div>
        </div>
      );
    })()}
  </div>
)}
```

**Service Groups** (only show when customizing):
```tsx
{(isCustomizing || selectedPreset === 'custom') && (
  <>
    <h3 className="text-lg font-semibold text-white mb-2">
      {selectedPreset === 'custom' ? 'Select Services' : 'Customize Services'}
    </h3>
    <p className="text-gray-400 mb-4">
      {selectedPreset === 'custom'
        ? 'Choose which services to run. Dependencies are automatically included.'
        : 'Modify the preset selection. Dependencies are automatically included.'}
    </p>

    {/* Existing validation warnings, auto-enabled info, and service groups */}
    {/* ... keep all existing service group rendering code ... */}
  </>
)}
```

6. Update the useEffect that sets defaults to not override preset selections:
```typescript
useEffect(() => {
  const fetchServices = async () => {
    setLoading(true);
    try {
      const data = await setupApi.getServices(profile);
      setServices(data);

      // Only set defaults if no preset is selected
      if (!selectedPreset) {
        const defaults = data
          .filter(s => s.default_enabled && s.available_for_profile && !s.required)
          .map(s => s.name);
        onChange(defaults);
      } else if (selectedPreset !== 'custom') {
        // Re-apply preset with new profile
        const presetServices = getPresetServices(selectedPreset, data);
        onChange(presetServices);
      }
    } catch (error) {
      console.error('Failed to fetch services:', error);
    } finally {
      setLoading(false);
    }
  };
  fetchServices();
}, [profile, selectedPreset]);
```

**Don't**:
- Remove existing service group rendering code - it's used in customization mode
- Change the validation or auto-enable logic
- Modify the parent component's state management

**Verify**: `cd /opt/local-ai-packaged/management-ui/frontend && npm run build`

---

### Task 3: UPDATE index.ts to export presets

**Why**: Make preset types and constants available for potential use in other components.

**Mirror**: `management-ui/frontend/src/components/setup/index.ts`

**Do**:
Update `/opt/local-ai-packaged/management-ui/frontend/src/components/setup/index.ts`:

```typescript
export { ProfileStep } from './ProfileStep';
export { EnvironmentStep } from './EnvironmentStep';
export { SecretsStep } from './SecretsStep';
export { ConfirmStep } from './ConfirmStep';
export { SetupWizard } from './SetupWizard';
export { SERVICE_PRESETS, getPresetServices } from './presets';
export type { ServicePreset } from './presets';
```

**Don't**:
- Export ServicesStep directly (it's not exported currently)

**Verify**: `cd /opt/local-ai-packaged/management-ui/frontend && npm run build`

---

## Validation Strategy

### Automated Checks
- [ ] `cd /opt/local-ai-packaged/management-ui/frontend && npm run lint` - No lint errors
- [ ] `cd /opt/local-ai-packaged/management-ui/frontend && npm run build` - Build succeeds (includes TypeScript check)

### New Tests to Write

No unit tests are required for this feature because:
1. The project has no existing test framework set up (no test scripts in package.json)
2. The presets are static configuration data
3. The UI changes integrate with existing tested components

If tests are added in the future, consider:
| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `presets.test.ts` | `getPresetServices filters by available` | Preset services are correctly filtered |
| `presets.test.ts` | `all preset service names are valid` | No typos in service names |
| `ServicesStep.test.tsx` | `preset selection updates services` | UI state management works |

### Manual/E2E Validation

1. Start the management UI dev server:
```bash
cd /opt/local-ai-packaged/management-ui/frontend && npm run dev
```

2. Navigate to the setup wizard (may need to clear setup state)

3. Proceed to the Services step and verify:
   - [ ] Preset cards are displayed in a 2-column grid
   - [ ] Each preset shows icon, name, description
   - [ ] "Developer" preset shows "Recommended" badge
   - [ ] Clicking a preset selects it and updates service count
   - [ ] "Change preset" link appears after selection
   - [ ] "Customize" button opens service group view
   - [ ] "Custom" preset goes directly to service groups
   - [ ] Service count in summary matches selected services

4. Test preset service counts:
   - [ ] Minimal: ~1 service (open-webui)
   - [ ] Developer: ~10+ services (including Supabase)
   - [ ] Knowledge Base: ~12+ services (adds Qdrant, Neo4j)
   - [ ] Full Stack: ~15+ services (adds Langfuse, SearXNG)

5. Test profile interaction:
   - [ ] Go back to Profile step, change profile
   - [ ] Return to Services - preset should still be selected
   - [ ] Service count may adjust based on profile availability

### Edge Cases

- [ ] **Empty services list**: If API fails, show loading/error state
- [ ] **Profile change during preset**: Services re-filter correctly
- [ ] **Back/forward navigation**: Preset selection persists
- [ ] **Customizing then changing preset**: Selection resets to new preset

### Regression Check

- [ ] Existing wizard flow still works end-to-end
- [ ] Can complete setup with each preset
- [ ] Services start correctly based on selection
- [ ] Validation warnings still appear for missing dependencies

## Risks

1. **Service name mismatches**: Preset service names must exactly match `SERVICE_CONFIGS` keys in backend. Validate by checking `service_dependencies.py`.

2. **Profile-specific services**: Some services only appear for certain profiles (ollama-cpu vs ollama-gpu). The `getPresetServices` function handles this by filtering.

3. **Supabase required services**: Core Supabase services (vector, db, analytics, kong) are always required. Presets should not include these as they're auto-included.

4. **State persistence**: The wizard's `config.enabled_services` state should correctly reflect preset selections. Test by checking the ConfirmStep summary.
