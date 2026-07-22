import type { Resume } from '../types/resume';

const API_URL = 'http://localhost:8000/api/v1';

export interface ResumeResponse {
  success: boolean;
  data: Resume;
}

export async function fetchResume(id: string): Promise<ResumeResponse> {
  const res = await fetch(`${API_URL}/resume/${id}`);
  if (!res.ok) throw new Error('Resume not found');
  return res.json();
}

export async function saveResume(id: string, resume: Resume): Promise<ResumeResponse> {
  const res = await fetch(`${API_URL}/resume/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(resume),
  });
  if (!res.ok) throw new Error('Failed to save resume');
  return res.json();
}

export interface PdfGenerateResponse {
  success: boolean;
  downloadUrl: string;
}

export async function generatePdf(id: string): Promise<PdfGenerateResponse> {
  const res = await fetch(`${API_URL}/resume/${id}/pdf`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to generate PDF');
  return res.json();
}

export interface SuggestionResponse {
  success: boolean;
  data: {
    original: Resume;
    modified: Resume;
  };
}

export interface ApplySuggestionResponse {
  success: boolean;
  data: {
    version: import('../types/version').ResumeVersion;
    resume: Resume;
  };
}

export interface VersionsResponse {
  success: boolean;
  data: import('../types/version').ResumeVersion[];
}

export interface VersionResponse {
  success: boolean;
  data: import('../types/version').ResumeVersion;
}

export async function previewSuggestion(
  id: string,
  section: string,
  message: string,
  suggestion?: string,
): Promise<SuggestionResponse> {
  const res = await fetch(`${API_URL}/resume/${id}/preview-suggestion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ section, priority: 'medium', message, suggestion }),
  });
  if (!res.ok) throw new Error('Preview failed');
  return res.json();
}

export async function applySuggestion(
  id: string,
  section: string,
  message: string,
  suggestion?: string,
): Promise<ApplySuggestionResponse> {
  const res = await fetch(`${API_URL}/resume/${id}/apply-suggestion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ section, priority: 'medium', message, suggestion }),
  });
  if (!res.ok) throw new Error('Apply failed');
  return res.json();
}

export async function fetchVersions(id: string): Promise<VersionsResponse> {
  const res = await fetch(`${API_URL}/resume/${id}/versions`);
  if (!res.ok) throw new Error('Failed to fetch versions');
  return res.json();
}

export async function restoreVersion(id: string, versionId: string): Promise<VersionResponse> {
  const res = await fetch(`${API_URL}/resume/${id}/versions/${versionId}/restore`, { method: 'POST' });
  if (!res.ok) throw new Error('Restore failed');
  return res.json();
}

export function getPdfDownloadUrl(id: string): string {
  return `${API_URL}/resume/${id}/pdf/download`;
}

export interface MatchResponse {
  success: boolean;
  data: import('../types/match').MatchResult;
}

export async function matchResume(id: string, description: string, jobTitle?: string): Promise<MatchResponse> {
  const res = await fetch(`${API_URL}/job-match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume_id: id, job_title: jobTitle || null, description }),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Match analysis failed');
  }
  return res.json();
}
