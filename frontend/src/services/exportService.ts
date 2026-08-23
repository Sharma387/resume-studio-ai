import { authFetch } from './authFetch';
import API_URL from '../config';

export type ExportFormat = 'pdf' | 'docx' | 'html';

export type SectionPlacement = {
  region?: 'main' | 'sidebar';
  order?: number;
};

export type LayoutConfigPayload = {
  mode?: 'single' | 'two_column';
  sidebar?: 'left' | 'right';
  ratio?: '30/70' | '32/68' | '35/65' | '40/60';
  gap?: 'none' | 'compact' | 'balanced' | 'wide';
  density?: 'compact' | 'normal' | 'spacious';
  sections?: Record<string, SectionPlacement>;
};

export class ExportError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

function filenameFromDisposition(disposition: string | null): string | null {
  if (!disposition) return null;
  const match = /filename="?([^";]+)"?/.exec(disposition);
  return match ? match[1] : null;
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function friendlyExportError(status: number | undefined, fallback: string): string {
  if (status === 401 || status === 403) return 'You are not authorized to export this resume.';
  if (status === 404) return 'The resume, layout, or theme could not be found.';
  if (status === 422) return 'This export format is not supported.';
  return fallback;
}

/**
 * Export a resume through the unified export API and trigger a browser
 * download using the filename from Content-Disposition when available.
 *
 * ``layoutConfig`` is optional; when omitted the API applies any persisted
 * layout customization (explicit request > persisted > engine default).
 */
export async function downloadResumeExport(
  resumeId: string,
  layoutId: string,
  themeId: string,
  format: ExportFormat,
  layoutConfig?: LayoutConfigPayload,
  autoBalance?: boolean,
): Promise<string> {
  const payload: Record<string, unknown> = { layout_id: layoutId, theme_id: themeId, format };
  if (layoutConfig) payload.layout_config = layoutConfig;
  // Auto-balance is a request-time transformation; omit when disabled so the
  // server falls back to the persisted/manual configuration.
  if (autoBalance) payload.auto_balance = true;

  const response = await authFetch(`${API_URL}/resume/${resumeId}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let detail = "We couldn't generate the export. Please try again.";
    try {
      const body = await response.json();
      if (body && typeof body.detail === 'string' && body.detail) detail = body.detail;
    } catch { /* keep default message */ }
    throw new ExportError(friendlyExportError(response.status, detail), response.status);
  }

  const blob = await response.blob();
  const filename =
    filenameFromDisposition(response.headers.get('content-disposition')) ||
    `resume-${layoutId}.${format}`;
  triggerDownload(blob, filename);
  return filename;
}
