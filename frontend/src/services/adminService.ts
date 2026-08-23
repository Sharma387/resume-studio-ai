import API_URL from '../config';
import { authFetch } from './authFetch';
import type {
  AdminDashboard,
  AiConfig,
  AiTestResult,
  DiscoveredModel,
  AdminConfig,
  DatabaseStatus,
  StorageStatus,
  FeatureFlags,
  SystemHealth,
  ParseTestResult,
  DatabaseValidation,
  AiParseSnippetResult,
} from '../types/admin';

export async function fetchDashboard(): Promise<AdminDashboard> {
  const res = await authFetch(`${API_URL}/admin/dashboard`);
  const body = await res.json();
  if (!body.success) throw new Error('Failed to fetch dashboard');
  return body.data;
}

export async function fetchAiConfig(): Promise<AiConfig> {
  const res = await authFetch(`${API_URL}/admin/ai`);
  const body = await res.json();
  if (!body.success) throw new Error('Failed to fetch AI config');
  return body.data;
}

export async function testAiConnection(): Promise<AiTestResult> {
  const res = await authFetch(`${API_URL}/admin/ai/test`, { method: 'POST' });
  const body = await res.json();
  if (!body.success) throw new Error('AI test failed');
  return body.data;
}

export async function fetchModels(): Promise<DiscoveredModel[]> {
  const res = await authFetch(`${API_URL}/admin/models`);
  const body = await res.json();
  if (!body.success) throw new Error('Failed to fetch models');
  return body.data;
}

export async function fetchConfig(): Promise<AdminConfig> {
  const res = await authFetch(`${API_URL}/admin/config`);
  const body = await res.json();
  if (!body.success) throw new Error('Failed to fetch config');
  return body.data;
}

export async function fetchDatabaseStatus(): Promise<DatabaseStatus> {
  const res = await authFetch(`${API_URL}/admin/database`);
  const body = await res.json();
  if (!body.success) throw new Error('Failed to fetch database status');
  return body.data;
}

export async function validateDatabase(): Promise<DatabaseValidation> {
  const res = await authFetch(`${API_URL}/admin/database/validate`, { method: 'POST' });
  const body = await res.json();
  if (!body.success) throw new Error('Database validation failed');
  return body.data;
}

export async function fetchStorageStatus(): Promise<StorageStatus> {
  const res = await authFetch(`${API_URL}/admin/storage`);
  const body = await res.json();
  if (!body.success) throw new Error('Failed to fetch storage status');
  return body.data;
}

export async function fetchFeatures(): Promise<FeatureFlags> {
  const res = await authFetch(`${API_URL}/admin/features`);
  const body = await res.json();
  if (!body.success) throw new Error('Failed to fetch features');
  return body.data;
}

export async function updateFeature(key: string, value: unknown): Promise<FeatureFlags> {
  const res = await authFetch(`${API_URL}/admin/features`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, value }),
  });
  const body = await res.json();
  if (!body.success) throw new Error(body.detail || 'Failed to update feature');
  return body.data;
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const res = await authFetch(`${API_URL}/admin/system`);
  const body = await res.json();
  if (!body.success) throw new Error('Failed to fetch system health');
  return body.data;
}

export async function testParseResume(text: string): Promise<ParseTestResult> {
  const res = await authFetch(`${API_URL}/admin/ai/parse-test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  const body = await res.json();
  if (!body.success) throw new Error('Parse test failed');
  return body.data;
}

export async function testAiParseSnippet(): Promise<AiParseSnippetResult> {
  const res = await authFetch(`${API_URL}/admin/ai/test-parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  const body = await res.json();
  if (!body.success) throw new Error('AI parse snippet test failed');
  return body.data;
}
