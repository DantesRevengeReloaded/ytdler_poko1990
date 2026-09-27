const $ = (s) => document.querySelector(s);

const defaultStatus = {
  job: 'idle',
  jobLabel: 'Idle',
  phase: 'idle',
  phaseLabel: 'Idle',
  message: 'No work in progress',
  progress: 0,
  indeterminate: false,
  countLabel: '-',
};

let statusState = { ...defaultStatus };
const jobLabels = { single: 'Single download', playlist: 'Playlist download', spotify: 'Spotify download', idle: 'Idle' };
const POLL_INTERVAL_MS = 500;
const AUTO_REFRESH_MS = 20000;
const SETTINGS_KEY = 'poko_settings_v1';
let progressTimer = null;
let autoRefreshTimer = null;
let latestStorage = [];
let isSettingsOpen = false;
let settingsPopoverInitialized = false;
const settingsState = {
  autoRefresh: true,
  density: 'comfortable',
  animations: true,
  reduceMotion: false,
  sizeFormat: 'adaptive',
  timeFormat: 'relative',
  theme: 'dark'
};
const LIBRARY_PAGE_SIZE = 60;
const libraryState = {
  allFiles: [],
  groups: [],
  selectedKey: '',
  selectedCategory: 'all',
  selectedSubfolder: 'all',
  selectedSort: 'default',
  visibleCount: LIBRARY_PAGE_SIZE,
};
const playerState = {
  queue: [],
  currentIndex: -1,
  currentPath: '',
  currentTrack: null,
  isPlaying: false,
};
const HISTORY_PAGE_SIZE = 60;
const historyState = {
  tab: 'downloads',
  entries: [],
  groups: [],
  selectedGroup: 'all',
  visibleCount: HISTORY_PAGE_SIZE,
};

function createJobId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return `job-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function ensureStatusVisible() {
  const panel = $('#live-status');
  if (!panel) return;
  panel.style.display = 'block';
}

function renderStatus() {
  ensureStatusVisible();
  const progressEl = $('#live-progress');
  const textEl = $('#live-progress-text');
  const jobEl = $('#status-job-label');
  const phaseEl = $('#status-phase-label');
  const countsEl = $('#status-counts');
  const pill = $('#status-pill');
  const pillLabel = $('#status-pill-label');
  const liveStatus = $('#live-status');
  if (!progressEl || !textEl || !jobEl || !phaseEl || !countsEl || !pill || !pillLabel || !liveStatus) return;

  progressEl.classList.toggle('indeterminate', !!statusState.indeterminate);
  progressEl.style.width = statusState.indeterminate ? '38%' : `${statusState.progress || 0}%`;
  ['progress-fill--single', 'progress-fill--playlist', 'progress-fill--spotify'].forEach((c) => progressEl.classList.remove(c));
  if (statusState.job && statusState.job !== 'idle') progressEl.classList.add(`progress-fill--${statusState.job}`);

  textEl.textContent = statusState.message;
  jobEl.textContent = statusState.jobLabel;
  phaseEl.textContent = statusState.phaseLabel;
  countsEl.textContent = statusState.countLabel || '-';

  const working = statusState.job && !['idle', 'done', 'error'].includes(statusState.phase);
  const completed = statusState.phase === 'done';
  const errored = statusState.phase === 'error';

  pill.classList.remove('pill-busy', 'pill-done', 'pill-error');
  liveStatus.classList.remove('is-active', 'is-done', 'is-error');

  if (working) {
    pillLabel.textContent = 'In Progress';
    pill.classList.add('pill-busy');
    liveStatus.classList.add('is-active');
  } else if (completed) {
    pillLabel.textContent = 'Completed';
    pill.classList.add('pill-done');
    liveStatus.classList.add('is-done');
  } else if (errored) {
    pillLabel.textContent = 'Error';
    pill.classList.add('pill-error');
    liveStatus.classList.add('is-error');
  } else {
    pillLabel.textContent = 'Idle';
  }
}

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}');
    Object.assign(settingsState, saved || {});
  } catch {}
}

function saveSettings() {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settingsState));
  } catch {}
}

function applySettings() {
  const isLight = settingsState.theme === 'light';
  document.body.classList.toggle('theme-light', isLight);
  document.body.classList.toggle('compact', settingsState.density === 'compact');
  document.body.classList.toggle('no-anim', !settingsState.animations || settingsState.reduceMotion);
  
  updateAmbientLayer();

  if (!settingsState.animations || settingsState.reduceMotion) {
    closeSettings();
  }
}

function updateAmbientLayer() {
  if (window.lightAnimInterval) clearInterval(window.lightAnimInterval);
  const ambient = document.querySelector('.ambient-layer');
  if (!ambient) return;
  
  const isLight = settingsState.theme === 'light';
  if (isLight && settingsState.animations !== false && !settingsState.reduceMotion) {
    ambient.style.display = 'block';
    const srv = document.getElementById('service-type') ? document.getElementById('service-type').value : 'single';
    let c1 = '77, 228, 255'; // default cyan
    let c2 = '132, 112, 255'; // default purple
    
    if (srv === 'single') {
      c1 = '50, 213, 131'; // green
      c2 = '77, 228, 255'; // cyan
    } else if (srv === 'playlist') {
      c1 = '89, 183, 255'; // blue
      c2 = '160, 120, 255'; // purple
    } else if (srv === 'spotify') {
      c1 = '29, 185, 84'; // spotify green
      c2 = '50, 213, 131'; // light green
    }
    
    let angle = 0;
    window.lightAnimInterval = setInterval(() => {
      angle = (angle + 0.2) % 360;
      const x1 = 50 + 35 * Math.cos(angle * Math.PI / 180);
      const y1 = 50 + 35 * Math.sin(angle * Math.PI / 180);
      const x2 = 50 + 35 * Math.cos((angle + 180) * Math.PI / 180);
      const y2 = 50 + 35 * Math.sin((angle + 180) * Math.PI / 180);
      ambient.style.background = `radial-gradient(circle at ${x1}% ${y1}%, rgba(${c1}, 0.15), transparent 50%), radial-gradient(circle at ${x2}% ${y2}%, rgba(${c2}, 0.15), transparent 50%)`;
    }, 50);
  } else {
    ambient.style.display = '';
    ambient.style.background = '';
  }
}

function positionSettingsPopover() {
  const trigger = $('#settings-trigger');
  const panel = $('#settings-panel');
  if (!trigger || !panel || panel.hidden) return;

  const rect = trigger.getBoundingClientRect();
  const panelWidth = Math.min(420, Math.max(320, window.innerWidth - 24));
  panel.style.width = `${panelWidth}px`;
  panel.style.left = '0px';
  panel.style.top = '0px';
  const panelRect = panel.getBoundingClientRect();
  const gutter = 12;
  const left = Math.min(
    Math.max(gutter, rect.right - panelRect.width),
    window.innerWidth - panelRect.width - gutter,
  );
  const top = Math.min(rect.bottom + 10, window.innerHeight - panelRect.height - gutter);
  panel.style.left = `${left}px`;
  panel.style.top = `${Math.max(gutter, top)}px`;
}

function renderSettingsVisibility() {
  const trigger = $('#settings-trigger');
  const panel = $('#settings-panel');
  const backdrop = $('#settings-backdrop');
  if (!trigger || !panel || !backdrop) return;

  panel.hidden = !isSettingsOpen;
  backdrop.hidden = !isSettingsOpen;
  trigger.setAttribute('aria-expanded', String(isSettingsOpen));
  document.body.classList.toggle('settings-open', isSettingsOpen);

  if (isSettingsOpen) {
    positionSettingsPopover();
  } else {
    panel.style.left = '';
    panel.style.top = '';
    panel.style.width = '';
  }
}

function openSettings() {
  if (isSettingsOpen) return;
  isSettingsOpen = true;
  renderSettingsVisibility();
}

function closeSettings() {
  if (!isSettingsOpen) return;
  isSettingsOpen = false;
  renderSettingsVisibility();
}

function toggleSettings() {
  if (isSettingsOpen) {
    closeSettings();
  } else {
    openSettings();
  }
}

function initSettingsPopover() {
  if (settingsPopoverInitialized) return;
  const trigger = $('#settings-trigger');
  const panel = $('#settings-panel');
  const backdrop = $('#settings-backdrop');
  const closeBtn = $('#settings-close');
  if (!trigger || !panel || !backdrop || !closeBtn) return;
  settingsPopoverInitialized = true;

  trigger.addEventListener('click', (event) => {
    event.preventDefault();
    toggleSettings();
  });

  closeBtn.addEventListener('click', () => {
    closeSettings();
  });

  window.addEventListener('pointerdown', (event) => {
    if (!isSettingsOpen) return;
    const target = event.target;
    if (trigger.contains(target)) return;
    if (panel.contains(target)) return;
    closeSettings();
  }, true);

  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isSettingsOpen) closeSettings();
  });

  window.addEventListener('resize', () => {
    if (isSettingsOpen) positionSettingsPopover();
  });
  window.addEventListener('scroll', () => {
    if (isSettingsOpen) positionSettingsPopover();
  }, true);

  renderSettingsVisibility();
}

function setStatus(job, patch = {}) {
  const nextJob = job || statusState.job;
  statusState = {
    ...statusState,
    job: nextJob,
    jobLabel: jobLabels[nextJob] || statusState.jobLabel,
    ...patch,
  };
  renderStatus();
}

function stopPolling() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
}

function startPolling(job, jobId) {
  stopPolling();
  const tick = async () => {
    try {
      const res = await fetch(`/api/v1/downloads/progress/${jobId}`);
      if (res.status === 404) return;
      if (!res.ok) throw new Error('progress fetch failed');
      const data = await res.json();
      const total = data.total || 0;
      const completed = data.completed || 0;
      const percent = data.progress_percent != null ? data.progress_percent : total ? (completed / total) * 100 : statusState.progress;
      const label = data.phase === 'done' ? 'Completed' : data.phase === 'error' ? 'Error' : data.phase || 'Working';
      const counts = total ? `${completed}/${total}` : '-';
      let message = data.message || 'Working...';

      if (data.job_type === 'playlist' && total) {
        message = `${data.playlist_title || 'Playlist'}: ${completed}/${total} items`;
      } else if (data.job_type === 'spotify' && total) {
        message = `${data.playlist_title || 'Spotify list'}: ${completed}/${total} tracks`;
      }

      setStatus(job, {
        phase: data.phase,
        phaseLabel: label,
        message,
        progress: percent,
        indeterminate: !total,
        countLabel: counts,
      });

      if (data.phase === 'done' || data.phase === 'error') stopPolling();
    } catch {
      stopPolling();
    }
  };

  tick();
  progressTimer = setInterval(tick, POLL_INTERVAL_MS);
}

async function postDownload() {
  const url = $('#unified-url').value.trim();
  if (!isValidUrl(url, ['https://www.youtube.com/', 'https://youtube.com/'])) {
    showToast('Enter a valid YouTube URL.', 'error');
    return;
  }

  clearResult();
  const jobId = createJobId();
  setButtonLoading('#unified-submit', true, 'Download');
  setStatus('single', {
    phase: 'metadata',
    phaseLabel: 'Fetching metadata',
    message: 'Reading video details...',
    progress: 12,
    indeterminate: true,
    countLabel: '-',
  });
  startPolling('single', jobId);

  try {
    const res = await fetch('/api/v1/downloads/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        kind: $('#unified-kind').value,
        resolution: $('#unified-resolution').value,
        bitrate: $('#unified-bitrate').value,
        job_id: jobId,
      }),
    });

    if (!res.ok) throw new Error(await readApiError(res, 'Request failed'));

    const data = await res.json();
    renderResult(data, 'single');
    setStatus('single', {
      phase: 'done',
      phaseLabel: 'Completed',
      message: `Saved ${basename(data.filepath || data.title || 'file')}`,
      progress: 100,
      indeterminate: false,
      countLabel: '1/1',
    });

    clearInputs(['#unified-url']);
    showToast('Download complete', 'success');
    await refreshData();
  } catch (err) {
    const msg = err.message || 'Download failed';
    setStatus('single', { phase: 'error', phaseLabel: 'Error', message: msg, progress: 0, indeterminate: false, countLabel: '-' });
    showToast(msg, 'error');
  }

  stopPolling();
  setButtonLoading('#unified-submit', false, 'Download');
  $('#unified-status').textContent = '';
}

async function postPlaylist() {
  const url = $('#unified-url').value.trim();
  if (!isValidUrl(url, ['https://www.youtube.com/playlist', 'https://youtube.com/playlist'])) {
    showToast('Enter a valid YouTube playlist URL.', 'error');
    return;
  }

  clearResult();
  const jobId = createJobId();
  setButtonLoading('#unified-submit', true, 'Download Playlist');
  setStatus('playlist', {
    phase: 'metadata',
    phaseLabel: 'Fetching metadata',
    message: 'Reading playlist details...',
    progress: 10,
    indeterminate: true,
    countLabel: '-',
  });
  startPolling('playlist', jobId);

  try {
    const res = await fetch('/api/v1/downloads/playlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        kind: $('#unified-kind').value,
        resolution: $('#unified-resolution').value,
        bitrate: $('#unified-bitrate').value,
        job_id: jobId,
      }),
    });

    if (!res.ok) throw new Error(await readApiError(res, 'Playlist request failed'));

    const data = await res.json();
    renderResult(data, 'playlist');
    setStatus('playlist', {
      phase: 'done',
      phaseLabel: 'Completed',
      message: `Downloaded ${data.count || 0} items from ${data.playlist_title || 'playlist'}`,
      progress: 100,
      indeterminate: false,
      countLabel: `${data.count || 0}/${data.count || 0}`,
    });

    clearInputs(['#unified-url']);
    showToast(`Playlist downloaded (${data.count || 0} items)`, 'success');
    await refreshData();
  } catch (err) {
    const msg = err.message || 'Playlist failed';
    setStatus('playlist', { phase: 'error', phaseLabel: 'Error', message: msg, progress: 0, indeterminate: false, countLabel: '-' });
    showToast(msg, 'error');
  }

  stopPolling();
  setButtonLoading('#unified-submit', false, 'Download Playlist');
  $('#unified-status').textContent = '';
}

async function mirrorSpotifyPlaylist() {
  const url = $('#unified-url').value.trim();
  if (!isValidUrl(url, ['https://open.spotify.com/', 'spotify:'])) {
    showToast('Enter a valid Spotify URL.', 'error');
    return;
  }

  clearResult();
  const jobId = createJobId();
  setButtonLoading('#unified-submit', true, 'Download Spotify list');
  setStatus('spotify', {
    phase: 'metadata',
    phaseLabel: 'Fetching Spotify',
    message: 'Gathering collection details...',
    progress: 18,
    indeterminate: true,
    countLabel: '-',
  });
  startPolling('spotify', jobId);

  try {
    const kind = $('#unified-kind').value;
    const res = await fetch('/api/v1/spotify/mirror', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        kind,
        resolution: $('#unified-resolution').value,
        bitrate: $('#unified-bitrate').value || '192',
        job_id: jobId,
      }),
    });

    if (!res.ok) throw new Error(await readApiError(res, 'Spotify mirror failed', 'spotify'));

    const data = await res.json();
    renderResult(data, 'spotify');
    const count = data.track_count || 0;
    const done = data.downloaded || 0;

    setStatus('spotify', {
      phase: 'done',
      phaseLabel: 'Completed',
      message: `${data.playlist_title || 'Spotify list'}: ${done}/${count} tracks`,
      progress: 100,
      indeterminate: false,
      countLabel: `${done}/${count || '?'}`,
    });

    $('#unified-status').textContent = `${data.playlist_title || 'Spotify list'}: ${done}/${count} tracks.`;
    clearInputs(['#unified-url']);
    showToast(`${done}/${count} tracks mirrored`, 'success');
    await refreshData();
  } catch (err) {
    const msg = err.message || 'Spotify mirror failed';
    $('#unified-status').textContent = msg;
    setStatus('spotify', { phase: 'error', phaseLabel: 'Error', message: msg, progress: 0, indeterminate: false, countLabel: '-' });
    showToast(msg, 'error');
  }

  setButtonLoading('#unified-submit', false, 'Download Spotify list');
  stopPolling();
}

async function loadStats() {
  const statsEl = $('#stats');
  if (!statsEl) return;

  try {
    const [statsRes, breakdownRes, dHistRes, sHistRes] = await Promise.all([
      fetch('/api/v1/stats'),
      fetch('/api/v1/stats/breakdown'),
      fetch('/api/v1/downloads/history?limit=1'),
      fetch('/api/v1/spotify/history?limit=1'),
    ]);

    if (!statsRes.ok) throw new Error('Failed to load stats');
    const stats = await statsRes.json();
    const dHist = dHistRes.ok ? await dHistRes.json() : { total: 0, items: [] };
    const sHist = sHistRes.ok ? await sHistRes.json() : { total: 0, items: [] };

    statsEl.innerHTML = `
      <div class="stat-tile"><div class="label">Total items</div><div class="value">${stats.total_items}</div></div>
      <div class="stat-tile"><div class="label">Total size</div><div class="value">${formatSize(stats.total_size_mb)}</div></div>
    `;

    if (breakdownRes.ok) {
      const bd = await breakdownRes.json();
      latestStorage = bd.storage || [];
      renderOutputFolders(latestStorage);
    }

    renderQueueSummary({ downloads: dHist.total || 0, spotify: sHist.total || 0, lastDownload: dHist.items?.[0], lastSpotify: sHist.items?.[0] });
  } catch (err) {
    statsEl.innerHTML = `<div class="state-card error">Stats error: ${escapeHtml(err.message)}</div>`;
  }
}

async function loadOutputRoot() {
  const rootEl = $('#output-root');
  if (!rootEl) return;

  try {
    const res = await fetch('/api/v1/files/root');
    if (!res.ok) throw new Error('Could not resolve output root');
    const data = await res.json();
    rootEl.textContent = data.root;
    rootEl.title = data.root;
  } catch {
    rootEl.textContent = 'Configured downloads directory';
    rootEl.title = 'Configured downloads directory';
  }
}

function renderOutputFolders(storage) {
  const list = $('#output-folders');
  if (!list) return;

  if (!storage || !storage.length) {
    list.innerHTML = '<div class="state-card">No output folders detected yet.</div>';
    return;
  }

  list.innerHTML = storage.map((item) => `
    <div class="folder-item">
      <strong>${escapeHtml(item.directory)}</strong>
      <span>${item.file_count} files · ${formatSize(item.size_mb)}</span>
    </div>
  `).join('');
}

function renderQueueSummary(data) {
  const el = $('#queue-summary');
  if (!el) return;

  const lastD = data.lastDownload ? formatDate(data.lastDownload.downloaded_date) : 'None';
  const lastS = data.lastSpotify ? formatDate(data.lastSpotify.downloaded_date) : 'None';

  el.innerHTML = `
    <div class="queue-row"><span>Last download</span><strong>${escapeHtml(lastD)}</strong></div>
    <div class="queue-row"><span>Last Spotify mirror</span><strong>${escapeHtml(lastS)}</strong></div>
  `;
}

async function loadLibrary(isSilent = false) {
  const body = $('#library-body');
  const selector = $('#library-playlist-select');
  const summary = $('#library-summary');
  const loadMoreBtn = $('#library-load-more');
  if (!body) return;

  if (!isSilent && body.innerHTML.trim() === '') {
    body.innerHTML = '<div class="state-card">Loading files...</div>';
    if (summary) summary.textContent = 'Loading library...';
  }

  try {
    const res = await fetch('/api/v1/files');
    if (!res.ok) throw new Error('Failed to load library');
    const data = await res.json();
    const files = data.files || [];
    libraryState.allFiles = files;
    libraryState.groups = buildLibraryGroups(files);

    if (!files.length) {
      clearCurrentTrack();
      playerState.queue = [];
      renderPlayerState();
      body.innerHTML = '<div class="state-card">No files yet. Start with a single or playlist download.</div>';
      if (selector) selector.innerHTML = '<option value="all">All playlists</option>';
      if (summary) summary.textContent = 'No tracks found.';
      if (loadMoreBtn) loadMoreBtn.hidden = true;
      return;
    }

    syncLibrarySelection();
    renderLibrarySelector();
    renderLibraryRows();
  } catch (err) {
    body.innerHTML = `<div class="state-card error">Library error: ${escapeHtml(err.message)}</div>`;
    if (summary) summary.textContent = 'Library failed to load.';
    if (loadMoreBtn) loadMoreBtn.hidden = true;
  }
}

function buildLibraryGroups(files) {
  // Group by category (singles, playlists, spotify)
  const cats = {
    'all': { label: 'All Downloads', subfolders: new Map() },
    'singledls': { label: 'Singles', subfolders: new Map() },
    'playlists': { label: 'Playlists', subfolders: new Map() },
    'spotify_playlists': { label: 'Spotify', subfolders: new Map() }
  };
  
  files.forEach(file => {
    const c = cats[file.category] || cats['all'];
    const parts = String(file.path || '').split('/');
    const folder = parts.length > 1 ? parts[1] : 'Root';
    
    // Add to specific category
    if (!c.subfolders.has(folder)) c.subfolders.set(folder, []);
    c.subfolders.get(folder).push(file);
    
    // Add to 'all'
    if (!cats['all'].subfolders.has('all')) cats['all'].subfolders.set('all', []);
    cats['all'].subfolders.get('all').push(file);
  });
  
  return cats;
}

function syncLibrarySelection() {
  if (!libraryState.selectedCategory) libraryState.selectedCategory = 'all';
  if (!libraryState.selectedSubfolder) libraryState.selectedSubfolder = 'all';
  libraryState.visibleCount = LIBRARY_PAGE_SIZE;
}

function renderLibrarySelector() {
  const catSelect = $('#library-playlist-select');
  const subSelect = $('#library-subfolder-select');
  if (!catSelect || !subSelect) return;
  
  if (catSelect.options.length === 0) {
    catSelect.innerHTML = Object.keys(libraryState.groups).map(k => 
      `<option value="${k}">${libraryState.groups[k].label}</option>`
    ).join('');
  }
  catSelect.value = libraryState.selectedCategory;
  
  const currentCat = libraryState.groups[libraryState.selectedCategory];
  if (libraryState.selectedCategory === 'all' || currentCat.subfolders.size <= 1) {
    subSelect.innerHTML = '<option value="all">No folders</option>';
    subSelect.disabled = true;
    libraryState.selectedSubfolder = 'all';
  } else {
    subSelect.disabled = false;
    let html = '<option value="all">All</option>';
    for (const [folder, files] of currentCat.subfolders.entries()) {
      if (folder === 'all') continue;
      html += `<option value="${escapeAttr(folder)}">${escapeHtml(folder)} (${files.length})</option>`;
    }
    subSelect.innerHTML = html;
    if (currentCat.subfolders.has(libraryState.selectedSubfolder)) {
      subSelect.value = libraryState.selectedSubfolder;
    } else {
      subSelect.value = 'all';
      libraryState.selectedSubfolder = 'all';
    }
  }
}

function getSelectedLibraryGroup() {
  const cat = libraryState.groups[libraryState.selectedCategory];
  if (!cat) return { files: [] };
  
  if (libraryState.selectedSubfolder === 'all') {
    let allFiles = [];
    for (const files of cat.subfolders.values()) {
      allFiles = allFiles.concat(files);
    }
    // Remove duplicates if any
    return { files: [...new Set(allFiles)] };
  }
  
  return { files: cat.subfolders.get(libraryState.selectedSubfolder) || [] };
}



function getLibraryFileMeta(file) {
  const parts = String(file.path || '').split('/');
  const folderName = parts[1] || file.category || 'library';
  return `${folderName} · ${formatSize(file.size_mb)}`;
}

function renderPlayerState() {
  const shell = $('#global-player');
  const title = $('#player-title');
  const meta = $('#player-meta');
  const toggle = $('#player-toggle');
  const prev = $('#player-prev');
  const next = $('#player-next');
  const seek = $('#player-seek');
  const currentTime = $('#player-current-time');
  const duration = $('#player-duration');
  const hasTrack = !!playerState.currentTrack;

  if (!shell || !title || !meta || !toggle || !prev || !next || !seek || !currentTime || !duration) return;

  // shell.hidden = !hasTrack; // Removed because global player should always be visible
  title.textContent = hasTrack ? playerState.currentTrack.name : 'No track selected';
  meta.textContent = hasTrack ? getLibraryFileMeta(playerState.currentTrack) : 'Choose a song from the library';
  const iconPlay = toggle.querySelector('.icon-play');
  const iconPause = toggle.querySelector('.icon-pause');
  if (iconPlay && iconPause) {
    iconPlay.style.display = playerState.isPlaying ? 'none' : 'block';
    iconPause.style.display = playerState.isPlaying ? 'block' : 'none';
    toggle.title = playerState.isPlaying ? 'Pause' : 'Play';
  } else {
    toggle.textContent = playerState.isPlaying ? 'Pause' : 'Play';
  }
  
  toggle.disabled = !hasTrack;
  prev.disabled = !hasTrack || playerState.currentIndex <= 0;
  next.disabled = !hasTrack || playerState.currentIndex < 0 || playerState.currentIndex >= playerState.queue.length - 1;

  if (!hasTrack) {
    seek.max = '0';
    seek.value = '0';
    currentTime.textContent = '0:00';
    duration.textContent = '0:00';
  }
}

function syncPlayerWithLibrary(files = null) {
  const sourceFiles = files || getSelectedLibraryGroup()?.files || [];
  playerState.queue = sourceFiles.filter((file) => file.type === 'audio');
  if (!playerState.currentPath) {
    playerState.currentIndex = -1;
    playerState.currentTrack = null;
    renderPlayerState();
    return;
  }

  const currentTrack = libraryState.allFiles.find((file) => file.path === playerState.currentPath);
  if (!currentTrack) {
    clearCurrentTrack();
    renderPlayerState();
    return;
  }

  playerState.currentTrack = currentTrack;
  playerState.currentIndex = playerState.queue.findIndex((file) => file.path === playerState.currentPath);
  renderPlayerState();
}

function playTrackAt(index) {
  const player = $('#audio-player');
  const track = playerState.queue[index];
  if (!player || !track) return;

  playerState.currentTrack = track;
  playerState.currentPath = track.path;
  playerState.currentIndex = index;

  if (player.dataset.path !== track.path) {
    player.src = `/api/v1/files/stream/${encodeFilePath(track.path)}`;
    player.dataset.path = track.path;
  }

  playerState.isPlaying = true;
  renderPlayerState();
  renderLibraryRows();

  const playPromise = player.play();
  if (playPromise && typeof playPromise.catch === 'function') {
    playPromise.catch(() => {
      playerState.isPlaying = false;
      renderPlayerState();
      renderLibraryRows();
    });
  }
}

function playTrackByPath(path) {
  if (!path) return;
  const index = playerState.queue.findIndex((file) => file.path === path);
  if (index === -1) return;

  const player = $('#audio-player');
  if (player && playerState.currentPath === path && player.paused) {
    player.play();
    return;
  }

  playTrackAt(index);
}

function clearCurrentTrack() {
  const player = $('#audio-player');
  if (player) {
    player.pause();
    player.removeAttribute('src');
    player.dataset.path = '';
    player.load();
  }

  playerState.currentIndex = -1;
  playerState.currentPath = '';
  playerState.currentTrack = null;
  playerState.isPlaying = false;
}

function togglePlayerPlayback() {
  const player = $('#audio-player');
  if (!player || !playerState.currentTrack) return;

  if (player.paused) {
    player.play();
  } else {
    player.pause();
  }
}

function playPreviousTrack() {
  const player = $('#audio-player');
  if (player && player.currentTime > 3) {
    player.currentTime = 0;
    return;
  }
  if (playerState.currentIndex > 0) playTrackAt(playerState.currentIndex - 1);
}

function playNextTrack() {
  if (playerState.currentIndex >= 0 && playerState.currentIndex < playerState.queue.length - 1) {
    playTrackAt(playerState.currentIndex + 1);
  }
}

function renderLibraryRows() {
  const body = $('#library-body');
  const summary = $('#library-summary');
  const loadMoreBtn = $('#library-load-more');
  if (!body) return;

  const selected = getSelectedLibraryGroup();
  if (!selected || !selected.files || !selected.files.length) {
    playerState.queue = [];
    renderPlayerState();
    body.innerHTML = '<div class="state-card">No tracks available.</div>';
    if (summary) summary.textContent = 'No tracks available.';
    if (loadMoreBtn) loadMoreBtn.hidden = true;
    return;
  }

  // Sort files before taking visible subset
  let sortedFiles = [...selected.files];
  if (libraryState.selectedSort === 'a-z') {
    sortedFiles.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  } else if (libraryState.selectedSort === 'z-a') {
    sortedFiles.sort((a, b) => (b.name || '').localeCompare(a.name || ''));
  } else if (libraryState.selectedSort === 'newest') {
    sortedFiles.sort((a, b) => (b.modified || 0) - (a.modified || 0));
  } else if (libraryState.selectedSort === 'oldest') {
    sortedFiles.sort((a, b) => (a.modified || 0) - (b.modified || 0));
  }

  syncPlayerWithLibrary(sortedFiles);

  const visible = sortedFiles.slice(0, libraryState.visibleCount);
  
  const totalSize = selected.files.reduce((acc, item) => acc + (Number(item.size_mb) || 0), 0);
  const latestModified = selected.files.reduce((max, item) => Math.max(max, Number(item.modified) || 0), 0);
  const latest = latestModified ? formatDate(latestModified) : '-';
  const label = libraryState.selectedCategory === 'all' ? 'All Downloads' : 
                libraryState.groups[libraryState.selectedCategory]?.label + 
                (libraryState.selectedSubfolder === 'all' ? '' : ` / ${libraryState.selectedSubfolder}`);

  if (summary) {
    summary.textContent = `${label} · ${selected.files.length} tracks · ${totalSize.toFixed(2)} MB · Updated ${latest}`;
  }

  if (!visible.length) {
    body.innerHTML = '<div class="state-card">No tracks in this playlist.</div>';
    if (loadMoreBtn) loadMoreBtn.hidden = true;
    return;
  }

  body.innerHTML = visible.map((f) => {
    const isAudio = f.type === 'audio';
    const isActive = f.path === playerState.currentPath;
    const badge = isActive ? (playerState.isPlaying ? 'Playing' : 'Paused') : (isAudio ? 'Audio' : 'Video');
    return `
      <div
        class="lib-row${isAudio ? ' is-playable' : ' is-disabled'}${isActive ? ' is-active' : ''}"
        data-path="${escapeAttr(f.path)}"
        data-type="${escapeAttr(f.type)}"
        ${isAudio ? `role="button" tabindex="0" aria-label="Play ${escapeAttr(f.name)}"` : 'aria-disabled="true"'}
      >
        <div class="lib-meta">
          <span class="lib-name" title="${escapeAttr(f.name)}">${escapeHtml(f.name)}</span>
          <span class="lib-info">${escapeHtml(getLibraryFileMeta(f))}</span>
        </div>
        <span class="lib-badge${isActive ? ' is-live' : ''}">${escapeHtml(badge)}</span>
      </div>
    `;
  }).join('');

  if (loadMoreBtn) {
    loadMoreBtn.hidden = libraryState.visibleCount >= selected.files.length;
  }
}

function encodeFilePath(path) {
  return path.split('/').map(encodeURIComponent).join('/');
}

async function loadHistory() {
  const body = $('#history-body');
  const sourceSelect = $('#history-source-select');
  const groupSelect = $('#history-group-select');
  const summary = $('#history-summary');
  const loadMoreBtn = $('#history-load-more');
  if (!body) return;
  body.innerHTML = '<div class="state-card">Loading history...</div>';
  if (summary) summary.textContent = 'Loading history summary...';

  historyState.tab = sourceSelect ? sourceSelect.value : historyState.tab;

  try {
    const endpoint = historyState.tab === 'spotify'
      ? '/api/v1/spotify/history?limit=200'
      : '/api/v1/downloads/history?limit=200';
    const res = await fetch(endpoint);
    if (!res.ok) throw new Error('Failed to load history');
    const data = await res.json();
    const items = data.items || [];

    historyState.entries = items;
    historyState.groups = buildHistoryGroups(historyState.tab, items);
    syncHistorySelection();
    renderHistoryGroupSelector();
    renderHistoryRows();

    if (!items.length) {
      if (historyState.tab === 'spotify') {
        body.innerHTML = '<div class="state-card">No Spotify downloads yet.</div>';
      } else {
        body.innerHTML = '<div class="state-card">No downloads yet.</div>';
      }
      if (summary) summary.textContent = 'No history entries found.';
      if (loadMoreBtn) loadMoreBtn.hidden = true;
    } else {
      const active = historyState.groups.find((g) => g.key === historyState.selectedGroup);
      if (summary && active) {
        summary.textContent = `${active.label} · ${active.items.length} entries · ${formatSize(active.totalSize) || '0 MB'} · Latest ${formatDate(active.latestDate)}`;
      }
    }
  } catch (err) {
    body.innerHTML = `<div class="state-card error">History error: ${escapeHtml(err.message)}</div>`;
    if (summary) summary.textContent = 'History failed to load.';
    if (groupSelect) groupSelect.innerHTML = '';
    if (loadMoreBtn) loadMoreBtn.hidden = true;
  }
}

function buildHistoryGroups(tab, items) {
  const map = new Map();

  const addToGroup = (key, label, item) => {
    if (!map.has(key)) map.set(key, { key, label, items: [] });
    map.get(key).items.push(item);
  };

  items.forEach((item) => {
    if (tab === 'spotify') {
      const playlist = item.playlist_title || 'Unknown playlist';
      addToGroup(`playlist:${playlist}`, `Playlist · ${playlist}`, item);
    } else {
      const kind = item.type || 'other';
      addToGroup(`kind:${kind}`, `Type · ${kind}`, item);
    }
  });

  const groups = Array.from(map.values()).map((group) => {
    const totalSize = group.items.reduce((acc, item) => acc + (Number(item.size_mb) || 0), 0);
    const latestDate = group.items.reduce((latest, item) => {
      const ts = new Date(item.downloaded_date || 0).getTime();
      return Math.max(latest, Number.isFinite(ts) ? ts : 0);
    }, 0);
    return { ...group, totalSize, latestDate };
  }).sort((a, b) => b.items.length - a.items.length || a.label.localeCompare(b.label));

  const allTotalSize = items.reduce((acc, item) => acc + (Number(item.size_mb) || 0), 0);
  const allLatest = items.reduce((latest, item) => {
    const ts = new Date(item.downloaded_date || 0).getTime();
    return Math.max(latest, Number.isFinite(ts) ? ts : 0);
  }, 0);

  groups.unshift({
    key: 'all',
    label: 'All entries',
    items,
    totalSize: allTotalSize,
    latestDate: allLatest,
  });

  return groups;
}

function syncHistorySelection() {
  const keys = new Set(historyState.groups.map((g) => g.key));
  if (!keys.has(historyState.selectedGroup)) {
    const nonAll = historyState.groups.find((g) => g.key !== 'all');
    historyState.selectedGroup = nonAll ? nonAll.key : 'all';
  }
  historyState.visibleCount = HISTORY_PAGE_SIZE;
}

function renderHistoryGroupSelector() {
  const groupSelect = $('#history-group-select');
  if (!groupSelect) return;
  groupSelect.innerHTML = historyState.groups.map((group) => (
    `<option value="${escapeAttr(group.key)}">${escapeHtml(group.label)} (${group.items.length})</option>`
  )).join('');
  groupSelect.value = historyState.selectedGroup;
}

function renderHistoryRows() {
  const body = $('#history-body');
  const summary = $('#history-summary');
  const loadMoreBtn = $('#history-load-more');
  if (!body) return;

  const active = historyState.groups.find((g) => g.key === historyState.selectedGroup) || historyState.groups[0];
  if (!active) {
    body.innerHTML = '<div class="state-card">No history entries found.</div>';
    if (summary) summary.textContent = 'No history entries found.';
    if (loadMoreBtn) loadMoreBtn.hidden = true;
    return;
  }

  const visible = active.items.slice(0, historyState.visibleCount);
  if (summary) {
    summary.textContent = `${active.label} · ${active.items.length} entries · ${formatSize(active.totalSize) || '0 MB'} · Latest ${formatDate(active.latestDate)}`;
  }

  if (!visible.length) {
    body.innerHTML = '<div class="state-card">No entries in this group.</div>';
    if (loadMoreBtn) loadMoreBtn.hidden = true;
    return;
  }

  if (historyState.tab === 'spotify') {
    body.innerHTML = visible.map((item) => `
      <div class="history-row">
        <div class="history-meta">
          <span class="history-title" title="${escapeAttr(item.track_title || 'Unknown')}">${escapeHtml(item.track_title || 'Unknown')}</span>
          <span class="history-sub">${escapeHtml(item.artist || '')} · ${escapeHtml(item.playlist_title || '')} · <span class="history-status ${item.status === 'downloaded' ? 'ok' : 'fail'}">${escapeHtml(item.status || '')}</span></span>
        </div>
        <span class="history-date">${formatDate(item.downloaded_date)}</span>
      </div>
    `).join('');
  } else {
    body.innerHTML = visible.map((item) => `
      <div class="history-row">
        <div class="history-meta">
          <span class="history-title" title="${escapeAttr(item.title || 'Unknown')}">${escapeHtml(item.title || 'Unknown')}</span>
          <span class="history-sub">${escapeHtml(item.type || '')} · ${formatSize(item.size_mb || 0)} · ${(item.time_length || 0).toFixed(1)} min</span>
        </div>
        <span class="history-date">${formatDate(item.downloaded_date)}</span>
      </div>
    `).join('');
  }

  if (loadMoreBtn) {
    loadMoreBtn.hidden = historyState.visibleCount >= active.items.length;
  }
}



function renderResult(data, variant) {
  const body = $('#result-body');
  const kindBadge = $('#result-kind');
  const result = $('#result');
  if (!body || !kindBadge || !result) return;

  if (variant === 'playlist') {
    const items = data.items || [];
    const count = data.count != null ? data.count : items.length;
    kindBadge.textContent = `${count} items`;
    body.innerHTML = [
      rowMarkup('Playlist', data.playlist_title || 'Playlist'),
      rowMarkup('Files saved', `${count}`),
      rowMarkup('Type', items[0]?.kind || 'playlist'),
      rowMarkup('Duration', data.duration_seconds != null ? `${data.duration_seconds.toFixed(1)} s` : 'n/a'),
    ].join('');
  } else if (variant === 'spotify') {
    const total = data.track_count || (data.tracks ? data.tracks.length : 0);
    const done = data.downloaded != null ? data.downloaded : total;
    kindBadge.textContent = `${done}/${total || '?'} tracks`;
    body.innerHTML = [
      rowMarkup('Collection', data.playlist_title || 'Spotify collection'),
      rowMarkup('Owner', data.owner || 'n/a'),
      rowMarkup('Source', data.source_type || 'playlist'),
      rowMarkup('Tracks saved', `${done}/${total || '?'}`),
      rowMarkup('Manifest', data.manifest_path || data.manifest || 'n/a'),
    ].join('');
  } else {
    kindBadge.textContent = data.kind || 'download';
    body.innerHTML = [
      rowMarkup('Title', data.title || 'Unknown'),
      rowMarkup('Kind', data.kind || 'n/a'),
      rowMarkup('Size', data.size_mb != null ? formatSize(data.size_mb) : 'n/a'),
      rowMarkup('Duration', data.duration_minutes != null ? `${data.duration_minutes.toFixed(2)} min` : 'n/a'),
      rowMarkup('Saved as', basename(data.filepath || 'n/a')),
    ].join('');
  }

  result.hidden = false;
}

function clearResult() {
  const result = $('#result');
  const body = $('#result-body');
  const badge = $('#result-kind');
  if (body) {
    body.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        </div>
        <h4>Ready to download</h4>
        <p class="muted">Enter a URL and start a download. The summary will appear here.</p>
      </div>
    `;
  }
  if (badge) badge.textContent = 'Waiting';
  if (result) result.hidden = false;
}

function rowMarkup(label, value) {
  return `<div class="result-row"><span class="result-label">${escapeHtml(String(label))}</span><span class="value">${escapeHtml(String(value))}</span></div>`;
}

async function readApiError(response, fallbackMessage, kind = 'generic') {
  let raw = '';

  try {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const data = await response.json();
      raw = extractApiErrorMessage(data);
    } else {
      raw = await response.text();
    }
  } catch {
    raw = '';
  }

  const message = cleanErrorMessage(raw || fallbackMessage);
  if (kind === 'spotify') return formatSpotifyError(message);
  return message || fallbackMessage;
}

function extractApiErrorMessage(payload) {
  if (payload == null) return '';
  if (typeof payload === 'string') return payload;
  if (typeof payload.detail === 'string') return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item.msg === 'string') return item.msg;
        return '';
      })
      .filter(Boolean)
      .join('; ');
  }
  if (typeof payload.message === 'string') return payload.message;
  return '';
}

function cleanErrorMessage(raw) {
  if (!raw) return '';

  let message = String(raw).trim();

  try {
    const parsed = JSON.parse(message);
    const extracted = extractApiErrorMessage(parsed);
    if (extracted) message = extracted;
  } catch {}

  if ((message.startsWith('"') && message.endsWith('"')) || (message.startsWith("'") && message.endsWith("'"))) {
    message = message.slice(1, -1);
  }

  try {
    const parsedNested = JSON.parse(message);
    const extractedNested = extractApiErrorMessage(parsedNested);
    if (extractedNested) message = extractedNested;
  } catch {}

  return message.replace(/^error\s*[:\-]\s*/i, '').trim();
}

function formatSpotifyError(message) {
  const normalized = (message || '').toLowerCase();
  if (!normalized) return 'Spotify download failed.';

  if (normalized.includes('blocked by spotify api access restrictions')) {
    return 'Spotify blocked direct access to this playlist, and no matching fallback tracks were found. Connect Spotify OAuth or configure an sp_dc cookie for better access.';
  }

  if (
    normalized.includes('active premium subscription required') ||
    normalized.includes('premium subscription required for the owner of the app')
  ) {
    return 'Spotify blocked this playlist for the app\'s current access mode. Try connecting Spotify OAuth or configuring an sp_dc cookie.';
  }

  if (normalized.includes('unexpected spotify mirror error')) {
    return 'Spotify download failed unexpectedly. Check the server logs and try again.';
  }

  return message;
}

function isValidUrl(value, prefixes) {
  if (!value) return false;
  return prefixes.some((prefix) => value.startsWith(prefix));
}

function toggleInputs(kindSelectId, resRowId, brRowId) {
  const kindEl = $(kindSelectId);
  if (!kindEl) return;
  const isAudio = kindEl.value === 'audio';
  const resRow = $(resRowId);
  const brRow = $(brRowId);
  if (!resRow || !brRow) return;

  resRow.hidden = isAudio;
  brRow.hidden = !isAudio;
}

function setButtonLoading(selector, isLoading, label) {
  const btn = $(selector);
  if (!btn) return;
  if (!btn.dataset.originalText) btn.dataset.originalText = btn.textContent;
  btn.disabled = isLoading;
  if (isLoading) {
    btn.classList.add('loading');
    btn.textContent = 'Processing...';
  } else {
    btn.classList.remove('loading');
    btn.textContent = label || btn.dataset.originalText;
  }
}

function showToast(message, type) {
  const toast = document.createElement('div');
  toast.className = `toast ${type === 'success' ? 'toast-success' : 'toast-error'}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('visible'));
  setTimeout(() => {
    toast.classList.remove('visible');
    setTimeout(() => toast.remove(), 240);
  }, 2400);
}

function clearInputs(ids) {
  (ids || []).forEach((id) => {
    const el = $(id);
    if (el) el.value = '';
  });
}

function basename(path) {
  if (!path) return '';
  const parts = path.split(/[\\/]/);
  return parts[parts.length - 1];
}

function formatPlaybackTime(totalSeconds) {
  const seconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}:${String(remainder).padStart(2, '0')}`;
}

function formatDate(iso) {
  if (!iso) return '-';
  try {
    let dateStr = iso;
    if (typeof iso === 'string' && iso.includes('T') && !iso.endsWith('Z') && !iso.match(/[+-]\d{2}:?\d{2}$/)) {
      dateStr = iso + 'Z';
    }
    const date = typeof iso === 'number'
      ? new Date(iso < 1e12 ? iso * 1000 : iso)
      : new Date(dateStr);
    if (Number.isNaN(date.getTime())) return String(iso);
    if (settingsState.timeFormat === 'exact') return date.toLocaleString();
    return formatRelativeDate(date);
  } catch {
    return String(iso);
  }
}

function formatRelativeDate(date) {
  const diffMs = date.getTime() - Date.now();
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  const week = 7 * day;
  const month = 30 * day;
  const year = 365 * day;

  if (Math.abs(diffMs) < hour) return rtf.format(Math.round(diffMs / minute), 'minute');
  if (Math.abs(diffMs) < day) return rtf.format(Math.round(diffMs / hour), 'hour');
  if (Math.abs(diffMs) < week) return rtf.format(Math.round(diffMs / day), 'day');
  if (Math.abs(diffMs) < month) return rtf.format(Math.round(diffMs / week), 'week');
  if (Math.abs(diffMs) < year) return rtf.format(Math.round(diffMs / month), 'month');
  return rtf.format(Math.round(diffMs / year), 'year');
}

function formatSize(valueMb) {
  const numeric = Number(valueMb) || 0;
  if (settingsState.sizeFormat === 'mb') return `${numeric.toFixed(2)} MB`;
  if (numeric >= 1024) return `${(numeric / 1024).toFixed(2)} GB`;
  return `${numeric.toFixed(2)} MB`;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, '&#96;');
}

function initSettings() {
  const autoRefresh = $('#setting-autorefresh');
  const density = $('#setting-density');
  const animations = $('#setting-animations');
  const reduceMotion = $('#setting-reduce-motion');
  const sizeFormat = $('#setting-size-format');
  const timeFormat = $('#setting-time-format');
  const theme = $('#setting-theme');

  if (autoRefresh) autoRefresh.checked = !!settingsState.autoRefresh;
  if (density) density.value = settingsState.density;
  if (animations) animations.checked = !!settingsState.animations;
  if (reduceMotion) reduceMotion.checked = !!settingsState.reduceMotion;
  if (sizeFormat) sizeFormat.value = settingsState.sizeFormat;
  if (timeFormat) timeFormat.value = settingsState.timeFormat;
  if (theme) theme.value = settingsState.theme || 'dark';

  if (autoRefresh) {
    autoRefresh.addEventListener('change', () => {
      settingsState.autoRefresh = autoRefresh.checked;
      saveSettings();
      if (settingsState.autoRefresh) {
        scheduleAutoRefresh();
      } else {
        clearAutoRefresh();
      }
    });
  }

  if (density) {
    density.addEventListener('change', () => {
      settingsState.density = density.value;
      applySettings();
      saveSettings();
    });
  }

  if (animations) {
    animations.addEventListener('change', () => {
      settingsState.animations = animations.checked;
      applySettings();
      saveSettings();
    });
  }

  if (reduceMotion) {
    reduceMotion.addEventListener('change', () => {
      settingsState.reduceMotion = reduceMotion.checked;
      applySettings();
      saveSettings();
    });
  }

  if (sizeFormat) {
    sizeFormat.addEventListener('change', async () => {
      settingsState.sizeFormat = sizeFormat.value;
      saveSettings();
      await refreshData();
    });
  }

  if (timeFormat) {
    timeFormat.addEventListener('change', async () => {
      settingsState.timeFormat = timeFormat.value;
      saveSettings();
      await refreshData();
    });
  }

  if (theme) {
    theme.addEventListener('change', () => {
      settingsState.theme = theme.value;
      applySettings();
      saveSettings();
    });
  }
}

function clearAutoRefresh() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
}

function scheduleAutoRefresh() {
  clearAutoRefresh();
  autoRefreshTimer = setInterval(() => {
    refreshData(true);
  }, AUTO_REFRESH_MS);
}

async function refreshData(isAutoRefresh = false) {
  await Promise.all([loadStats(), loadLibrary(isAutoRefresh), loadHistory(), loadOutputRoot()]);
}

function bindEvents() {
  $('#unified-submit')?.addEventListener('click', () => {
    const service = $('#service-type').value;
    if (service === 'single') postDownload();
    else if (service === 'playlist') postPlaylist();
    else if (service === 'spotify') mirrorSpotifyPlaylist();
  });
  
  $('#service-type')?.addEventListener('change', (e) => {
    const service = e.target.value;
    const card = $('#unified-card');
    const badge = $('#unified-badge');
    const urlLabel = $('#unified-url-label');
    const urlInput = $('#unified-url');
    const helper = $('#unified-helper');
    const btn = $('#unified-submit');
    
    card.classList.remove('tone-green', 'tone-blue', 'tone-amber', 'tone-spotify');
    badge.classList.remove('ghost');
    
    if (service === 'single') {
      card.classList.add('tone-green');
      badge.textContent = 'One-off';
      urlLabel.textContent = 'YouTube single URL';
      urlInput.placeholder = 'https://www.youtube.com/watch?v=...';
      helper.textContent = 'Saves into the singles output folder.';
      btn.textContent = 'Download';
      btn.className = 'btn-primary';
    } else if (service === 'playlist') {
      card.classList.add('tone-blue');
      badge.textContent = 'Multi';
      badge.classList.add('ghost');
      urlLabel.textContent = 'YouTube playlist URL';
      urlInput.placeholder = 'https://www.youtube.com/playlist?list=...';
      helper.textContent = 'Files are grouped by playlist name.';
      btn.textContent = 'Download Playlist';
      btn.className = 'btn-secondary';
    } else if (service === 'spotify') {
      card.classList.add('tone-spotify');
      badge.textContent = 'Mirror';
      badge.classList.add('ghost');
      urlLabel.textContent = 'Spotify playlist/artist/album URL';
      urlInput.placeholder = 'https://open.spotify.com/playlist/...';
      helper.textContent = 'Uses YouTube as source and stores audio or video files in spotify folders.';
      btn.textContent = 'Download Spotify list';
      btn.className = 'btn-spotify';
    }
    updateAmbientLayer();
  });

  $('#refresh-stats')?.addEventListener('click', loadStats);
  $('#refresh-library')?.addEventListener('click', loadLibrary);
  $('#library-playlist-select')?.addEventListener('change', (e) => {
    libraryState.selectedCategory = e.target.value;
    libraryState.selectedSubfolder = 'all';
    libraryState.visibleCount = LIBRARY_PAGE_SIZE;
    renderLibrarySelector();
    renderLibraryRows();
  });
  $('#library-subfolder-select')?.addEventListener('change', (e) => {
    libraryState.selectedSubfolder = e.target.value;
    libraryState.visibleCount = LIBRARY_PAGE_SIZE;
    renderLibraryRows();
  });
  $('#library-sort-select')?.addEventListener('change', (e) => {
    libraryState.selectedSort = e.target.value;
    libraryState.visibleCount = LIBRARY_PAGE_SIZE;
    renderLibraryRows();
  });
  $('#output-root')?.addEventListener('click', async () => {
    try {
      await fetch('/api/v1/files/open-root', { method: 'POST' });
    } catch (e) {
      console.error('Failed to open root:', e);
    }
  });
  
  $('#btn-open-logs')?.addEventListener('click', async () => {
    try {
      await fetch('/api/v1/system/open-logs', { method: 'POST' });
    } catch (e) {
      console.error('Failed to open logs:', e);
    }
  });
  
  $('#btn-update-core')?.addEventListener('click', async (e) => {
    const btn = e.target;
    btn.disabled = true;
    btn.textContent = 'Updating...';
    try {
      const res = await fetch('/api/v1/system/update-core', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        if (data.details && data.details.includes('Requirement already satisfied')) {
          alert('yt-dlp is already up to date!');
          btn.textContent = 'Up to date';
        } else {
          alert('Successfully updated yt-dlp!\\n\\n' + data.details);
          btn.textContent = 'Updated!';
        }
        setTimeout(() => { btn.textContent = 'Update yt-dlp'; btn.disabled = false; }, 3000);
      } else {
        alert('Update failed: ' + data.detail);
        btn.textContent = 'Update Failed';
        setTimeout(() => { btn.textContent = 'Update yt-dlp'; btn.disabled = false; }, 3000);
      }
    } catch (err) {
      alert('Update error: ' + err);
      btn.textContent = 'Update yt-dlp';
      btn.disabled = false;
    }
  });
  $('#library-load-more')?.addEventListener('click', () => {
    libraryState.visibleCount += LIBRARY_PAGE_SIZE;
    renderLibraryRows();
  });
  $('#library-body')?.addEventListener('click', (event) => {
    const row = event.target.closest('.lib-row.is-playable');
    if (!row) return;
    playTrackByPath(row.dataset.path);
  });
  $('#library-body')?.addEventListener('keydown', (event) => {
    const row = event.target.closest('.lib-row.is-playable');
    if (!row) return;
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    playTrackByPath(row.dataset.path);
  });
  $('#player-prev')?.addEventListener('click', playPreviousTrack);
  $('#player-next')?.addEventListener('click', playNextTrack);
  $('#player-toggle')?.addEventListener('click', togglePlayerPlayback);
  $('#player-shuffle')?.addEventListener('click', () => {
    if (!playerState.queue || playerState.queue.length === 0) return;
    const current = playerState.currentTrack;
    // Shuffle the remaining queue
    playerState.queue.sort(() => Math.random() - 0.5);
    // Move current track to start so it doesn't repeat immediately
    if (current) {
       const idx = playerState.queue.findIndex(t => t.path === current.path);
       if (idx > -1) {
         playerState.queue.splice(idx, 1);
         playerState.queue.unshift(current);
       }
       playerState.currentIndex = 0;
    }
    playNextTrack();
  });
  $('#player-seek')?.addEventListener('input', (event) => {
    const player = $('#audio-player');
    const currentTime = $('#player-current-time');
    const nextValue = Number(event.target.value) || 0;
    if (player) player.currentTime = nextValue;
    if (currentTime) currentTime.textContent = formatPlaybackTime(nextValue);
  });
  $('#audio-player')?.addEventListener('loadedmetadata', () => {
    const player = $('#audio-player');
    const seek = $('#player-seek');
    const duration = $('#player-duration');
    if (!player || !seek || !duration) return;
    const total = Number.isFinite(player.duration) ? Math.floor(player.duration) : 0;
    seek.max = String(total);
    seek.value = '0';
    duration.textContent = formatPlaybackTime(total);
  });
  $('#audio-player')?.addEventListener('timeupdate', () => {
    const player = $('#audio-player');
    const seek = $('#player-seek');
    const currentTime = $('#player-current-time');
    if (!player || !seek || !currentTime) return;
    const progress = Math.floor(player.currentTime || 0);
    seek.value = String(progress);
    currentTime.textContent = formatPlaybackTime(progress);
  });
  $('#audio-player')?.addEventListener('play', () => {
    playerState.isPlaying = true;
    renderPlayerState();
    renderLibraryRows();
  });
  $('#audio-player')?.addEventListener('pause', () => {
    playerState.isPlaying = false;
    renderPlayerState();
    renderLibraryRows();
  });
  $('#audio-player')?.addEventListener('ended', () => {
    if (playerState.currentIndex >= 0 && playerState.currentIndex < playerState.queue.length - 1) {
      playNextTrack();
      return;
    }
    playerState.isPlaying = false;
    renderPlayerState();
    renderLibraryRows();
  });
  $('#refresh-history')?.addEventListener('click', loadHistory);
  $('#history-source-select')?.addEventListener('change', (e) => {
    historyState.tab = e.target.value;
    historyState.selectedGroup = 'all';
    historyState.visibleCount = HISTORY_PAGE_SIZE;
    loadHistory();
  });
  $('#history-group-select')?.addEventListener('change', (e) => {
    historyState.selectedGroup = e.target.value;
    historyState.visibleCount = HISTORY_PAGE_SIZE;
    renderHistoryRows();
  });
  $('#history-load-more')?.addEventListener('click', () => {
    historyState.visibleCount += HISTORY_PAGE_SIZE;
    renderHistoryRows();
  });

  $('#unified-kind')?.addEventListener('change', () => toggleInputs('#unified-kind', '#unified-res-row', '#unified-br-row'));
}

async function init() {
  loadSettings();
  applySettings();
  bindEvents();
  initSettings();
  initSettingsPopover();
  toggleInputs('#unified-kind', '#unified-res-row', '#unified-br-row');
  renderStatus();

  await refreshData();

  if (settingsState.autoRefresh) scheduleAutoRefresh();
}

init();
