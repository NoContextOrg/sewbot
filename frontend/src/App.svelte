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

  const handleConnect = () => {
    status = "Online";
  };

  const handleDisconnect = () => {
    status = "Offline";
  };

  const handleError = () => {
    status = "Offline";
  };

  onMount(() => {
    socket.on("connect", handleConnect);
    socket.on("disconnect", handleDisconnect);
    socket.on("connect_error", handleError);

    socket.connect();
    status = socket.connected ? "Online" : "Offline";

    return () => {
      socket.off("connect", handleConnect);
      socket.off("disconnect", handleDisconnect);
      socket.off("connect_error", handleError);
      socket.disconnect();
    };
  });

  const sendMove = (dir) => socket.emit("move", { direction: dir });

  // Keyboard Listeners
  window.onkeydown = (e) => {
    const key = e.key.toLowerCase();
    if (["w","a","s","d"].includes(key)) sendMove(key);
  };
  window.onkeyup = () => sendMove("stop");

  let messages = [];
  function handleBubble(e){
    messages = [...messages, { text: e.detail.text, cls: e.detail.cls, ts: e.detail.ts }];
  }

</script>

<SewbotDashboard {backendOrigin} {status} {sendMove} on:bubble={handleBubble}>
  <svelte:fragment slot="bubbles">
    {#each messages as m}
      <div class="bubble {m.cls}">
        <div class="msg">{m.text}</div>
        <div class="ts">{m.ts}</div>
      </div>
    {/each}
  </svelte:fragment>
</SewbotDashboard>