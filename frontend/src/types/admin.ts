export interface AdminDashboard {
  version: string;
  environment: string;
  storage_backend: string;
  ai_provider: string;
  ai_model: string;
  ai_connected: boolean;
  database_connected: boolean;
  migration: string | null;
  uptime_seconds: number;
  table_counts: Record<string, number>;
}

export interface AiConfig {
  endpoint: string;
  model: string;
  timeout: number;
  max_retries: number;
  mock_allowed: boolean;
  key_configured: boolean;
  connectivity: {
    provider: string;
    configured_endpoint: string;
    configured_model: string;
    reachable: boolean;
    mock_mode: boolean;
  };
}

export interface AiTestResult {
  endpoint: string;
  model: string;
  reachable: boolean;
  response_time_ms: number | null;
  http_status: number | null;
  error: string | null;
  retry_count: number;
  content?: string;
}

export interface DiscoveredModel {
  id: string;
  object: string;
  owned_by: string;
}

export interface AdminConfig {
  app_name: string;
  app_version: string;
  debug: boolean;
  storage_backend: string;
  database_url: string;
  omniroute_api_url: string;
  omniroute_api_key_configured: boolean;
  omniroute_model: string;
  omniroute_timeout: number;
  omniroute_max_retries: number;
  allow_mock_ai_data: boolean;
  jwt_access_expire_minutes: number;
  jwt_refresh_expire_days: number;
  db_pool_size: number;
  db_max_overflow: number;
  db_pool_timeout: number;
}

export interface DatabaseStatus {
  backend: string;
  migration: string | null;
  table_counts: Record<string, number | null>;
  pool: {
    size: number;
    overflow: number;
    timeout: number;
  };
}

export interface StorageStatus {
  backend: string;
  json_files: number;
  dir_counts: Record<string, number>;
  migrated: boolean;
}

export interface FeatureFlags {
  debug: boolean;
  allow_mock_ai_data: boolean;
  storage_backend: string;
  ai_enabled: boolean;
  database_enabled: boolean;
  mock_mode: boolean;
}

export interface SystemHealthSection {
  status: 'healthy' | 'warning' | 'critical';
  [key: string]: unknown;
}

export interface SystemHealth {
  application: SystemHealthSection;
  ai: SystemHealthSection;
  database: SystemHealthSection;
  storage: SystemHealthSection;
}

export interface AiParseSnippetResult {
  success: boolean;
  latency_ms: number | null;
  error: string | null;
  parsed: {
    name: string | null;
    email: string | null;
    skills_count: number | null;
    experience_count: number | null;
  } | null;
}

export interface ParseTestResult {
  latency_ms: number | null;
  success: boolean;
  error: string | null;
  parsed_resume: Record<string, unknown> | null;
}

export interface DatabaseValidation {
  valid: boolean;
  checks: Array<{
    name: string;
    status: 'ok' | 'warn' | 'error';
    detail?: string;
  }>;
}
