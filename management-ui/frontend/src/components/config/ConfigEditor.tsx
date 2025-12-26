import { useState } from 'react';
import { Save, RotateCcw, Key, Download, AlertCircle } from 'lucide-react';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
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
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerateSecrets = async () => {
    setIsGenerating(true);
    try {
      const result = await configApi.generateSecrets(true);
      if (result.generated_count > 0) {
        setGeneratedSecrets(result.secrets);
      } else {
        alert('All secrets are already configured!');
      }
    } catch (error) {
      console.error('Failed to generate secrets:', error);
    } finally {
      setIsGenerating(false);
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

  // Format category name
  const formatCategoryName = (cat: string) => {
    return cat.charAt(0).toUpperCase() + cat.slice(1).replace(/_/g, ' ');
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        {/* Action Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-gray-800 rounded-lg">
          <div className="flex items-center gap-3">
            <Button
              variant="primary"
              onClick={handleSave}
              disabled={!hasChanges || isSaving}
              isLoading={isSaving}
            >
              <Save className="w-4 h-4 mr-2" />
              Save Changes
            </Button>
            {hasChanges && (
              <Button variant="ghost" onClick={resetChanges}>
                <RotateCcw className="w-4 h-4 mr-2" />
                Reset
              </Button>
            )}
          </div>
          <Button
            variant="secondary"
            onClick={handleGenerateSecrets}
            disabled={isGenerating}
            isLoading={isGenerating}
          >
            <Key className="w-4 h-4 mr-2" />
            Generate Missing Secrets
          </Button>
        </div>

        {/* Unsaved changes warning */}
        {hasChanges && (
          <div className="flex items-center gap-3 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
            <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0" />
            <p className="text-yellow-400 text-sm">
              You have unsaved changes. Don't forget to save before leaving.
            </p>
          </div>
        )}

        {/* Generated Secrets Preview */}
        {generatedSecrets && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
            <h4 className="font-medium text-green-400 mb-2 flex items-center gap-2">
              <Key className="w-4 h-4" />
              Generated Secrets Preview
            </h4>
            <p className="text-sm text-gray-300 mb-3">
              {Object.keys(generatedSecrets).length} secrets generated. Review and apply:
            </p>
            <div className="space-y-1 text-sm font-mono bg-gray-900 p-3 rounded max-h-40 overflow-y-auto">
              {Object.entries(generatedSecrets).map(([key, value]) => (
                <div key={key} className="flex">
                  <span className="text-gray-400">{key}=</span>
                  <span className="text-green-400 truncate">{value.substring(0, 30)}...</span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex gap-3">
              <Button variant="primary" onClick={handleApplySecrets}>
                Apply All
              </Button>
              <Button variant="ghost" onClick={() => setGeneratedSecrets(null)}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Config Sections */}
        {Object.entries(categories).map(([category, vars]) => (
          <ConfigSection
            key={category}
            title={formatCategoryName(category)}
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

        <Card>
          <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
            <Download className="w-4 h-4 text-gray-400" />
            Download
          </h4>
          <a
            href={configApi.getDownloadUrl()}
            download=".env"
            className="block w-full text-center px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            Download .env
          </a>
        </Card>

        {/* Validation Summary */}
        {validationErrors.length > 0 && (
          <Card>
            <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400" />
              Validation Issues
            </h4>
            <ul className="space-y-2">
              {validationErrors.map((error, idx) => (
                <li
                  key={idx}
                  className="text-sm p-2 bg-red-500/10 border border-red-500/20 rounded"
                >
                  <span className="font-medium text-red-400">{error.variable}</span>
                  <p className="text-gray-400">{error.message}</p>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
};
