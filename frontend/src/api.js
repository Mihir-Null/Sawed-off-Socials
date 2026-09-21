/**
 * Tiny wrapper around fetch for the backend API.
 *
 * Every helper returns parsed JSON or throws an ApiError carrying the HTTP
 * status and the server's `detail` (a string, or for action preflight an
 * object like {message, problems: [...]}).  Components catch ApiError and
 * show `describeError(err)` to the user.
 */

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : detail?.message || `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

/** Turn any thrown value into a short human readable message. */
export function describeError(err) {
  if (err instanceof ApiError) {
    if (err.detail && typeof err.detail === 'object' && Array.isArray(err.detail.problems)) {
      return err.detail.problems.join(' • ');
    }
    if (Array.isArray(err.detail)) {
      // FastAPI validation errors
      return err.detail.map((d) => `${(d.loc || []).slice(-1)[0]}: ${d.msg}`).join('; ');
    }
    return err.message;
  }
  if (err?.name === 'TypeError') return 'Cannot reach the server. Is it running?';
  return err?.message || String(err);
}

let onUnauthorized = () => {};
/** App registers a callback so any 401 flips the UI to the login screen. */
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

async function request(path, { method = 'GET', body, form } = {}) {
  const init = { method, headers: {}, credentials: 'same-origin' };
  if (form) {
    init.body = form;
  } else if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const res = await fetch(`/api${path}`, init);
  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  if (res.status === 401) onUnauthorized();
  if (!res.ok) throw new ApiError(res.status, data?.detail ?? `HTTP ${res.status}`);
  return data;
}

export const api = {
  session: () => request('/auth/session'),
  login: (password) => request('/auth/login', { method: 'POST', body: { password } }),
  logout: () => request('/auth/logout', { method: 'POST' }),

  getDetails: () => request('/details'),
  saveDetails: (details) => request('/details', { method: 'POST', body: details }),
  upload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/upload', { method: 'POST', form });
  },
  customEmails: () => request('/custom-emails'),

  checkAction: (action) => request(`/actions/${action}/check`),
  startAction: (action) => request(`/actions/${action}`, { method: 'POST' }),
  job: (id) => request(`/jobs/${id}`),
  jobs: () => request('/jobs'),
  logs: () => request('/logs'),

  googleStatus: () => request('/google/status'),
  googleLoginUrl: () => request('/google/login'),
  googleLogout: () => request('/google/logout', { method: 'POST' }),
};
