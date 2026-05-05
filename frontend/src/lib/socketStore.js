import { io } from "socket.io-client";
import { writable } from "svelte/store";

const normalizeOrigin = (value) => (value ? value.replace(/\/+$/, '') : '');
const resolveBackendOrigin = () => {
  const envOrigin = normalizeOrigin(
    import.meta.env.VITE_BACKEND_ORIGIN ||
    import.meta.env.VITE_BACKEND_URL ||
    ''
  );

  if (envOrigin) return envOrigin;
  if (typeof window === 'undefined') return '';

  if (import.meta.env.DEV) {
    const host = window.location.hostname || 'localhost';
    return `http://${host}:5000`;
  }

  return window.location.origin;
};

export const backendOrigin = resolveBackendOrigin();

export const socket = io(backendOrigin || undefined, {
  transports: ["websocket", "polling"],
  reconnection: true,
  autoConnect: false,
});

export const status = writable("Offline");
export const telemetry = writable({ fps: 0, latency: 0, bitrate: 0 });
export const messages = writable([]);

const MAX_MESSAGES = 200;

export const nowTs = () =>
  new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

export const appendMessage = (message) => {
  messages.update(msgs => [...msgs, message].slice(-MAX_MESSAGES));
};

export const initSocket = () => {
  socket.on("connect", () => status.set("Online"));
  socket.on("disconnect", () => status.set("Offline"));
  socket.on("connect_error", () => status.set("Offline"));
  socket.on("telemetry", (data) => telemetry.set(data));
  socket.on("log", (entry) => {
    if (!entry || !entry.text) return;
    const text = entry.text.trim();
    if (!text) return;

    const level = (entry.level || "").toLowerCase();
    const cls = entry.cls || (level === "error" ? "error" : level === "warning" ? "warn" : "system");
    appendMessage({ text, source: entry.source || "", cls, ts: entry.ts || nowTs() });
  });

  socket.connect();
  status.set(socket.connected ? "Online" : "Offline");
};

export const disconnectSocket = () => {
  socket.removeAllListeners();
  socket.disconnect();
};

export const sendMove = (dir) => socket.emit("move", { direction: dir });
export const sendAction = (type, action) => socket.emit("action", { type, action });

export const sendShellCommand = (command) => {
  if (!command) return;
  socket.emit("shell_command", { command });
  appendMessage({ text: `$ ${command}`, cls: "user", ts: nowTs() });
};
export const sendPowerOff = () => {
  socket.emit("power_off");
  appendMessage({ text: "Power off requested", cls: "warn", ts: nowTs() });
};
