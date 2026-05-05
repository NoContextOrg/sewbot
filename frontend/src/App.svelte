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
    appendMessage({ text: e.detail.text, cls: e.detail.cls, ts: e.detail.ts, source: e.detail.source || '' });
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
        {#if m.source}
          <span class="source source-{m.source}">{m.source}</span>
        {/if}
        <span class="msg">{m.text}</span>
        <span class="ts">{m.ts}</span>
      </div>
    {/each}
  </svelte:fragment>
</SewbotDashboard>