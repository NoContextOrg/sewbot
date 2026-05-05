<script>
  import { createEventDispatcher } from 'svelte';
  export let chatOpen = false;
  
  let chatText = '';
  const dispatch = createEventDispatcher();

  function submitCommand(){
    const v = chatText.trim();
    if (!v) return;
    dispatch('command', { text: v });
    chatText = '';
  }
</script>

{#if chatOpen}
  <aside class="chat-panel chat-modal">
    <div class="chat-header">System Log</div>
    <div class="chat-log" id="chatLog">
      <slot></slot>
    </div>
    <div class="chat-input">
      <input
        bind:value={chatText}
        placeholder="Shell command..."
        on:keydown={(e) => {
          if (e.key === 'Enter') {
            submitCommand();
          }
        }}
      />
      <button
        type="button"
        on:click={submitCommand}
      >Send</button>
    </div>
  </aside>
{/if}

<style>
  .chat-panel{background:rgba(26,26,26,0.82);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px) saturate(110%);border-radius:var(--sb-radius);padding:12px;border:1px solid rgba(255,255,255,0.04);display:flex;flex-direction:column;min-height:0}
  .chat-modal{position:absolute;right:14px;top:60px;width:320px;height:calc(100vh - 400px);z-index:10;box-shadow:0 4px 20px rgba(0,0,0,0.6);animation:slideIn 200ms ease-out}
  @keyframes slideIn{from{opacity:0;transform:translateX(100%);}to{opacity:1;transform:translateX(0);}}
  .chat-header{font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:var(--sb-muted);font-size:12px}
  .chat-log{flex:1;overflow:auto;padding:10px 6px;display:flex;flex-direction:column;gap:10px;min-height:0}

  .chat-input{display:flex;gap:8px;margin-top:10px}
  .chat-input input{flex:1;padding:10px;border-radius:var(--sb-radius);border:1px solid var(--sb-border);background:var(--sb-bubble);color:var(--sb-text);font-family:var(--sb-mono);font-size:12px}
  .chat-input button{padding:10px 14px;border-radius:8px;border:1px solid var(--sb-accent);background:var(--sb-accent);color:#fff;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;font-size:12px;cursor:pointer}

  @media (max-width: 1100px){
    .chat-modal{width:min(90vw, 320px)}
  }
</style>
