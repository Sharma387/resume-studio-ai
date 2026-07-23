/**
 * authDownload — download a file using authFetch and trigger browser download.
 * Works around the limitation that anchor tags (<a href download>) don't send auth headers.
 */

import { authFetch } from './authFetch';

export async function authDownload(url: string, filename: string = 'download'): Promise<void> {
  const response = await authFetch(url);

  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);

  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);

  // Release the blob URL after a short delay to ensure the download starts
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}
