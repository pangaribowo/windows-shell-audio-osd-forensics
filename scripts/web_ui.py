"""
Web UI: Rich interactive browser debugger dashboard for AI Agents and Human Operators
Includes live MJPEG video stream, F2/F3 hotkeys, coordinate clicker, OSD sync panel, and pixel inspector.
"""

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Antigravity Desktop Agent - Live Screen & OSD Debugger</title>
<style>
  :root {
    --bg: #0b0f17;
    --card: #151b26;
    --border: #232c3d;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --accent: #3b82f6;
    --accent-hover: #2563eb;
    --danger: #ef4444;
    --success: #10b981;
    --warning: #f59e0b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-height: 100vh;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
    gap: 10px;
  }
  .title-group { display: flex; align-items: center; gap: 12px; }
  h1 { font-size: 1.25rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px; }
  .badge {
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .badge-success {
    background: rgba(16, 185, 129, 0.15);
    color: var(--success);
    border: 1px solid rgba(16, 185, 129, 0.3);
  }
  .badge-agent {
    background: rgba(59, 130, 246, 0.15);
    color: var(--accent);
    border: 1px solid rgba(59, 130, 246, 0.3);
  }

  /* Controls Toolbars */
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
    background: var(--card);
    padding: 12px;
    border-radius: 8px;
    border: 1px solid var(--border);
  }
  .toolbar-group {
    display: flex;
    align-items: center;
    gap: 6px;
    border-right: 1px solid var(--border);
    padding-right: 12px;
  }
  .toolbar-group:last-child { border-right: none; }
  .toolbar-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-right: 4px; }

  button {
    background: var(--accent);
    color: white;
    border: none;
    padding: 7px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    transition: all 0.15s;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  button:hover { background: var(--accent-hover); transform: translateY(-1px); }
  button:active { transform: translateY(0); }
  button.secondary {
    background: #1e2636;
    color: var(--text);
    border: 1px solid var(--border);
  }
  button.secondary:hover { background: #273349; }
  button.danger { background: #dc2626; }
  button.danger:hover { background: #b91c1c; }
  button.action-btn { background: #22c55e; }
  button.action-btn:hover { background: #16a34a; }
  select {
    background: #1e2636;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 0.85rem;
  }

  /* Main Layout */
  .main-layout {
    display: grid;
    grid-template-columns: 1fr 390px;
    gap: 16px;
    flex: 1;
  }
  @media (max-width: 1024px) {
    .main-layout { grid-template-columns: 1fr; }
  }

  .screen-box {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }
  .screen-meta {
    width: 100%;
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: var(--text-muted);
  }
  .screen-wrapper {
    position: relative;
    max-width: 100%;
    cursor: crosshair;
    display: inline-block;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
  }
  #screenImg {
    max-width: 100%;
    height: auto;
    display: block;
  }
  .marker {
    position: absolute;
    width: 16px;
    height: 16px;
    border: 2px solid var(--danger);
    background: rgba(239, 68, 68, 0.4);
    border-radius: 50%;
    transform: translate(-50%, -50%);
    pointer-events: none;
    display: none;
  }

  /* Side Panels */
  .side-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .card-header {
    font-size: 0.9rem;
    font-weight: 700;
    color: #fff;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
  }
  .info-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    gap: 8px;
  }
  .info-label { color: var(--text-muted); }
  .info-val { font-weight: 600; text-align: right; }
  .mono { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }

  /* Volume Bar */
  .vol-container {
    background: #1e2636;
    border-radius: 6px;
    height: 16px;
    width: 100%;
    overflow: hidden;
    position: relative;
    margin-top: 4px;
  }
  .vol-fill {
    background: linear-gradient(90deg, #3b82f6, #60a5fa);
    height: 100%;
    width: 0%;
    transition: width 0.2s ease;
  }
  .vol-text {
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.7rem; font-weight: bold; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.8);
  }

  .color-swatch {
    width: 22px;
    height: 22px;
    border-radius: 4px;
    border: 1px solid var(--border);
    display: inline-block;
    vertical-align: middle;
  }
  .window-tree {
    max-height: 250px;
    overflow-y: auto;
    font-size: 0.8rem;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .window-node {
    background: #0f141f;
    border: 1px solid var(--border);
    padding: 8px;
    border-radius: 6px;
  }
  .window-title { font-weight: 600; color: #60a5fa; }
  .alert-box {
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #fcd34d;
    padding: 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    line-height: 1.4;
  }
  .toast {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #10b981;
    color: white;
    padding: 10px 18px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    opacity: 0;
    transform: translateY(10px);
    transition: all 0.25s;
    pointer-events: none;
    z-index: 9999;
  }
  .toast.show { opacity: 1; transform: translateY(0); }
</style>
</head>
<body>

<header>
  <div class="title-group">
    <h1>🤖 Antigravity Desktop Agent Core</h1>
    <span class="badge badge-agent">Codex / Astra Desktop Control</span>
    <span class="badge badge-success" id="streamBadge">● Live Mode</span>
  </div>
  <div id="systemInfo" style="font-size:0.8rem; color:var(--text-muted);">
    Loading System Metrics...
  </div>
</header>

<!-- Main Toolbar: Hotkeys, OSD Sync & Streaming Controls -->
<div class="toolbar">
  <div class="toolbar-group">
    <span class="toolbar-label">Feed</span>
    <button id="btnStreamToggle" class="action-btn">▶ Live Stream</button>
    <button id="btnRefresh" class="secondary">🔄 Refresh</button>
    <select id="autoRefreshSelect">
      <option value="stream" selected>Live Video (Stream)</option>
      <option value="1000">Poll 1s</option>
      <option value="2000">Poll 2s</option>
      <option value="manual">Manual Poll</option>
    </select>
  </div>

  <div class="toolbar-group">
    <span class="toolbar-label">Hotkeys / OSD</span>
    <button id="btnF2" class="secondary" title="Lenovo ThinkPad / Windows Volume Down">🔉 F2 (Vol -)</button>
    <button id="btnF3" class="secondary" title="Lenovo ThinkPad / Windows Volume Up">🔊 F3 (Vol +)</button>
    <button id="btnMute" class="secondary">🔇 Mute</button>
    <button id="btnFixOsd" class="action-btn" title="Remediate Lenovo stuck '0' slider and sync WASAPI & waveOut">🛠️ Fix OSD Sync</button>
    <button id="btnShowHud" class="secondary" title="Trigger Synchronized Agent HUD overlay">👁️ Show HUD</button>
  </div>

  <div class="toolbar-group">
    <span class="toolbar-label">Interaction Mode</span>
    <select id="clickModeSelect">
      <option value="inspect" selected>Click to Inspect Hierarchy</option>
      <option value="click">Click to Send Real Mouse Click</option>
      <option value="double">Click to Double Click</option>
    </select>
  </div>

  <div class="toolbar-group">
    <span class="toolbar-label">View</span>
    <button id="btnZoomOsd" class="secondary">🔍 OSD Area</button>
    <button id="btnZoomFull" class="secondary">🖥️ Full Screen</button>
  </div>
</div>

<div class="main-layout">
  <!-- Screen Canvas & Feed -->
  <div class="screen-box">
    <div class="screen-meta">
      <span id="screenCoords">Pointer: (0, 0) | Desktop: 1366x768</span>
      <span id="latencyDisplay">Feed: Ready</span>
    </div>
    <div class="screen-wrapper" id="screenWrapper">
      <img id="screenImg" src="/api/screenshot" alt="Desktop Screen Capture">
      <div class="marker" id="marker"></div>
    </div>
  </div>

  <!-- Sidebar: Audio, OSD Diagnostics & UI Inspector -->
  <div class="side-panel">
    <!-- Audio & OSD Diagnostics Card -->
    <div class="card">
      <div class="card-header">
        <span>🔊 Audio & OSD Synchronization</span>
        <button id="btnSyncAudio" class="secondary" style="padding:3px 8px; font-size:0.75rem;">Sync Now</button>
      </div>
      <div class="info-row">
        <span class="info-label">Master Volume:</span>
        <span class="info-val mono" id="volVal">--</span>
      </div>
      <div class="vol-container">
        <div class="vol-fill" id="volBar"></div>
        <div class="vol-text" id="volText">--</div>
      </div>
      <div class="info-row">
        <span class="info-label">Audio Device:</span>
        <span class="info-val" id="audioDevice" style="font-size:0.75rem;">Detecting...</span>
      </div>
      <div class="info-row">
        <span class="info-label">OSD Driver:</span>
        <span class="info-val" id="osdOwner">Detecting...</span>
      </div>
      <div class="info-row">
        <span class="info-label">Legacy waveOut:</span>
        <span class="info-val mono" id="waveoutVal">--</span>
      </div>

      <div class="alert-box" id="osdDiagnosisBox">
        Analyzing OSD processes...
      </div>
    </div>

    <!-- Inspector Details Card -->
    <div class="card">
      <div class="card-header">
        <span>🔍 Element & Pixel Inspector</span>
        <span class="mono" id="inspCoord">(Click screen)</span>
      </div>
      <div class="info-row">
        <span class="info-label">Pixel Color:</span>
        <span class="info-val">
          <span class="color-swatch" id="colorSwatch"></span>
          <span class="mono" id="hexVal">#000000</span>
        </span>
      </div>
      <div class="info-row">
        <span class="info-label">Direct Hit HWND:</span>
        <span class="info-val mono" id="hitHwnd">None</span>
      </div>
      <div class="info-row">
        <span class="info-label">Window Class:</span>
        <span class="info-val mono" id="hitClass">-</span>
      </div>
      <div class="info-row">
        <span class="info-label">Title / Caption:</span>
        <span class="info-val" id="hitTitle">-</span>
      </div>
      <div class="info-row">
        <span class="info-label">Process (PID):</span>
        <span class="info-val mono" id="hitProc">-</span>
      </div>

      <div style="font-size:0.8rem; font-weight:600; color:var(--text-muted); margin-top:6px;">Window Hierarchy:</div>
      <div class="window-tree" id="windowTree">
        <div style="font-size:0.75rem; color:var(--text-muted);">Click on any element in the desktop feed to view its child tree and Win32 styles.</div>
      </div>
    </div>
  </div>
</div>

<div class="toast" id="toast">Action Completed</div>

<script>
  const screenImg = document.getElementById('screenImg');
  const screenWrapper = document.getElementById('screenWrapper');
  const marker = document.getElementById('marker');
  const screenCoords = document.getElementById('screenCoords');
  const latencyDisplay = document.getElementById('latencyDisplay');
  const streamBadge = document.getElementById('streamBadge');
  const toast = document.getElementById('toast');

  let currentCrop = null;
  let isStreaming = true;
  let pollTimer = null;
  let naturalW = 1366, naturalH = 768;

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2000);
  }

  // Live MJPEG streaming or Polling
  function setStreamMode(mode) {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }

    if (mode === 'stream') {
      isStreaming = true;
      streamBadge.textContent = '● Live Video Stream';
      streamBadge.className = 'badge badge-success';
      const cropQuery = currentCrop ? `&crop=${currentCrop.join(',')}` : '';
      screenImg.src = `/api/stream?fps=15${cropQuery}&t=` + Date.now();
    } else {
      isStreaming = false;
      streamBadge.textContent = '○ Snapshot Poll';
      streamBadge.className = 'badge badge-agent';
      refreshSnapshot();
      if (mode !== 'manual') {
        const interval = parseInt(mode, 10) || 1000;
        pollTimer = setInterval(refreshSnapshot, interval);
      }
    }
  }

  function refreshSnapshot() {
    const t0 = performance.now();
    let url = '/api/screenshot?t=' + Date.now();
    if (currentCrop) {
      const [x, y, w, h] = currentCrop;
      url = `/api/crop?x=${x}&y=${y}&w=${w}&h=${h}&t=` + Date.now();
    }
    const tempImg = new Image();
    tempImg.onload = () => {
      screenImg.src = tempImg.src;
      const ms = Math.round(performance.now() - t0);
      latencyDisplay.textContent = `Latency: ${ms}ms`;
    };
    tempImg.src = url;
  }

  document.getElementById('autoRefreshSelect').addEventListener('change', (e) => {
    setStreamMode(e.target.value);
  });
  document.getElementById('btnStreamToggle').addEventListener('click', () => {
    const sel = document.getElementById('autoRefreshSelect');
    if (isStreaming) {
      sel.value = '1000';
      setStreamMode('1000');
    } else {
      sel.value = 'stream';
      setStreamMode('stream');
    }
  });
  document.getElementById('btnRefresh').addEventListener('click', refreshSnapshot);

  // Zoom presets
  document.getElementById('btnZoomOsd').addEventListener('click', () => {
    currentCrop = [0, 0, 360, 300];
    showToast('Zoomed to OSD / Top-Left Area');
    setStreamMode(document.getElementById('autoRefreshSelect').value);
  });
  document.getElementById('btnZoomFull').addEventListener('click', () => {
    currentCrop = null;
    showToast('Reset to Full Desktop Screen');
    setStreamMode(document.getElementById('autoRefreshSelect').value);
  });

  // Action Hotkeys API
  async function sendAction(endpoint, body) {
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      return data;
    } catch (e) {
      console.error('sendAction failed', e);
      return { error: String(e) };
    }
  }

  document.getElementById('btnF2').addEventListener('click', async () => {
    showToast('Sending F2 (Volume Down)...');
    await sendAction('/api/action/volume', { action: 'down', trigger_hud: true });
    updateAudioInfo();
  });
  document.getElementById('btnF3').addEventListener('click', async () => {
    showToast('Sending F3 (Volume Up)...');
    await sendAction('/api/action/volume', { action: 'up', trigger_hud: true });
    updateAudioInfo();
  });
  document.getElementById('btnMute').addEventListener('click', async () => {
    showToast('Toggling Audio Mute...');
    await sendAction('/api/action/volume', { action: 'mute', trigger_hud: true });
    updateAudioInfo();
  });
  document.getElementById('btnFixOsd').addEventListener('click', async () => {
    showToast('Remediating OSD Desynchronization...');
    const res = await sendAction('/api/action/fix_osd', {});
    showToast('OSD & waveOut Synchronized!');
    updateAudioInfo();
  });
  document.getElementById('btnShowHud').addEventListener('click', async () => {
    showToast('Triggering Synchronized Agent HUD...');
    await sendAction('/api/action/hud', { duration: 2.0 });
  });
  document.getElementById('btnSyncAudio').addEventListener('click', updateAudioInfo);

  // Audio and System Polling
  async function updateAudioInfo() {
    try {
      const res = await fetch('/api/info?t=' + Date.now());
      const data = await res.json();
      if (data.system) {
        document.getElementById('systemInfo').textContent = `${data.system.os} | Screen: ${data.screen.w}x${data.screen.h}`;
        naturalW = data.screen.w;
        naturalH = data.screen.h;
      }
      if (data.audio) {
        const a = data.audio;
        const pct = a.volume_pct !== null ? a.volume_pct : 0;
        document.getElementById('volVal').textContent = a.is_muted ? `${pct}% (MUTED)` : `${pct}%`;
        document.getElementById('volBar').style.width = `${pct}%`;
        document.getElementById('volText').textContent = a.is_muted ? 'MUTED' : `${pct}%`;
        document.getElementById('audioDevice').textContent = a.device_name || 'Default';
        document.getElementById('waveoutVal').textContent = a.waveout_vol || 'N/A';
      }
      if (data.osd) {
        const o = data.osd;
        document.getElementById('osdOwner').textContent = o.osd_owner_identified;
        document.getElementById('osdDiagnosisBox').textContent = o.slider_zero_root_cause;
      }
    } catch (e) {
      console.warn('updateAudioInfo error', e);
    }
  }

  // Interactive Screen Click & Inspection
  screenWrapper.addEventListener('mousemove', (e) => {
    const rect = screenImg.getBoundingClientRect();
    const scaleX = (currentCrop ? currentCrop[2] : naturalW) / rect.width;
    const scaleY = (currentCrop ? currentCrop[3] : naturalH) / rect.height;
    const offsetX = currentCrop ? currentCrop[0] : 0;
    const offsetY = currentCrop ? currentCrop[1] : 0;

    const x = Math.round(offsetX + (e.clientX - rect.left) * scaleX);
    const y = Math.round(offsetY + (e.clientY - rect.top) * scaleY);
    screenCoords.textContent = `Pointer: (${x}, ${y}) | Desktop: ${naturalW}x${naturalH}`;
  });

  screenWrapper.addEventListener('click', async (e) => {
    const rect = screenImg.getBoundingClientRect();
    const scaleX = (currentCrop ? currentCrop[2] : naturalW) / rect.width;
    const scaleY = (currentCrop ? currentCrop[3] : naturalH) / rect.height;
    const offsetX = currentCrop ? currentCrop[0] : 0;
    const offsetY = currentCrop ? currentCrop[1] : 0;

    const x = Math.round(offsetX + (e.clientX - rect.left) * scaleX);
    const y = Math.round(offsetY + (e.clientY - rect.top) * scaleY);

    marker.style.left = (e.clientX - rect.left) + 'px';
    marker.style.top = (e.clientY - rect.top) + 'px';
    marker.style.display = 'block';

    const mode = document.getElementById('clickModeSelect').value;
    if (mode === 'click') {
      showToast(`Sent Click to (${x}, ${y})`);
      await sendAction('/api/action/click', { x, y, button: 'left' });
    } else if (mode === 'double') {
      showToast(`Sent Double-Click to (${x}, ${y})`);
      await sendAction('/api/action/click', { x, y, button: 'left', double: true });
    } else {
      // Inspect mode
      document.getElementById('inspCoord').textContent = `(${x}, ${y})`;
      try {
        const res = await fetch(`/api/inspect?x=${x}&y=${y}&t=` + Date.now());
        const data = await res.json();
        renderInspection(data);
      } catch (err) {
        console.error('Inspect error', err);
      }
    }
  });

  function renderInspection(data) {
    if (data.pixel) {
      document.getElementById('hexVal').textContent = data.pixel.hex;
      document.getElementById('colorSwatch').style.backgroundColor = data.pixel.hex;
    }
    if (data.hit_window) {
      const h = data.hit_window;
      document.getElementById('hitHwnd').textContent = `0x${h.hwnd.toString(16)} (${h.hwnd})`;
      document.getElementById('hitClass').textContent = h.class_name;
      document.getElementById('hitTitle').textContent = h.title || '(No Title)';
      document.getElementById('hitProc').textContent = `${h.process_name} [${h.pid}]`;
    } else {
      document.getElementById('hitHwnd').textContent = 'None';
      document.getElementById('hitClass').textContent = '-';
      document.getElementById('hitTitle').textContent = '-';
      document.getElementById('hitProc').textContent = '-';
    }

    const tree = document.getElementById('windowTree');
    tree.innerHTML = '';
    const windows = data.windows || [];
    if (windows.length === 0) {
      tree.innerHTML = '<div style="font-size:0.75rem; color:var(--text-muted);">No covering windows found.</div>';
      return;
    }

    windows.forEach((w) => {
      const node = document.createElement('div');
      node.className = 'window-node';
      node.innerHTML = `
        <div class="window-title">${w.title || '(Untitled)'}</div>
        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">
          Class: <span class="mono">${w.class_name}</span> | PID: ${w.pid} (${w.process_name})
        </div>
        <div style="font-size:0.7rem; color:#9ca3af; margin-top:2px;">
          Rect: ${w.rect.width}x${w.rect.height} @ (${w.rect.left}, ${w.rect.top}) |
          ${w.is_layered ? '<span style="color:#f59e0b">Layered</span>' : ''}
          ${w.is_topmost ? '<span style="color:#10b981">Topmost</span>' : ''}
        </div>
      `;
      tree.appendChild(node);
    });
  }

  // Initial load
  updateAudioInfo();
  setInterval(updateAudioInfo, 3000);
  setStreamMode('stream');
</script>
</body>
</html>
"""
