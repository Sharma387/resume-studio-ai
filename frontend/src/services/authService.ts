import API_URL from '../config';

export interface LoginResponse {
  success: boolean;
  data: {
    user: { id: string; email: string; full_name: string; role: string };
    tokens: { access_token: string; refresh_token: string; token_type: string; expires_in: number };
  };
}

export interface RegisterResponse {
  success: boolean;
  data: {
    user: { id: string; email: string; full_name: string; role: string };
    tokens: { access_token: string; refresh_token: string };
  };
}

export interface TokenResponse {
  success: boolean;
  data: { access_token: string; refresh_token: string };
}

export interface UserResponse {
  success: boolean;
  data: { id: string; email: string; full_name: string; role: string };
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || data.error?.message || 'Login failed');
  }
  return res.json();
}

export async function register(email: string, password: string, full_name: string): Promise<RegisterResponse> {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name }),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || data.error?.message || 'Registration failed');
  }
  return res.json();
}

export async function refreshToken(refresh_token: string): Promise<TokenResponse> {
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token }),
  });
  if (!res.ok) throw new Error('Token refresh failed');
  return res.json();
}

export async function logout(refresh_token: string, access_token: string): Promise<void> {
  await fetch(`${API_URL}/auth/logout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${access_token}` },
    body: JSON.stringify({ refresh_token }),
  });
}

export async function getCurrentUser(access_token: string): Promise<UserResponse> {
  const res = await fetch(`${API_URL}/auth/me`, {
    headers: { 'Authorization': `Bearer ${access_token}` },
  });
  if (!res.ok) throw new Error('Failed to get user');
  return res.json();
}
