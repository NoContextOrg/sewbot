<script>
  import { createEventDispatcher, onMount } from 'svelte';
  export let cameraOn;
  export let chatOpen;

  const dispatch = createEventDispatcher();

  let pressed = { w: false, a: false, s: false, d: false, 1: false, 2: false, 3: false, 4: false, 5: false, 6: false, 7: false, 8: false, 9: false, 0: false };

  function emitMovement() {
    const movementKeys = ['w', 'a', 's', 'd'];
    const activeKeys = movementKeys.filter(k => pressed[k]).join('');
    if (activeKeys.length > 0) {
      dispatch('move', activeKeys);
    } else {
      dispatch('move', 'stop');
    }
  }

  function sendDir(dir){
    pressed = { ...pressed, [dir]: true };
    emitMovement();
  }

  function stopDir(dir, fromKeyboard = false){
    if (dir === null) {
      pressed = { ...pressed, w: false, a: false, s: false, d: false };
      emitMovement();
      return;
    }

    if (dir && pressed[dir]) {
      if (fromKeyboard) {
        setTimeout(() => { 
          pressed = { ...pressed, [dir]: false }; 
          emitMovement();
        }, 100);
      } else {
        pressed = { ...pressed, [dir]: false };
        emitMovement();
      }
    } else if (!dir) {
      pressed = { ...pressed, w: false, a: false, s: false, d: false };
      emitMovement();
    }
  }

  function handleKeyDown(e) {
    const tag = document.activeElement?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    const key = e.key.toLowerCase();
    
    // Movement keys
    if (['w','a','s','d'].includes(key) && !pressed[key]) {
      sendDir(key);
    }
    
    // Action keys
    if (['1','2','3','4','5','6','7','8','9','0'].includes(key) && !pressed[key]) {
      pressed = { ...pressed, [key]: true };
      if (key === '1') handleSideFlap('open');
      if (key === '2') handleSideFlap('close');
      if (key === '3') handleRamp('open');
      if (key === '4') handleRamp('close');
      if (key === '5') handleSpray('left');
      if (key === '6') handleSpray('right');
      if (key === '7') handlePump('on');
      if (key === '8') handlePump('off');
      if (key === '9') handleConveyor('on');
      if (key === '0') handleConveyor('off');
    }
  }

  function handleKeyUp(e) {
    const tag = document.activeElement?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    const key = e.key.toLowerCase();
    
    // Movement keys
    if (['w','a','s','d'].includes(key)) {
      stopDir(key, true);
    }
    
    // Action keys (visual reset)
    if (['1','2','3','4','5','6','7','8','9','0'].includes(key)) {
      setTimeout(() => {
        pressed = { ...pressed, [key]: false };
      }, 100);
    }
  }

  // Removed onMount event listeners, using <svelte:window> instead

  function powerOff(){ dispatch('poweroff'); }
  function toggleCamera(){ dispatch('toggleCamera'); }
  function toggleSystemLog(){ dispatch('toggleLog'); }

  // Action handlers
  function handleAction(type, action) {
    dispatch('action', { type, action });
    dispatch('bubble', `${type}: ${action}`);
  }
  function handleSideFlap(action) { handleAction('sideFlap', action); }
  function handleRamp(action) { handleAction('ramp', action); }
  function handleSpray(action) { handleAction('spray', action); }
  function handlePump(action) { handleAction('pump', action); }
  function handleConveyor(action) { handleAction('conveyor', action); }
</script>

<svelte:window on:keydown={handleKeyDown} on:keyup={handleKeyUp} />

<footer class="control-pad-overlay">
  <div class="side-panel">
    <div class="control-section">
      <div class="section-title">SIDE FLAPS</div>
      <div class="control-row">
        <button class="action-btn {pressed['1'] ? 'pressed' : ''}" on:click={() => handleSideFlap('open')}>Open <span class="hotkey">1</span></button>
        <button class="action-btn {pressed['2'] ? 'pressed' : ''}" on:click={() => handleSideFlap('close')}>Close <span class="hotkey">2</span></button>
      </div>
    </div>
    <div class="control-section">
      <div class="section-title">RAMP</div>
      <div class="control-row">
        <button class="action-btn {pressed['3'] ? 'pressed' : ''}" on:click={() => handleRamp('open')}>Open <span class="hotkey">3</span></button>
        <button class="action-btn {pressed['4'] ? 'pressed' : ''}" on:click={() => handleRamp('close')}>Close <span class="hotkey">4</span></button>
      </div>
    </div>
    <div class="control-section wide">
      <div class="section-title">SPRAY</div>
      <div class="control-row">
        <button class="action-btn {pressed['5'] ? 'pressed' : ''}" on:click={() => handleSpray('left')}>Left <span class="hotkey">5</span></button>
        <button class="action-btn {pressed['6'] ? 'pressed' : ''}" on:click={() => handleSpray('right')}>Right <span class="hotkey">6</span></button>
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
      <button class="dpad-center" aria-label="Stop" on:pointerdown={() => stopDir(null)}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" fill="currentColor" rx="2" /></svg>
      </button>
      <button class="dpad-btn {pressed.d ? 'pressed' : ''}" aria-label="Right" on:pointerdown={() => sendDir('d')} on:pointerup={() => stopDir('d')} on:pointerleave={() => stopDir('d')}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 12H8M12 8l4 4-4 4" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <span class="dpad-key">D</span>
        </button>

        <div></div>
        <button class="dpad-btn {pressed.s ? 'pressed' : ''}" aria-label="Down" on:pointerdown={() => sendDir('s')} on:pointerup={() => stopDir('s')} on:pointerleave={() => stopDir('s')}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8v8M8 12l4 4 4-4" stroke="currentColor" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
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
        <button class="action-btn {pressed['7'] ? 'pressed' : ''}" on:click={() => handlePump('on')}>On <span class="hotkey">7</span></button>
        <button class="action-btn {pressed['8'] ? 'pressed' : ''}" on:click={() => handlePump('off')}>Off <span class="hotkey">8</span></button>
      </div>
    </div>
    <div class="control-section">
      <div class="section-title">CONVEYOR</div>
      <div class="control-row">
        <button class="action-btn {pressed['9'] ? 'pressed' : ''}" on:click={() => handleConveyor('on')}>On <span class="hotkey">9</span></button>
        <button class="action-btn {pressed['0'] ? 'pressed' : ''}" on:click={() => handleConveyor('off')}>Off <span class="hotkey">0</span></button>
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
  .dpad-btn{width:56px;height:56px;border-radius:6px;border:1px solid var(--sb-border);background:var(--sb-bubble);display:flex;align-items:center;justify-content:center;cursor:pointer;color:#fff;transition:background 120ms ease;position:relative}
  .dpad-btn:hover{background:#333}
  .dpad-btn svg{width:22px;height:22px}
  .dpad-btn:active{background:#2f2f2f}
  .dpad-btn.pressed{background:var(--sb-accent);border-color:var(--sb-accent);color:#fff}
  .dpad-center{width:56px;height:56px;border-radius:6px;border:1px solid var(--sb-border);background:#1f1f1f;display:flex;align-items:center;justify-content:center;cursor:pointer;color:#ef4444;transition:background 120ms ease;position:relative}
  .dpad-center:hover{background:#333}
  .dpad-center svg{width:20px;height:20px}
  .dpad-center:active{background:#2f2f2f}
  .dpad-key{
    position:absolute;
    bottom:4px;
    right:4px;
    font-size:9px;
    font-weight:800;
    color:var(--sb-muted);
    background:rgba(0,0,0,0.4);
    padding:1px 4px;
    border-radius:3px;
    border:1px solid rgba(255,255,255,0.1);
  }
  .dpad-btn.pressed .dpad-key{
    color:#fff;
    border-color:rgba(255,255,255,0.4);
  }

  .action-btn {
    height: 52px;
    padding: 0 14px;
    border-radius: 6px;
    border: 1px solid var(--sb-border);
    background: var(--sb-bubble);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
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
  .action-btn:active, .action-btn.pressed {
    background: var(--sb-accent);
    border-color: var(--sb-accent);
  }
  .hotkey {
    background: rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    color: var(--sb-muted);
  }
  .action-btn.pressed .hotkey {
    color: #fff;
    border-color: rgba(255,255,255,0.4);
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
