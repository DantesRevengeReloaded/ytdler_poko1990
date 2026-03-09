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
};
const LIBRARY_PAGE_SIZE = 60;
const libraryState = {
  allFiles: [],
  groups: [],
  selectedKey: '',
  visibleCount: LIBRARY_PAGE_SIZE,
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
  document.body.classList.toggle('compact', settingsState.density === 'compact');
  document.body.classList.toggle('no-anim', !settingsState.animations || settingsState.reduceMotion);
  if (!settingsState.animations || settingsState.reduceMotion) {
    closeSettings();
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
  const url = $('#url').value.trim();
  if (!isValidUrl(url, ['https://www.youtube.com/', 'https://youtube.com/'])) {
    showToast('Enter a valid YouTube URL.', 'error');
    return;
  }

  clearResult();
  const jobId = createJobId();
  setButtonLoading('#submit', true, 'Download');
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
        kind: $('#kind').value,
        resolution: $('#resolution').value,
        bitrate: $('#bitrate').value,
        job_id: jobId,
      }),
    });

    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || 'Request failed');
    }

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

    clearInputs(['#url']);
    showToast('Download complete', 'success');
    await refreshData();
  } catch (err) {
    const msg = err.message || 'Download failed';
    setStatus('single', { phase: 'error', phaseLabel: 'Error', message: msg, progress: 0, indeterminate: false, countLabel: '-' });
    showToast(msg, 'error');
  }

  stopPolling();
  setButtonLoading('#submit', false, 'Download');
  $('#status').textContent = '';
}

async function postPlaylist() {
  const url = $('#pl-url').value.trim();
  if (!isValidUrl(url, ['https://www.youtube.com/playlist', 'https://youtube.com/playlist'])) {
    showToast('Enter a valid YouTube playlist URL.', 'error');
    return;
  }

  clearResult();
  const jobId = createJobId();
  setButtonLoading('#pl-submit', true, 'Download Playlist');
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
        kind: $('#pl-kind').value,
        resolution: $('#pl-resolution').value,
        bitrate: $('#pl-bitrate').value,
        job_id: jobId,
      }),
    });

    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || 'Playlist request failed');
    }

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

    clearInputs(['#pl-url']);
    showToast(`Playlist downloaded (${data.count || 0} items)`, 'success');
    await refreshData();
  } catch (err) {
    const msg = err.message || 'Playlist failed';
    setStatus('playlist', { phase: 'error', phaseLabel: 'Error', message: msg, progress: 0, indeterminate: false, countLabel: '-' });
    showToast(msg, 'error');
  }

  stopPolling();
  setButtonLoading('#pl-submit', false, 'Download Playlist');
  $('#pl-status').textContent = '';
}

async function mirrorSpotifyPlaylist() {
  const url = $('#sp-url').value.trim();
  if (!isValidUrl(url, ['https://open.spotify.com/', 'spotify:'])) {
    showToast('Enter a valid Spotify URL.', 'error');
    return;
  }

  clearResult();
  const jobId = createJobId();
  setButtonLoading('#sp-submit', true, 'Download Spotify list');
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
    const res = await fetch('/api/v1/spotify/mirror', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, bitrate: $('#sp-bitrate').value || '192', job_id: jobId }),
    });

    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || 'Spotify mirror failed');
    }

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

    $('#sp-status').textContent = `${data.playlist_title || 'Spotify list'}: ${done}/${count} tracks.`;
    clearInputs(['#sp-url']);
    showToast(`${done}/${count} tracks mirrored`, 'success');
    await refreshData();
  } catch (err) {
    const msg = err.message || 'Spotify mirror failed';
    $('#sp-status').textContent = msg;
    setStatus('spotify', { phase: 'error', phaseLabel: 'Error', message: msg, progress: 0, indeterminate: false, countLabel: '-' });
    showToast(msg, 'error');
  }

  setButtonLoading('#sp-submit', false, 'Download Spotify list');
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
      <div class="stat-tile"><div class="label">Downloads logged</div><div class="value">${dHist.total || 0}</div></div>
      <div class="stat-tile"><div class="label">Spotify logged</div><div class="value">${sHist.total || 0}</div></div>
    `;

    $('#hero-total-items').textContent = String(stats.total_items);
    $('#hero-total-size').textContent = formatSize(stats.total_size_mb);
    $('#hero-recent').textContent = (dHist.items && dHist.items.length) ? formatDate(dHist.items[0].downloaded_date) : 'No entries';

    if (breakdownRes.ok) {
      const bd = await breakdownRes.json();
      latestStorage = bd.storage || [];
      renderBreakdown(bd);
      renderOutputFolders(latestStorage);
    }

    renderQueueSummary({ downloads: dHist.total || 0, spotify: sHist.total || 0, lastDownload: dHist.items?.[0], lastSpotify: sHist.items?.[0] });
  } catch (err) {
    statsEl.innerHTML = `<div class="state-card error">Stats error: ${escapeHtml(err.message)}</div>`;
  }
}

function renderBreakdown(data) {
  const el = $('#stats-breakdown');
  if (!el) return;
  const breakdown = data.breakdown || [];
  const storage = data.storage || [];

  if (!breakdown.length && !storage.length) {
    el.innerHTML = '<div class="state-card">No breakdown data yet.</div>';
    return;
  }

  const typeRow = breakdown.map((b) => `<span class="breakdown-pill">${escapeHtml(b.type)}: ${b.count} items · ${formatSize(b.total_mb)}</span>`).join('');
  const storeRow = storage.map((s) => `<span class="breakdown-pill">${escapeHtml(s.directory)}: ${s.file_count} files · ${formatSize(s.size_mb)}</span>`).join('');
  el.innerHTML = `<div class="breakdown-row">${typeRow}</div><div class="breakdown-row">${storeRow}</div>`;
}

async function loadOutputRoot() {
  const rootEl = $('#output-root');
  if (!rootEl) return;

  try {
    const res = await fetch('/api/v1/files/root');
    if (!res.ok) throw new Error('Could not resolve output root');
    const data = await res.json();
    rootEl.textContent = `Base folder: ${data.root}`;
  } catch {
    rootEl.textContent = 'Base folder: configured downloads directory';
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
    <div class="queue-row"><span>Download history entries</span><strong>${data.downloads}</strong></div>
    <div class="queue-row"><span>Spotify history entries</span><strong>${data.spotify}</strong></div>
    <div class="queue-row"><span>Last download</span><strong>${escapeHtml(lastD)}</strong></div>
    <div class="queue-row"><span>Last Spotify mirror</span><strong>${escapeHtml(lastS)}</strong></div>
  `;
}

async function loadLibrary() {
  const body = $('#library-body');
  const selector = $('#library-playlist-select');
  const summary = $('#library-summary');
  const loadMoreBtn = $('#library-load-more');
  if (!body) return;

  body.innerHTML = '<div class="state-card">Loading files...</div>';
  if (summary) summary.textContent = 'Loading library...';

  try {
    const res = await fetch('/api/v1/files');
    if (!res.ok) throw new Error('Failed to load library');
    const data = await res.json();
    const files = data.files || [];
    libraryState.allFiles = files;
    libraryState.groups = buildLibraryGroups(files);

    if (!files.length) {
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
  const map = new Map();
  files.forEach((file) => {
    const group = resolveLibraryGroup(file);
    if (!map.has(group.key)) {
      map.set(group.key, { key: group.key, label: group.label, files: [] });
    }
    map.get(group.key).files.push(file);
  });

  const groups = Array.from(map.values()).map((g) => {
    const totalSize = g.files.reduce((acc, item) => acc + (Number(item.size_mb) || 0), 0);
    const latestModified = g.files.reduce((max, item) => Math.max(max, Number(item.modified) || 0), 0);
    return { ...g, totalSize, latestModified };
  }).sort((a, b) => b.files.length - a.files.length || a.label.localeCompare(b.label));

  const allTotalSize = files.reduce((acc, item) => acc + (Number(item.size_mb) || 0), 0);
  const allLatest = files.reduce((max, item) => Math.max(max, Number(item.modified) || 0), 0);
  groups.unshift({
    key: 'all',
    label: 'All playlists',
    files,
    totalSize: allTotalSize,
    latestModified: allLatest,
  });

  return groups;
}

function resolveLibraryGroup(file) {
  const parts = String(file.path || '').split('/');
  if (file.category === 'singledls') return { key: 'singledls', label: 'Singles' };
  if (file.category === 'playlists') {
    const folder = parts[1] || 'YouTube playlist';
    return { key: `yt:${folder}`, label: `YouTube · ${folder}` };
  }
  if (file.category === 'spotify_playlists') {
    const folder = parts[1] || 'Spotify playlist';
    return { key: `sp:${folder}`, label: `Spotify · ${folder}` };
  }
  return { key: file.category || 'other', label: file.category || 'Other' };
}

function syncLibrarySelection() {
  const keys = new Set(libraryState.groups.map((g) => g.key));
  if (libraryState.selectedKey && keys.has(libraryState.selectedKey)) return;

  const nonAll = libraryState.groups.filter((g) => g.key !== 'all');
  libraryState.selectedKey = (nonAll[0] && nonAll[0].key) || 'all';
  libraryState.visibleCount = LIBRARY_PAGE_SIZE;
}

function renderLibrarySelector() {
  const selector = $('#library-playlist-select');
  if (!selector) return;

  selector.innerHTML = libraryState.groups.map((group) => {
    return `<option value="${escapeAttr(group.key)}">${escapeHtml(group.label)} (${group.files.length})</option>`;
  }).join('');
  selector.value = libraryState.selectedKey;
}

function renderLibraryRows() {
  const body = $('#library-body');
  const summary = $('#library-summary');
  const loadMoreBtn = $('#library-load-more');
  if (!body) return;

  const selected = libraryState.groups.find((g) => g.key === libraryState.selectedKey) || libraryState.groups[0];
  if (!selected) {
    body.innerHTML = '<div class="state-card">No tracks available.</div>';
    if (summary) summary.textContent = 'No tracks available.';
    if (loadMoreBtn) loadMoreBtn.hidden = true;
    return;
  }

  const visible = selected.files.slice(0, libraryState.visibleCount);
  const latest = selected.latestModified ? formatDate(selected.latestModified) : '-';
  if (summary) {
    summary.textContent = `${selected.label} · ${selected.files.length} tracks · ${selected.totalSize.toFixed(2)} MB · Updated ${latest}`;
  }

  if (!visible.length) {
    body.innerHTML = '<div class="state-card">No tracks in this playlist.</div>';
    if (loadMoreBtn) loadMoreBtn.hidden = true;
    return;
  }

  body.innerHTML = visible.map((f) => {
    const isAudio = f.type === 'audio';
    const parts = String(f.path || '').split('/');
    const folderName = parts[1] || f.category || 'library';
    const meta = `${folderName} · ${formatSize(f.size_mb)}`;
    return `
      <div class="lib-row" data-path="${escapeAttr(f.path)}" data-type="${f.type}">
        <div class="lib-meta">
          <span class="lib-name" title="${escapeAttr(f.name)}">${escapeHtml(f.name)}</span>
          <span class="lib-info">${escapeHtml(meta)}</span>
        </div>
        <div class="lib-actions">
          ${isAudio ? `<button class="btn-ghost lib-btn" data-path="${escapeAttr(f.path)}" onclick="playFile(this)">Play</button>` : ''}
          <button class="btn-ghost lib-btn" data-path="${escapeAttr(f.path)}" onclick="deleteFile(this)">Delete</button>
        </div>
      </div>
    `;
  }).join('');

  if (loadMoreBtn) {
    loadMoreBtn.hidden = libraryState.visibleCount >= selected.files.length;
  }
}

function playFile(btn) {
  const path = btn.dataset.path;
  const player = $('#audio-player');
  if (!player) return;
  player.src = `/api/v1/files/stream/${encodeFilePath(path)}`;
  player.style.display = 'block';
  player.play();
  showToast(`Playing ${basename(path)}`, 'success');
}

async function deleteFile(btn) {
  const path = btn.dataset.path;
  if (!confirm(`Delete ${basename(path)}?`)) return;
  try {
    const res = await fetch(`/api/v1/files/${encodeFilePath(path)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Delete failed');
    showToast('Deleted', 'success');
    await refreshData();
  } catch (err) {
    showToast(err.message || 'Delete failed', 'error');
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

async function loadSpotifyAuthStatus() {
  const badge = $('#spotify-auth-badge');
  if (!badge) return;

  try {
    const res = await fetch('/api/v1/spotify/auth/status');
    if (!res.ok) throw new Error('status unavailable');
    const data = await res.json();

    if (data.connected) {
      badge.textContent = 'Spotify connected';
      badge.style.borderColor = 'rgba(50, 213, 131, 0.52)';
      badge.style.color = '#a3f6cd';
    } else {
      badge.textContent = 'Spotify not connected';
      badge.style.borderColor = 'rgba(249, 112, 102, 0.45)';
      badge.style.color = '#ffb5ac';
    }
  } catch {
    badge.textContent = 'Auth unknown';
  }
}

function renderResult(data, variant) {
  const body = $('#result-body');
  const kindBadge = $('#result-kind');
  const result = $('#result');
  const strip = $('#result-strip');
  if (!body || !kindBadge || !result || !strip) return;

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

  strip.hidden = false;
  result.hidden = false;
}

function clearResult() {
  const strip = $('#result-strip');
  const body = $('#result-body');
  const badge = $('#result-kind');
  if (strip) strip.hidden = true;
  if (body) body.innerHTML = '';
  if (badge) badge.textContent = '';
}

function rowMarkup(label, value) {
  return `<div class="result-row"><span class="result-label">${escapeHtml(String(label))}</span><span class="value">${escapeHtml(String(value))}</span></div>`;
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

function formatDate(iso) {
  if (!iso) return '-';
  try {
    const date = typeof iso === 'number'
      ? new Date(iso < 1e12 ? iso * 1000 : iso)
      : new Date(iso);
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

  if (autoRefresh) autoRefresh.checked = !!settingsState.autoRefresh;
  if (density) density.value = settingsState.density;
  if (animations) animations.checked = !!settingsState.animations;
  if (reduceMotion) reduceMotion.checked = !!settingsState.reduceMotion;
  if (sizeFormat) sizeFormat.value = settingsState.sizeFormat;
  if (timeFormat) timeFormat.value = settingsState.timeFormat;

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
    refreshData();
  }, AUTO_REFRESH_MS);
}

async function refreshData() {
  await Promise.all([loadStats(), loadLibrary(), loadHistory(), loadOutputRoot()]);
}

function bindEvents() {
  $('#submit')?.addEventListener('click', postDownload);
  $('#pl-submit')?.addEventListener('click', postPlaylist);
  $('#sp-submit')?.addEventListener('click', mirrorSpotifyPlaylist);
  $('#refresh-stats')?.addEventListener('click', loadStats);
  $('#refresh-library')?.addEventListener('click', loadLibrary);
  $('#library-playlist-select')?.addEventListener('change', (e) => {
    libraryState.selectedKey = e.target.value;
    libraryState.visibleCount = LIBRARY_PAGE_SIZE;
    renderLibraryRows();
  });
  $('#library-load-more')?.addEventListener('click', () => {
    libraryState.visibleCount += LIBRARY_PAGE_SIZE;
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

  $('#kind')?.addEventListener('change', () => toggleInputs('#kind', '#res-row', '#br-row'));
  $('#pl-kind')?.addEventListener('change', () => toggleInputs('#pl-kind', '#pl-res-row', '#pl-br-row'));
}

async function init() {
  loadSettings();
  applySettings();
  bindEvents();
  initSettings();
  initSettingsPopover();
  toggleInputs('#kind', '#res-row', '#br-row');
  toggleInputs('#pl-kind', '#pl-res-row', '#pl-br-row');
  renderStatus();

  await refreshData();
  await loadSpotifyAuthStatus();

  if (settingsState.autoRefresh) scheduleAutoRefresh();
}

init();

window.playFile = playFile;
window.deleteFile = deleteFile;
