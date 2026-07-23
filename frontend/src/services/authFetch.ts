/**
 * authFetch — fetch wrapper that automatically attaches the Bearer token
 * and handles 401 responses with a single token refresh retry.
 */

const STORAGE_KEY_ACCESS = 'rsai_access_token';
const STORAGE_KEY_REFRESH = 'rsai_refresh_token';

function getToken(): string | null {
  return localStorage.getItem(STORAGE_KEY_ACCESS);
}

function getRefreshToken(): string | null {
  return localStorage.getItem(STORAGE_KEY_REFRESH);
}

function clearTokens(): void {
  localStorage.removeItem(STORAGE_KEY_ACCESS);
  localStorage.removeItem(STORAGE_KEY_REFRESH);
}

async function tryRefresh(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  try {
    const res = await fetch('http://localhost:8000/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) { clearTokens(); return null; }
    const data = await res.json();
    localStorage.setItem(STORAGE_KEY_ACCESS, data.data.access_token);
    localStorage.setItem(STORAGE_KEY_REFRESH, data.data.refresh_token);
    return data.data.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

export async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, { ...options, headers });

  // If 401, try refresh once
  if (response.status === 401 && getRefreshToken()) {
    const newToken = await tryRefresh();
    if (newToken) {
      headers.set('Authorization', `Bearer ${newToken}`);
      return fetch(url, { ...options, headers });
    }
    // Refresh failed — redirect to login
    clearTokens();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }

  return response;
}

export { getToken };
