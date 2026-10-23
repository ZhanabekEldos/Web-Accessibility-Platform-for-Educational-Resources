// Тонкий клиент REST API. Все ошибки приводятся к ApiError с понятным сообщением.
export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let currentLang = "ru";
export const setApiLang = (lang) => { currentLang = lang; };

async function request(method, path, { body, params, signal } = {}) {
  const url = new URL("/api" + path, window.location.origin);
  url.searchParams.set("lang", currentLang);
  for (const [k, v] of Object.entries(params || {})) {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
  }
  let res;
  try {
    res = await fetch(url, {
      method,
      signal,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (e) {
    if (e.name === "AbortError") throw e;
    throw new ApiError(0, "network", "network");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = data?.error || {};
    throw new ApiError(res.status, err.code || "http_error", err.message || res.statusText, err.details);
  }
  return data;
}

export const api = {
  get: (path, params, signal) => request("GET", path, { params, signal }),
  post: (path, body, params) => request("POST", path, { body: body ?? {}, params }),
  put: (path, body) => request("PUT", path, { body }),
  patch: (path, body) => request("PATCH", path, { body }),
  del: (path, params) => request("DELETE", path, { params }),
  exportUrl: (scanId, format) => `/api/scans/${scanId}/export?format=${format}&lang=${currentLang}`,
};
