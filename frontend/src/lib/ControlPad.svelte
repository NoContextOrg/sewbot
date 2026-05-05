<script>
  import { createEventDispatcher, onMount } from 'svelte';
  export let cameraOn;
  export let chatOpen;

  const dispatch = createEventDispatcher();

  let pressed = { w: false, a: false, s: false, d: false };

  function sendDir(dir){
    dispatch('move', dir);
    pressed = { ...pressed, [dir]: true };
  }

  function stopDir(dir, fromKeyboard = false){
    if (dir && pressed[dir]) {
      dispatch('move', 'stop');
      if (fromKeyboard) {
        setTimeout(() => { pressed = { ...pressed, [dir]: false }; }, 100);
      } else {
        pressed = { ...pressed, [dir]: false };
      }
    } else if (!dir) {
      dispatch('move', 'stop');
      pressed = { w: false, a: false, s: false, d: false };
    }
  }

  function handleKeyDown(e) {
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

  function powerOff(){ dispatch('poweroff'); }
  function toggleCamera(){ dispatch('toggleCamera'); }
  function toggleSystemLog(){ dispatch('toggleLog'); }

  // Action handlers
  function handleSideFlap(action) { dispatch('bubble', `Side Flap: ${action}`); }
  function handleRamp(action) { dispatch('bubble', `Ramp: ${action}`); }
  function handleSpray(action) { dispatch('bubble', `Spray: ${action}`); }
  function handlePump(action) { dispatch('bubble', `Pump: ${action}`); }
  function handleConveyor(action) { dispatch('bubble', `Conveyor: ${action}`); }
</script>

<footer class="control-pad-overlay">
  <div class="side-panel">
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
        <button class="action-btn" on:click={() => handleRamp('open')}>Open</button>
        <button class="action-btn" on:click={() => handleRamp('close')}>Close</button>
      </div>
    </div>
    <div class="control-section wide">
      <div class="section-title">SPRAY</div>
      <div class="control-row">
        <button class="action-btn" on:click={() => handleSpray('left')}>Left</button>
        <button class="action-btn" on:click={() => handleSpray('right')}>Right</button>
      </div>
    </div>
  </div>

  <div class="center-panel">
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
  </div>

  <div class="side-panel">
    <div class="control-section">
      <div class="section-title">PUMP</div>
      <div class="control-row">
        <button class="action-btn" on:click={() => handlePump('on')}>On</button>
        <button class="action-btn" on:click={() => handlePump('off')}>Off</button>
      </div>
    </div>
    <div class="control-section">
      <div class="section-title">CONVEYOR</div>
      <div class="control-row">
        <button class="action-btn" on:click={() => handleConveyor('on')}>On</button>
        <button class="action-btn" on:click={() => handleConveyor('off')}>Off</button>
      </div>
    </div>
    <div class="control-section wide">
      <div class="section-title">SYSTEM</div>
      <div class="control-row">
        <button class="btn-power" title="Power off" on:click={powerOff}>POWER OFF</button>
        <button class="action-btn" title="Toggle camera" on:click={toggleCamera} style={cameraOn ? '' : 'color: #ef4444'}>
          CAMERA {cameraOn ? 'ON' : 'OFF'}
        </button>
        <button class="action-btn" title="Toggle system log" on:click={toggleSystemLog}>
          SYSTEM LOGS
        </button>
      </div>
    </div>
  </div>
</footer>

<style>
  .control-pad-overlay{
    display:grid;
    grid-template-columns: 1fr auto 1fr;
    gap:20px;
    align-items:end;
    padding:10px 20px;
    position:absolute;
    bottom:0;
    left:0;
    right:0;
    background:rgba(26,26,26,0.85);
    border-top:1px solid var(--sb-border);
    border-radius:0 0 var(--sb-radius) var(--sb-radius);
    z-index:10;
  }
  .side-panel {
    display: grid;
    grid-template-columns: auto auto;
    gap: 16px 24px;
    justify-items: center;
    align-items: end;
  }
  .control-section {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .control-section.wide {
    grid-column: 1 / -1;
  }
  .section-title{font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:var(--sb-muted);margin-bottom:6px;text-align:center}
  .control-row {
    display: flex;
    gap: 6px;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
  }

  .dpad{
    display:grid;
    grid-template-columns:56px 56px 56px;
    grid-template-rows:56px 56px 56px;
    gap:4px;
    place-items:center;
    background:transparent;
    border:none;
    border-radius:0;
    padding:0;
    box-shadow:none;
  }
  .dpad-btn{width:56px;height:56px;border-radius:6px;border:1px solid var(--sb-border);background:var(--sb-bubble);display:flex;align-items:center;justify-content:center;cursor:pointer;color:#fff;transition:background 120ms ease}
  .dpad-btn:hover{background:#333}
  .dpad-btn svg{width:22px;height:22px}
  .dpad-btn:active{background:#2f2f2f}
  .dpad-btn.pressed{background:var(--sb-accent);border-color:var(--sb-accent);color:#fff}
  .dpad-center{width:56px;height:56px;border-radius:6px;border:1px solid var(--sb-border);background:#1f1f1f}
  .dpad-key{display:none} /* Optional visual toggle */

  .action-btn {
    height: 52px;
    padding: 0 14px;
    border-radius: 6px;
    border: 1px solid var(--sb-border);
    background: var(--sb-bubble);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: #fff;
    font-weight: bold;
    text-transform: uppercase;
    font-size: 13px;
    transition: background 120ms ease;
  }
  .action-btn:hover {
    background: #333;
  }
  .action-btn:active {
    background: #2f2f2f;
  }

  .btn-power{height:52px;min-width:86px;padding:0 14px;border-radius:6px;border:1px solid #991B1B;background:#7F1D1D;color:#fff;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;font-size:13px;cursor:pointer;transition:background 120ms ease, border-color 120ms ease}
  .btn-power:hover{background:#9B1C1C}
  .btn-power:active{background:#7F1D1D}

  @media (max-width: 1100px){
    .control-pad-overlay{
      grid-template-columns: 1fr;
      justify-items: center;
      gap: 32px;
    }
  }
</style>
