<script>
  import { onMount, createEventDispatcher } from 'svelte';
  export let backendOrigin = '';
  export let status = 'Offline';
  export let telemetry = { fps: 0, latency: 0, bitrate: 0 };
  export let sendMove = (dir = '') => {};

  const dispatch = createEventDispatcher();

  let feedNonce = Date.now();
  $: feedUrl = `${backendOrigin}/video_feed?ts=${feedNonce}`;
  let feedError = '';
  let liveFeed = false;

  let chatText = '';

  let autoOn = true;
  let cameraOn = true;
  let recordOn = false;
  let speed = 50;

  $: fps = telemetry.fps || 0;
  $: latency = telemetry.latency || 0;
  $: bitrate = telemetry.bitrate || 0;

  let chatOpen = false;

  function reloadFeed(){ feedError=''; feedNonce = Date.now(); }

  // Set liveFeed true when feed loads, false when error
  function handleFeedLoad() {
    feedError = '';
    liveFeed = true;
  }
  function handleFeedError() {
    feedError = 'Video feed unavailable';
    liveFeed = false;
  }

  function nowTs(){
    const d = new Date();
    return d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
  }

  function pushBubble(text, cls='system'){
    dispatch('bubble', { text, cls, ts: nowTs() });
  }

  let pressed = { w: false, a: false, s: false, d: false };

  function sendDir(dir){
    sendMove(dir);
    pressed = { ...pressed, [dir]: true };
  }

  function stopDir(dir, fromKeyboard = false){
    if (dir && pressed[dir]) {
      sendMove('stop');
      if (fromKeyboard) {
        // Add a short delay for visual feedback
        setTimeout(() => {
          pressed = { ...pressed, [dir]: false };
        }, 100);
      } else {
        pressed = { ...pressed, [dir]: false };
      }
    } else if (!dir) {
      sendMove('stop');
      pressed = { w: false, a: false, s: false, d: false };
    }
  }

  function handleKeyDown(e) {
    // Ignore if typing in an input or textarea
    const tag = document.activeElement?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    const key = e.key.toLowerCase();
    if (['w','a','s','d'].includes(key) && !pressed[key]) {
      sendDir(key);
    }
  }
  function handleKeyUp(e) {
    const tag = document.activeElement?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    const key = e.key.toLowerCase();
    if (['w','a','s','d'].includes(key)) {
      stopDir(key, true);
    }
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  });

  function increaseSpeed(){
    speed = Math.min(100, speed + 5);
  }

  function decreaseSpeed(){
    speed = Math.max(0, speed - 5);
  }

  function submitCommand(){
    const v = chatText.trim();
    if (!v) return;
    dispatch('command', { text: v });
    chatText = '';
  }

  function confirmPowerOff(){
    const ok = window.confirm('Power off the sewbot now?');
    if (ok) dispatch('poweroff');
  }

// --- Control handlers (replace with real logic as needed) ---
function handleSideFlap(action) {
  // TODO: connect to backend
  pushBubble(`Side Flap: ${action}`);
}
function handleRamp(action) {
  // TODO: connect to backend
  pushBubble(`Ramp: ${action}`);
}
function handleSpray(action) {
  // TODO: connect to backend
  pushBubble(`Spray: ${action}`);
}
function handlePump(action) {
  // TODO: connect to backend
  pushBubble(`Pump: ${action}`);
}
function handleConveyor(action) {
  // TODO: connect to backend
  pushBubble(`Conveyor: ${action}`);
}
</script>

<div class="viewport">
  <main class="main-grid">
    <section class="video-wrap">
      <div class="video-stage">
        <div class="overlay-head">
          <div class="overlay-brand">
            <div class="brand-name">SEWBOT</div>
            <div class="brand-sub">ROBOTIC CONTROLLER</div>
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
        <img src={feedUrl} alt="camera feed" class="video-element" on:error={handleFeedError} on:load={handleFeedLoad} />
        <div class="telemetry">
          <div class="telem-item">FPS <strong>{fps}</strong></div>
          <div class="telem-item">Latency <strong>{latency}ms</strong></div>
          <div class="telem-item">Bitrate <strong>{bitrate.toFixed(1)}Mb/s</strong></div>
        </div>
        {#if feedError}
          <div class="video-error">{feedError} <button type="button" class="link" on:click={reloadFeed}>Retry</button></div>
        {/if}
      </div>
    </section>

    <footer class="control-pad-overlay control-sections">
          <div class="control-section">
            <div class="section-title">MOVEMENT</div>
            <div class="dpad">
              <div></div>
              <button class="dpad-btn {pressed.w ? 'pressed' : ''}" aria-label="Up" on:pointerdown={() => sendDir('w')} on:pointerup={() => stopDir('w')} on:pointerleave={() => stopDir('w')}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8v8M8 12l4-4 4 4" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <span class="dpad-key">W</span>
              </button>
              <div></div>

              <button class="dpad-btn {pressed.a ? 'pressed' : ''}" aria-label="Left" on:pointerdown={() => sendDir('a')} on:pointerup={() => stopDir('a')} on:pointerleave={() => stopDir('a')}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 12h8M12 16l-4-4 4-4" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <span class="dpad-key">A</span>
              </button>
              <div class="dpad-center" aria-hidden="true"></div>
              <button class="dpad-btn {pressed.d ? 'pressed' : ''}" aria-label="Right" on:pointerdown={() => sendDir('d')} on:pointerup={() => stopDir('d')} on:pointerleave={() => stopDir('d')}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 12H8M12 8l4 4-4 4" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <span class="dpad-key">D</span>
              </button>

              <div></div>
              <button class="dpad-btn {pressed.s ? 'pressed' : ''}" aria-label="Down" on:pointerdown={() => sendDir('s')} on:pointerup={() => stopDir('s')} on:pointerleave={() => stopDir('s')}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V8m-4-4l4 4 4-4" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <span class="dpad-key">S</span>
              </button>
              <div></div>
            </div>
          </div>

          <div class="control-section">
            <div class="section-title">SIDE FLAPS</div>
            <div class="control-row">
              <button class="action-btn" on:click={() => handleSideFlap('open')}>Open</button>
              <button class="action-btn" on:click={() => handleSideFlap('close')}>Close</button>
            </div>
          </div>

          <div class="control-section">
            <div class="section-title">RAMP</div>
            <div class="control-row">
              <button class="action-btn" on:click={() => handleRamp('up')}>Up</button>
              <button class="action-btn" on:click={() => handleRamp('open')}>Open</button>
              <button class="action-btn" on:click={() => handleRamp('close')}>Close</button>
            </div>
          </div>

          <div class="control-section">
            <div class="section-title">SPRAY</div>
            <div class="control-row">
              <button class="action-btn" on:click={() => handleSpray('left')}>Left</button>
              <button class="action-btn" on:click={() => handleSpray('right')}>Right</button>
            </div>
          </div>

          <div class="control-section">
            <div class="section-title">PUMP</div>
            <div class="control-row">
              <button class="action-btn" on:click={() => handlePump('on')}>On</button>
              <button class="action-btn" on:click={() => handlePump('off')}>Off</button>
            </div>
          </div>

          <div class="control-section">
            <div class="section-title">CONVEYOR</div>
            <div class="control-row" style="display:flex; gap:8px">
              <button class="action-btn" on:click={() => handleConveyor('on')}>On</button>
              <button class="action-btn" on:click={() => handleConveyor('off')}>Off</button>
            </div>
          </div>

          <div class="control-section">
            <div class="section-title">SYSTEM</div>
            <div class="control-row" style="display:flex; gap:8px; align-items:center;">
              <button class="btn-power" title="Power off" on:click={confirmPowerOff}>POWER</button>
              <button class="btn-chat" title="Toggle system log" on:click={() => chatOpen = !chatOpen}>
                {#if chatOpen}✕{:else}☰{/if}
              </button>
            </div>
          </div>
        </footer>

    {#if chatOpen}
      <aside class="chat-panel chat-modal">
        <div class="chat-header">System Log</div>
        <div class="chat-log" id="chatLog">
          <slot name="bubbles"></slot>
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

  .brand{display:flex;flex-direction:column;gap:2px}
  .brand-name{font-weight:800;letter-spacing:0.06em;text-transform:uppercase;font-size:14px}
  .brand-sub{font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:var(--sb-muted)}

  .status{display:flex;gap:8px;align-items:center}
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
  .pill.muted{color:var(--sb-muted)}
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
  .pill.online{border-color:var(--sb-accent); color:var(--sb-accent)}

  .main-grid{display:grid;grid-template-columns:1fr;gap:0;flex:1;min-height:0;position:relative;overflow:visible}

  .video-wrap{display:flex;flex-direction:column;gap:0;justify-self:stretch;align-self:stretch;width:100%;height:100%;min-height:0;}
  .video-stage{position:relative;border-radius:var(--sb-radius);overflow:hidden;background:#0a0a0a;border:1px solid var(--sb-border);flex:1;display:flex;align-items:center;justify-content:center;width:100%;height:100%;max-height:100%;min-height:0;}
  .video-element{width:100%;height:100%;object-fit:cover;display:block;background:#0a0a0a}
  .overlay-head{position:absolute;left:10px;right:10px;top:10px;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;z-index:6}
  .overlay-brand{background:rgba(15,15,15,0.72);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px) saturate(120%);border:1px solid rgba(255,255,255,0.04);border-radius:var(--sb-radius);padding:6px 8px;display:flex;flex-direction:column;gap:2px}
  .overlay-status{display:flex;gap:8px;align-items:center;background:rgba(15,15,15,0.72);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px) saturate(120%);border:1px solid rgba(255,255,255,0.04);border-radius:var(--sb-radius);padding:6px 8px}
  .telemetry{position:absolute;right:10px;top:62px;display:flex;gap:16px;background:rgba(15,15,15,0.68);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px) saturate(120%);border:1px solid rgba(255,255,255,0.04);border-radius:var(--sb-radius);padding:8px 12px;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:var(--sb-muted);z-index:5}
  .telem-item{display:flex;gap:4px;align-items:center}
  .telem-item strong{color:var(--sb-accent);font-weight:700}
  .video-error{position:absolute;left:50%;top:10px;transform:translateX(-50%);background:rgba(26,26,26,0.9);-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px);border:1px solid rgba(255,255,255,0.04);border-radius:var(--sb-radius);padding:8px 10px;font-size:12px;color:var(--sb-text);z-index:12}
  .link{border:none;background:transparent;color:var(--sb-accent);font-weight:700;cursor:pointer;padding:0 4px}

  .chat-panel{background:rgba(26,26,26,0.82);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px) saturate(110%);border-radius:var(--sb-radius);padding:12px;border:1px solid rgba(255,255,255,0.04);display:flex;flex-direction:column;min-height:0}
  .chat-modal{position:absolute;right:14px;top:60px;width:320px;height:calc(100vh - 400px);z-index:10;box-shadow:0 4px 20px rgba(0,0,0,0.6);animation:slideIn 200ms ease-out}
  @keyframes slideIn{from{opacity:0;transform:translateX(100%);}to{opacity:1;transform:translateX(0);}}
  .chat-header{font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:var(--sb-muted);font-size:12px}
  .chat-log{flex:1;overflow:auto;padding:10px 6px;display:flex;flex-direction:column;gap:10px;min-height:0}

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

  .chat-input{display:flex;gap:8px;margin-top:10px}
  .chat-input input{flex:1;padding:10px;border-radius:var(--sb-radius);border:1px solid var(--sb-border);background:var(--sb-bubble);color:var(--sb-text);font-family:var(--sb-mono);font-size:12px}
  .chat-input button{padding:10px 14px;border-radius:8px;border:1px solid var(--sb-accent);background:var(--sb-accent);color:#fff;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;font-size:12px;cursor:pointer}

  .btn-chat{width:42px;height:42px;border-radius:8px;border:1px solid var(--sb-border);background:var(--sb-bubble);display:flex;align-items:center;justify-content:center;cursor:pointer;color:#fff;font-size:18px;font-weight:bold;transition:background 120ms ease}
  .btn-chat:hover{background:#333}
  .btn-chat:active{background:#2f2f2f}

  .btn-power{height:42px;min-width:86px;padding:0 12px;border-radius:8px;border:1px solid #991B1B;background:#7F1D1D;color:#fff;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;font-size:11px;cursor:pointer;transition:background 120ms ease, border-color 120ms ease}
  .btn-power:hover{background:#9B1C1C}
  .btn-power:active{background:#7F1D1D}

  .control-pad-overlay{
    display:flex;
    flex-wrap:wrap;
    justify-content:space-between;
    gap:16px;
    align-items:end;
    padding:12px;
    position:absolute;
    bottom:0;
    left:0;
    right:0;
    background:rgba(26,26,26,0.8);
    border:1px solid var(--sb-border);
    border-radius:var(--sb-radius);
    box-shadow:0 2px 12px 0 rgba(0,0,0,0.18);
    z-index:10;
  }
  .section-title{font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:var(--sb-muted);margin-bottom:10px}

  .dpad{
    display:grid;
    grid-template-columns:48px 48px 48px;
    grid-template-rows:48px 48px 48px;
    gap:6px;
    place-items:center;
    background:transparent;
    border:none;
    border-radius:0;
    padding:0;
    box-shadow:none;
  }
  .dpad-btn{width:48px;height:48px;border-radius:8px;border:1px solid var(--sb-border);background:var(--sb-bubble);display:flex;align-items:center;justify-content:center;cursor:pointer;color:#fff}
  .dpad-btn svg{width:18px;height:18px}
  .dpad-btn:active{background:#2f2f2f}
  .dpad-center{width:48px;height:48px;border-radius:8px;border:1px solid var(--sb-border);background:#1f1f1f}

  /* camera toggle */
  .camera-toggle{width:56px;height:36px;border-radius:10px;border:1px solid var(--sb-border);background:var(--sb-bubble);display:flex;align-items:center;justify-content:center;cursor:pointer;color:#fff;font-size:16px}
  .camera-toggle.on{border-color:var(--sb-accent);background:linear-gradient(180deg, rgba(59,130,246,0.12), rgba(59,130,246,0.06))}

  .speed{display:flex;gap:12px;align-items:center}
  .accel-btn{width:34px;height:34px;border-radius:8px;border:1px solid var(--sb-border);background:var(--sb-bubble);color:#fff;font-size:18px;display:flex;align-items:center;justify-content:center;cursor:pointer}
  .accel-btn:active{background:#2f2f2f}
  .speed.accel input[type='range']{margin:0 8px}
  .speed-val{min-width:48px;font-family:var(--sb-mono);font-size:12px;color:var(--sb-muted)}
  input[type='range']{width:100%;accent-color:var(--sb-accent)}

  @media (max-width: 1100px){
    .control-pad-overlay{justify-content:center}
    .chat-modal{width:min(90vw, 320px)}
  }
</style>