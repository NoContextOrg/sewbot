<script>
  import { io } from "socket.io-client";
  import { onMount } from "svelte";

  // Use the .local address so you never have to change IPs
  const socket = io("http://robot.local:5000");
  let status = "Offline";

  onMount(() => {
    socket.on("connect", () => status = "Online");
  });

  const sendMove = (dir) => socket.emit("move", { direction: dir });

  // Keyboard Listeners
  window.onkeydown = (e) => {
    const key = e.key.toLowerCase();
    if (["w","a","s","d"].includes(key)) sendMove(key);
  };
  window.onkeyup = () => sendMove("stop");
</script>

<main class="bg-zinc-900 min-h-screen text-white flex flex-col items-center p-8">
  <h1 class="text-2xl font-mono mb-4">CONTROLLER: {status}</h1>
  <img src="http://robot.local:5000/video_feed" class="border-2 border-red-500 w-full max-w-2xl" alt="Feed"/>
</main>