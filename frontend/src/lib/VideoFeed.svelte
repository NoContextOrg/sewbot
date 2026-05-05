<script>
  import { createEventDispatcher } from 'svelte';
  export let feedUrl;
  export let cameraOn;
  export let fps;
  export let latency;
  export let bitrate;

  const dispatch = createEventDispatcher();
  
  let liveFeed = false;
  let feedError = '';

  function handleFeedLoad() {
    feedError = '';
    liveFeed = true;
  }
  function handleFeedError() {
    feedError = 'Video feed unavailable';
    liveFeed = false;
  }
  function reloadFeed(){ 
    feedError=''; 
    dispatch('reload');
  }
</script>

<div class="video-stage">
  <div class="overlay-head">
    <div class="overlay-brand">
      <div class="brand-name">SEWBOT</div>
      <div class="brand-sub">The Sewage Robots</div>
    </div>
    <div class="overlay-status">
      <span class="pill live-feed-indicator {liveFeed ? 'live' : 'not-live'}">
        {#if liveFeed}
          <span class="blinking-dot"></span> LIVE
        {:else}
          <span class="not-live-dot"></span> NOT LIVE
        {/if}
      </span>
    </div>
  </div>
  {#if cameraOn}
    <img src={feedUrl} alt="camera feed" class="video-element" on:error={handleFeedError} on:load={handleFeedLoad} />
  {:else}
    <div class="video-element" style="display:flex;align-items:center;justify-content:center;color:var(--sb-muted);font-weight:bold;font-size:18px;letter-spacing:0.1em;background:#0a0a0a;">CAMERA OFF</div>
  {/if}
  <div class="telemetry">
    <div class="telem-item">FPS <strong>{fps}</strong></div>
    <div class="telem-item">Latency <strong>{latency}ms</strong></div>
    <div class="telem-item">Bitrate <strong>{bitrate.toFixed(1)}Mb/s</strong></div>
  </div>
  {#if feedError}
    <div class="video-error">{feedError} <button type="button" class="link" on:click={reloadFeed}>Retry</button></div>
  {/if}
</div>

<style>
  .video-stage{position:relative;border-radius:var(--sb-radius);overflow:hidden;background:#0a0a0a;border:1px solid var(--sb-border);flex:1;display:flex;align-items:center;justify-content:center;width:100%;height:100%;max-height:100%;min-height:0;}
  .video-element{width:100%;height:100%;object-fit:cover;display:block;background:#0a0a0a}
  .overlay-head{position:absolute;left:10px;right:10px;top:10px;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;z-index:6}
  .overlay-brand{background:rgba(15,15,15,0.72);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px) saturate(120%);border:1px solid rgba(255,255,255,0.04);border-radius:var(--sb-radius);padding:6px 8px;display:flex;flex-direction:column;gap:2px}
  .overlay-status{display:flex;gap:8px;align-items:center;background:rgba(15,15,15,0.72);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px) saturate(120%);spadding:6px 8px}
  .telemetry{position:absolute;left:10px;top:62px;display:flex;gap:16px;background:rgba(15,15,15,0.68);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px) saturate(120%);border:1px solid rgba(255,255,255,0.04);border-radius:var(--sb-radius);padding:8px 12px;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:var(--sb-muted);z-index:5}
  .telem-item{display:flex;gap:4px;align-items:center}
  .telem-item strong{font-weight:700}
  .video-error{position:absolute;left:50%;top:10px;transform:translateX(-50%);background:rgba(26,26,26,0.9);-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px);border:1px solid rgba(255,255,255,0.04);border-radius:var(--sb-radius);padding:8px 10px;font-size:12px;color:var(--sb-text);z-index:12}
  .link{border:none;background:transparent;color:var(--sb-accent);font-weight:700;cursor:pointer;padding:0 4px}
  .brand-name{font-weight:800;letter-spacing:0.06em;text-transform:uppercase;font-size:14px}
  .brand-sub{font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:var(--sb-muted)}
  .pill{
    display:inline-flex;
    align-items:center;
    height:26px;
    padding:0 10px;
    border-radius:999px;
    background:var(--sb-bubble);
    border:1px solid var(--sb-border);
    font-size:12px;
    letter-spacing:0.08em;
    text-transform:uppercase;
    color:var(--sb-text);
  }
  .pill.live-feed-indicator {
    position: relative;
    color: #fff;
    background: #2d1b1b;
    border: 1px solid #ef4444;
    font-weight: bold;
    box-shadow: 0 0 8px 2px rgba(239,68,68,0.25);
    min-width: 90px;
    justify-content: center;
  }
  .pill.live-feed-indicator.live {
    color: #fff;
    background: #2d1b1b;
    border: 1px solid #ef4444;
  }
  .pill.live-feed-indicator.not-live {
    color: #bbb;
    background: #222;
    border: 1px solid #444;
    box-shadow: none;
  }
  .blinking-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #ef4444;
    margin-right: 7px;
    box-shadow: 0 0 8px 2px #ef4444;
    animation: blink 1s steps(2, start) infinite;
    vertical-align: middle;
  }
  .not-live-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #888;
    margin-right: 7px;
    vertical-align: middle;
    box-shadow: none;
  }
  @keyframes blink {
    to { visibility: hidden; }
  }
</style>
