// src/api/authService.ts
import apiClient from './client';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AuthTokens {
  accessToken: string;
  refreshToken?: string;
}

export interface SignUpPayload {
  name: string;
  email: string;
  password: string;
}

export interface SignInPayload {
  email: string;
  password: string;
}

// ── Sign Up ───────────────────────────────────────────────────────────────────
// POST /api/auth/register
export async function signUp(payload: SignUpPayload): Promise<AuthTokens> {
  const { data } = await apiClient.post<AuthTokens>('/api/auth/register', payload);
  return data;
}

// Sign In 
// POST /api/auth/login
export async function signIn(payload: SignInPayload): Promise<AuthTokens> {
  const { data } = await apiClient.post<AuthTokens>('/api/auth/login', payload);
  return data;
}

// Sign Out
// POST /api/auth/logout
export async function signOut(): Promise<void> {
  await apiClient.post('/api/auth/logout');
}

// Forgot Password 
// POST /api/auth/forgot-password
export async function sendPasswordResetEmail(email: string): Promise<void> {
  await apiClient.post('/api/auth/forgot-password', { email });
}

// Verify Code 
// POST /api/auth/verify-code
export async function verifyResetCode(email: string, code: string): Promise<void> {
  await apiClient.post('/api/auth/verify-code', { email, code });
}

// Reset Password 
// POST /api/auth/reset-password
export async function resetPassword(
  email: string,
  code: string,
  newPassword: string
): Promise<void> {
  await apiClient.post('/api/auth/reset-password', { email, code, newPassword });
}