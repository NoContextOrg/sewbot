<script>
  import { io } from "socket.io-client";
  import { onMount } from "svelte";
  import SewbotDashboard from "./lib/SewbotDashboard.svelte";

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

  const backendOrigin = resolveBackendOrigin();

  const socket = io(backendOrigin || undefined, {
    transports: ["websocket", "polling"],
    reconnection: true,
    autoConnect: false,
  });

  let status = "Offline";
  let messages = [];
  const MAX_MESSAGES = 200;

  const nowTs = () =>
    new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const appendMessage = (message) => {
    messages = [...messages, message].slice(-MAX_MESSAGES);
  };

  const handleConnect = () => {
    status = "Online";
  };

  const handleDisconnect = () => {
    status = "Offline";
  };

  const handleError = () => {
    status = "Offline";
  };

  const handleLog = (entry) => {
    if (!entry || !entry.text) return;
    const source = entry.source ? `[${entry.source}] ` : "";
    const text = `${source}${entry.text}`.trim();
    if (!text) return;

    const level = (entry.level || "").toLowerCase();
    const cls = entry.cls || (level === "error" ? "error" : level === "warning" ? "warn" : "system");
    appendMessage({ text, cls, ts: entry.ts || nowTs() });
  };

  onMount(() => {
    socket.on("connect", handleConnect);
    socket.on("disconnect", handleDisconnect);
    socket.on("connect_error", handleError);
    socket.on("log", handleLog);

    socket.connect();
    status = socket.connected ? "Online" : "Offline";

    return () => {
      socket.off("connect", handleConnect);
      socket.off("disconnect", handleDisconnect);
      socket.off("connect_error", handleError);
      socket.off("log", handleLog);
      socket.disconnect();
    };
  });

  const sendMove = (dir) => socket.emit("move", { direction: dir });

  // Keyboard Listeners
  window.onkeydown = (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
    const key = e.key.toLowerCase();
    if (["w","a","s","d"].includes(key)) sendMove(key);
  };
  window.onkeyup = (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
    sendMove("stop");
  };

  function handleBubble(e){
    appendMessage({ text: e.detail.text, cls: e.detail.cls, ts: e.detail.ts });
  }

  function handleCommand(e){
    const command = e.detail.text;
    if (!command) return;
    socket.emit("ssh_command", { command });
    appendMessage({ text: `$ ${command}`, cls: "user", ts: nowTs() });
  }

  function handlePowerOff(){
    socket.emit("power_off");
    appendMessage({ text: "Power off requested", cls: "warn", ts: nowTs() });
  }

</script>

<SewbotDashboard {backendOrigin} {status} {sendMove} on:bubble={handleBubble} on:command={handleCommand} on:poweroff={handlePowerOff}>
  <svelte:fragment slot="bubbles">
    {#each messages as m}
      <div class="bubble {m.cls}">
        <div class="msg">{m.text}</div>
        <div class="ts">{m.ts}</div>
      </div>
    {/each}
  </svelte:fragment>
</SewbotDashboard>