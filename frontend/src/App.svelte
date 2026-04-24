<script>
  import { io } from "socket.io-client";
  import { onMount } from "svelte";

  const backendOrigin =
    import.meta.env.VITE_BACKEND_ORIGIN ||
    `${window.location.protocol}//${window.location.hostname}:5000`;

  const socket = io(backendOrigin, {
    transports: ["websocket", "polling"],
    reconnection: true,
  });

  let status = "Offline";
  let feedNonce = Date.now();
  let feedError = "";

  $: feedUrl = `${backendOrigin}/video_feed?ts=${feedNonce}`;

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
  const reloadFeed = () => {
    feedError = "";
    feedNonce = Date.now();
  };

  // Keyboard Listeners
  window.onkeydown = (e) => {
    const key = e.key.toLowerCase();
    if (["w","a","s","d"].includes(key)) sendMove(key);
  };
  window.onkeyup = () => sendMove("stop");
</script>

<main class="shell">
  <h1>Controller: {status}</h1>
  <p class="meta">Backend: {backendOrigin}</p>

  <div class="feed-wrap">
    <img
      src={feedUrl}
      class="feed"
      alt="Robot camera feed"
      on:error={() => (feedError = "Video feed unavailable. Check backend and camera logs.")}
      on:load={() => (feedError = "")}
    />
  </div>

  {#if feedError}
    <p class="error">{feedError}</p>
    <button type="button" on:click={reloadFeed}>Retry feed</button>
  {/if}
</main>

<style>
  .shell {
    min-height: 100vh;
    margin: 0;
    padding: 1.2rem;
    background: #090c12;
    color: #eef2ff;
    display: grid;
    gap: 0.75rem;
    justify-items: center;
    align-content: start;
    box-sizing: border-box;
  }

  h1 {
    margin: 0.5rem 0 0;
    font-size: 1.35rem;
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }

  .meta {
    margin: 0;
    font-size: 0.8rem;
    color: #8fa2c7;
    word-break: break-all;
  }

  .feed-wrap {
    width: min(100%, 960px);
    border: 2px solid #254272;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    background: #020409;
  }

  .feed {
    display: block;
    width: 100%;
    height: auto;
    aspect-ratio: 4 / 3;
    object-fit: contain;
  }

  .error {
    margin: 0;
    color: #ffb4b4;
  }

  button {
    border: 1px solid #5d89cc;
    background: #10203a;
    color: #eef2ff;
    border-radius: 8px;
    padding: 0.55rem 0.85rem;
    cursor: pointer;
  }

  button:hover {
    background: #193157;
  }
</style>