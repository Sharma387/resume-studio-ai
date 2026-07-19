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

export function getPdfDownloadUrl(id: string): string {
  return `${API_URL}/resume/${id}/pdf/download`;
}
