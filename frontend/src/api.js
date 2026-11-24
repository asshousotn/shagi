const envBase = import.meta.env.VITE_API_URL;
const API_BASE =
  envBase ||
  (window.location.port === "8011"
    ? `${window.location.protocol}//${window.location.hostname}:8010/api`
    : "/api");

export function uuid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
    const value = (Math.random() * 16) | 0;
    const digit = char === "x" ? value : (value & 0x3) | 0x8;
    return digit.toString(16);
  });
}

export function sessionId() {
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = uuid();
    localStorage.setItem("session_id", id);
  }
  return id;
}

function headers(extra = {}) {
  const result = { "X-Session-Id": sessionId(), ...extra };
  const token = localStorage.getItem("token");
  if (token) result.Authorization = `Bearer ${token}`;
  return result;
}

export async function api(path, options = {}) {
  const init = { ...options, headers: headers(options.headers || {}) };
  if (options.body && !(options.body instanceof FormData)) {
    init.headers["Content-Type"] = "application/json";
  }
  const response = await fetch(API_BASE + path, init);
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!response.ok) {
    const detail = Array.isArray(data?.detail)
      ? data.detail.map((item) => item.msg).join(", ")
      : data?.detail;
    throw new Error(detail || `Ошибка ${response.status}`);
  }
  return data;
}

export function assetUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//.test(path)) return path;
  return API_BASE.replace(/\/api$/, "") + path;
}

export async function track(type, payload) {
  const body = JSON.stringify({ type, ...payload });
  try {
    const response = await fetch(API_BASE + "/events", {
      method: "POST",
      headers: headers({ "Content-Type": "application/json" }),
      body,
      keepalive: true
    });
    if (!response.ok) throw new Error("event");
  } catch {
    const queue = JSON.parse(localStorage.getItem("event_queue") || "[]");
    queue.push({ type, ...payload });
    localStorage.setItem("event_queue", JSON.stringify(queue));
  }
}

export async function flushEvents() {
  const queue = JSON.parse(localStorage.getItem("event_queue") || "[]");
  if (!queue.length) return;
  localStorage.removeItem("event_queue");
  for (const event of queue) {
    await track(event.type, event);
  }
}
