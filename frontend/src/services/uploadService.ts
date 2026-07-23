import type { Resume } from '../types/resume';

import API_URL from '../config';
import { authFetch, getToken } from './authFetch';

export interface UploadResult {
  success: boolean;
  filename: string;
  original_name: string;
  size: number;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percent: number;
}

export interface ExtractData {
  pages: number;
  characters: number;
  text: string;
}

export interface ExtractResult {
  success: boolean;
  data: ExtractData;
}

export async function uploadResume(
  file: File,
  onProgress?: (p: UploadProgress) => void,
): Promise<UploadResult> {
  const form = new FormData();
  form.append('file', file);

  const xhr = new XMLHttpRequest();

  const promise = new Promise<UploadResult>((resolve, reject) => {
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress({
          loaded: e.loaded,
          total: e.total,
          percent: Math.round((e.loaded / e.total) * 100),
        });
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const data = JSON.parse(xhr.responseText);
          reject(new Error(data.detail || 'Upload failed'));
        } catch {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    });

    xhr.addEventListener('error', () => reject(new Error('Network error')));
    xhr.addEventListener('abort', () => reject(new Error('Upload cancelled')));

    xhr.open('POST', `${API_URL}/upload`);
    const token = getToken();
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.send(form);
  });

  return promise;
}

export interface ParseResult {
  success: boolean;
  id?: string;
  data: Resume;
}

export async function extractResume(filename: string): Promise<ExtractResult> {
  const res = await authFetch(`${API_URL}/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Extraction failed');
  }
  return res.json();
}

export async function parseResume(text: string, filename?: string): Promise<ParseResult> {
  const res = await authFetch(`${API_URL}/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, filename }),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Parsing failed');
  }
  return res.json();
}
