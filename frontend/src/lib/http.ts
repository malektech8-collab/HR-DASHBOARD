/**
 * The one HTTP client (P0-2 / upload UI).
 *
 * Before this, `api.ts` had 77 fetch sites and not one of them sent an
 * Authorization header, while `hooks/useGovernance.ts` had a complete auth
 * client of its own. P0-2 then put `Depends(get_current_user)` on six routes,
 * which made every one of them unreachable from the frontend — a gap that was
 * invisible precisely because the two halves lived in different files.
 *
 * So there is one client, and a structural test bans `fetch(` outside this
 * module. A second one is how the backend ended up with two ingest paths that
 * disagreed about 17 tables.
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_URL || 'http://localhost:8000';

const TOKEN_KEY = 'auth_token';

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable; the request will simply be anonymous */
  }
}

/** Thrown on any non-2xx, so a caller can branch on the status rather than
 *  on the text of a message. `isUnauthorized` is the one every page needs. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail || `API error: ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }

  get isUnauthorized(): boolean {
    return this.status === 401 || this.status === 403;
  }
}

function extractDetail(body: string): string {
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed?.detail === 'string') return parsed.detail;
    if (parsed?.detail) return JSON.stringify(parsed.detail);
  } catch {
    /* not JSON */
  }
  return body;
}

/**
 * Every request the app makes. Attaches the token when there is one, and
 * clears it on 401 so a stale token cannot keep failing silently.
 */
export async function request(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const url = path.startsWith('http') ? path : `${API_BASE_URL}${path}`;
  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    if (response.status === 401) clearToken();
    throw new ApiError(response.status, extractDetail(await response.text()));
  }
  return response;
}

export async function getJson<T>(path: string): Promise<T> {
  return (await request(path)).json() as Promise<T>;
}

export async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await request(path, {
    method: 'POST',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  return (text ? JSON.parse(text) : null) as T;
}

export async function postForm<T>(path: string, form: FormData): Promise<T> {
  // No Content-Type: the browser must set the multipart boundary itself.
  const response = await request(path, { method: 'POST', body: form });
  return response.json() as Promise<T>;
}

export async function del<T>(path: string): Promise<T> {
  const response = await request(path, { method: 'DELETE' });
  const text = await response.text();
  return (text ? JSON.parse(text) : null) as T;
}

/** The synthetic-JWT login the app already ships (`/api/governance/token`).
 *  The token layer itself is TD-006, Phase 3 hardening. */
export async function login(username: string, password: string): Promise<void> {
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);

  const response = await fetch(`${API_BASE_URL}/api/governance/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params,
  });
  if (!response.ok) {
    throw new ApiError(response.status,
      'Authentication failed. Please verify the credentials.');
  }
  setToken((await response.json()).access_token);
}
