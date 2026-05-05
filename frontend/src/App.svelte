<script>
  import { onMount } from "svelte";
  import SewbotDashboard from "./lib/SewbotDashboard.svelte";
  import { 
    initSocket, 
    disconnectSocket, 
    status, 
    telemetry, 
    messages, 
    backendOrigin, 
    sendMove, 
    sendAction,
    sendShellCommand, 
    sendPowerOff,
    appendMessage
  } from "./lib/socketStore";

  onMount(() => {
    initSocket();
    return () => {
      disconnectSocket();
    };
  });

  function handleBubble(e){
    appendMessage({ text: e.detail.text, cls: e.detail.cls, ts: e.detail.ts });
  }

  function handleCommand(e){
    sendShellCommand(e.detail.text);
  }

  function handlePowerOff(){
    sendPowerOff();
  }
</script>

<SewbotDashboard 
  backendOrigin={backendOrigin} 
  status={$status} 
  telemetry={$telemetry} 
  sendMove={sendMove} 
  sendAction={sendAction}
  on:bubble={handleBubble} 
  on:command={handleCommand} 
  on:poweroff={handlePowerOff}
>
  <svelte:fragment slot="bubbles">
    {#each $messages as m}
      <div class="bubble {m.cls}">
        <div class="msg">{m.text}</div>
        <div class="ts">{m.ts}</div>
      </div>
    {/each}
  </svelte:fragment>
</SewbotDashboard>