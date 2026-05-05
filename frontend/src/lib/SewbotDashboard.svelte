<script>
  import { createEventDispatcher } from 'svelte';
  import VideoFeed from './VideoFeed.svelte';
  import ControlPad from './ControlPad.svelte';
  import SystemLog from './SystemLog.svelte';

  export let backendOrigin = '';
  export let status = 'Offline';
  export let telemetry = { fps: 0, latency: 0, bitrate: 0 };
  export let sendMove = (dir = '') => {};

  const dispatch = createEventDispatcher();

  let feedNonce = Date.now();
  $: feedUrl = `${backendOrigin}/video_feed?ts=${feedNonce}`;

  let cameraOn = true;
  let chatOpen = false;

  $: fps = telemetry.fps || 0;
  $: latency = telemetry.latency || 0;
  $: bitrate = telemetry.bitrate || 0;

  function reloadFeed(){ feedNonce = Date.now(); }

  function handleMove(e) {
    sendMove(e.detail);
  }
</script>

<div class="viewport">
  <main class="main-grid">
    <section class="video-wrap">
      <VideoFeed 
        {feedUrl} 
        {cameraOn} 
        {fps} 
        {latency} 
        {bitrate} 
        on:reload={reloadFeed} 
      />
    </section>

    <ControlPad 
      {cameraOn} 
      {chatOpen} 
      on:move={handleMove}
      on:bubble={(e) => dispatch('bubble', { text: e.detail, cls: 'system', ts: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) })}
      on:poweroff={() => dispatch('poweroff')}
      on:toggleCamera={() => cameraOn = !cameraOn}
      on:toggleLog={() => chatOpen = !chatOpen}
    />

    <SystemLog {chatOpen} on:command>
      <slot name="bubbles"></slot>
    </SystemLog>
  </main>
</div>

<style>
  :global(:root){
    --sb-bg:#0F0F0F;
    --sb-panel:#1A1A1A;
    --sb-bubble:#262626;
    --sb-accent:#3B82F6;
    --sb-text:#FFFFFF;
    --sb-muted:#888888;
    --sb-border:#2D2D2D;
    --sb-radius:4px;
    --sb-sans: Inter, "Helvetica Neue", system-ui, "Segoe UI", Roboto, Arial, sans-serif;
    --sb-mono: "JetBrains Mono", "Roboto Mono", ui-monospace, Consolas, monospace;
    --sb-camera-aspect: 4 / 3;
  }

  .viewport{
    display:flex;
    flex-direction:column;
    height:100vh;
    height:100svh;
    max-height:100svh;
    padding:10px;
    box-sizing:border-box;
    gap:0;
    background:var(--sb-bg);
    color:var(--sb-text);
    font-family:var(--sb-sans);
    overflow:hidden;
  }

  .main-grid{display:grid;grid-template-columns:1fr;gap:0;flex:1;min-height:0;position:relative;overflow:visible}
  .video-wrap{display:flex;flex-direction:column;gap:0;justify-self:stretch;align-self:stretch;width:100%;height:100%;min-height:0;}

  /* style slotted message bubbles */
  ::slotted(.bubble){
    max-width:100%;
    padding:10px 10px;
    border-radius:var(--sb-radius);
    background:var(--sb-bubble);
    border:1px solid var(--sb-border);
    border-left:1px solid var(--sb-border);
    color:var(--sb-text);
    font-family:var(--sb-mono);
    font-size:12px;
    line-height:1.35;
    position:relative;
  }
  ::slotted(.bubble.user){
    border-color:var(--sb-accent);
  }
  ::slotted(.bubble.warn){
    background:#2A2115;
    border:1px solid #F59E0B;
    border-left:4px solid #F59E0B;
    color:#FDE68A;
  }
  ::slotted(.bubble.error){
    background:#2D1B1B;
    border:1px solid #EF4444;
    border-left:4px solid #EF4444;
    color:#FCA5A5;
  }
  ::slotted(.bubble) .ts{
    margin-top:6px;
    font-size:11px;
    color:var(--sb-accent);
    letter-spacing:0.06em;
  }
</style>