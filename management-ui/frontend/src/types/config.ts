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
