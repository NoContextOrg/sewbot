<script>
  import { io } from "socket.io-client";
  import { onMount } from "svelte";
  import SewbotDashboard from "./lib/SewbotDashboard.svelte";

  const backendOrigin =
    import.meta.env.VITE_BACKEND_ORIGIN ||
    import.meta.env.VITE_BACKEND_URL ||
    '/api/v1';

  const socket = io(backendOrigin, {
    transports: ["websocket", "polling"],
    reconnection: true,
  });

  let status = "Offline";

  onMount(() => {
    socket.on("connect", () => {
      status = "Online";
    });

    socket.on("disconnect", () => {
      status = "Offline";
    });

    socket.on("connect_error", () => {
      status = "Offline";
    });

    return () => {
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