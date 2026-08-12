import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, clearToken, getJson, postForm, request, setToken } from './http';

/**
 * The single point every request passes through.
 *
 * `globalThis.fetch` is stubbed directly rather than a module being mocked:
 * http.ts IS the fetch wrapper, so mocking a module inside the module under
 * test would test nothing.
 */

function respond(status: number, body: unknown = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  localStorage.clear();
  fetchMock = vi.fn().mockResolvedValue(respond(200, { ok: true }));
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

function headersOf(call: number = 0): Headers {
  return fetchMock.mock.calls[call][1].headers as Headers;
}

describe('the Authorization header', () => {
  it('is attached when a token is stored', async () => {
    // The regression this prevents: api.ts had 77 fetch sites and not one sent
    // a header, so every route P0-2 authenticated became unreachable.
    setToken('abc123');
    await getJson('/api/executive/summary');
    expect(headersOf().get('Authorization')).toBe('Bearer abc123');
  });

  it('is absent when there is no token, and the request is still made', async () => {
    // The dashboard is readable unauthenticated; only the mutating routes are not.
    await getJson('/api/executive/summary');
    expect(headersOf().get('Authorization')).toBeNull();
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it('resolves a relative path against the API base', async () => {
    await getJson('/api/executive/summary');
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/api\/executive\/summary$/);
  });
});

describe('401 and 403', () => {
  it('a 401 clears the stored token', async () => {
    // A stale token that is never cleared fails silently forever.
    setToken('stale');
    fetchMock.mockResolvedValue(respond(401, { detail: 'Not authenticated' }));
    await expect(getJson('/api/data/uploads')).rejects.toBeInstanceOf(ApiError);
    expect(localStorage.getItem('auth_token')).toBeNull();
  });

  it('a 403 does NOT clear it', async () => {
    // A permissions problem is not a session problem, and logging the user out
    // for one sends them round a login loop that cannot help.
    setToken('valid');
    fetchMock.mockResolvedValue(respond(403, { detail: 'Insufficient permissions' }));
    await expect(getJson('/api/governance/status')).rejects.toBeInstanceOf(ApiError);
    expect(localStorage.getItem('auth_token')).toBe('valid');
  });

  it('both are isUnauthorized, so a page branches on the status not the text', async () => {
    for (const status of [401, 403]) {
      fetchMock.mockResolvedValue(respond(status, { detail: 'no' }));
      const error = await getJson('/api/x').catch((e) => e) as ApiError;
      expect(error.isUnauthorized).toBe(true);
      expect(error.status).toBe(status);
    }
  });
});

describe('error detail', () => {
  it('a FastAPI {detail: ...} body surfaces as ApiError.detail', async () => {
    fetchMock.mockResolvedValue(respond(400, {
      detail: "'employees' feeds point-in-time history: history_since is required.",
    }));
    const error = await getJson('/api/data/uploads/x/commit').catch((e) => e) as ApiError;
    expect(error.detail).toContain('history_since is required');
    // and the message is the detail, so a page can render it directly
    expect(error.message).toContain('history_since is required');
  });

  it('a non-JSON body is passed through rather than becoming [object Object]', async () => {
    fetchMock.mockResolvedValue(new Response('upstream exploded', { status: 502 }));
    const error = await getJson('/api/x').catch((e) => e) as ApiError;
    expect(error.detail).toBe('upstream exploded');
  });

  it('a 2xx does not throw', async () => {
    await expect(getJson<{ ok: boolean }>('/api/x')).resolves.toEqual({ ok: true });
  });
});

describe('multipart', () => {
  it('postForm sets NO Content-Type', async () => {
    // The browser must set the multipart boundary itself. Setting the header
    // by hand produces an upload failure whose message points nowhere useful.
    const form = new FormData();
    form.append('file', new File(['a,b'], 'x.csv', { type: 'text/csv' }));
    await postForm('/api/data/uploads?table=employees', form);
    expect(headersOf().get('Content-Type')).toBeNull();
    expect(fetchMock.mock.calls[0][1].method).toBe('POST');
  });
});

describe('token storage', () => {
  it('clearToken survives storage being unavailable', () => {
    const spy = vi.spyOn(Storage.prototype, 'removeItem')
      .mockImplementation(() => { throw new Error('denied'); });
    expect(() => clearToken()).not.toThrow();
    spy.mockRestore();
  });

  it('request is exported for callers that need the raw Response', async () => {
    const response = await request('/api/x');
    expect(response.ok).toBe(true);
  });
});
