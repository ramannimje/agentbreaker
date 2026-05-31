const API_BASE = "/api";

async function fetchJson(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export function getSessions() {
  return fetchJson("/sessions");
}

export function getSession(sessionId) {
  return fetchJson(`/sessions/${sessionId}`);
}

export function getSessionTrace(sessionId) {
  return fetchJson(`/sessions/${sessionId}/trace`);
}

export function createSession(payload) {
  return fetchJson("/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
