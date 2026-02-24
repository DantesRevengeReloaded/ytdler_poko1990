const $ = (s) => document.querySelector(s);

const defaultStatus = {
  job: 'idle',
  jobLabel: 'Idle',
  phase: 'idle',
  phaseLabel: 'Idle',
  message: 'No work in progress',
  progress: 0,
  indeterminate: false,
  countLabel: '—',
};
let statusState = { ...defaultStatus };
const jobLabels = { single: 'Single download', playlist: 'Playlist download', spotify: 'Spotify download', idle: 'Idle' };
let progressTimer = null;
const POLL_INTERVAL_MS = 500;

function createJobId() {
  if (crypto && crypto.randomUUID) return crypto.randomUUID();
  return `job-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function ensureStatusVisible() {
  const panel = document.querySelector('#live-status');
  if (!panel) return;
  panel.style.display = 'block';
  panel.style.visibility = 'visible';
}

function renderStatus() {
  ensureStatusVisible();
  const progressEl = document.querySelector('#live-progress');
  const textEl = document.querySelector('#live-progress-text');
  const jobEl = document.querySelector('#status-job-label');
  const phaseEl = document.querySelector('#status-phase-label');
  const countsEl = document.querySelector('#status-counts');
  const pill = document.querySelector('#status-pill');
  if (!progressEl || !textEl || !jobEl || !phaseEl || !countsEl || !pill) return;

  progressEl.classList.toggle('indeterminate', !!statusState.indeterminate);
  progressEl.style.width = statusState.indeterminate ? '42%' : `${statusState.progress || 0}%`;
  ['progress-fill--single', 'progress-fill--playlist', 'progress-fill--spotify'].forEach((c) => progressEl.classList.remove(c));
  if (statusState.job && statusState.job !== 'idle') {
    const cls = `progress-fill--${statusState.job}`;
    progressEl.classList.add(cls);
  }
  textEl.textContent = statusState.message;
  jobEl.textContent = statusState.jobLabel || 'Working';
  phaseEl.textContent = statusState.phaseLabel || statusState.phase || 'Working';
  countsEl.textContent = statusState.countLabel || '—';

  const working = statusState.job && !['idle', 'done', 'error'].includes(statusState.phase);
  pill.textContent = working ? `In progress · ${statusState.jobLabel || ''}` : 'Idle';
  pill.classList.toggle('pill-busy', working);
  pill.classList.toggle('pill-soft', !working);
}

function startPolling(job, jobId) {
  stopPolling();
  const tick = async () => {
    try {
      const res = await fetch(`/api/v1/downloads/progress/${jobId}`);
      if (res.status === 404) {
        // Job may not be registered yet; keep polling.
        return;
      }
      if (!res.ok) throw new Error('progress fetch failed');
      const data = await res.json();
      const total = data.total || 0;
      const completed = data.completed || 0;
      const percent = data.progress_percent != null ? data.progress_percent : total ? (completed / total) * 100 : (statusState.progress || 0);
      const label = data.phase === 'done' ? 'Completed' : data.phase === 'error' ? 'Error' : data.phase || 'Working';
      const baseTitle = data.playlist_title || '';
      const counts = total ? `${completed}/${total}` : '';
      let message = data.message || 'Working...';
      if (data.job_type === 'playlist' && total) {
        const titlePart = baseTitle ? `${baseTitle}:` : 'Playlist:';
        message = `${titlePart} Total ${total} songs ${counts} downloaded`;
      } else if (data.job_type === 'spotify' && total) {
        const titlePart = baseTitle ? `${baseTitle}:` : 'Spotify:';
        message = `${titlePart} Total ${total} tracks ${counts} mirrored`;
      } else if (counts) {
        message = `${counts} • ${message}`;
      }
      setStatus(job, {
        phase: data.phase,
        phaseLabel: label,
        message,
        progress: percent,
        indeterminate: !total,
        countLabel: counts || '—',
      });
      if (data.phase === 'done' || data.phase === 'error') {
        stopPolling();
      }
    } catch (err) {
      stopPolling();
    }
  };
  tick();
  progressTimer = setInterval(tick, POLL_INTERVAL_MS);
}

function stopPolling() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
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

function resetStatus() {
  statusState = { ...defaultStatus };
  renderStatus();
  stopPolling();
}

async function postDownload() {
  const url = $('#url').value.trim();
  if (!isValidUrl(url, ['https://www.youtube.com/', 'https://youtube.com/'])) {
    showToast('Enter a valid YouTube URL.', 'error');
    return;
  }
  const kind = $('#kind').value;
  const resolution = $('#resolution').value;
  const bitrate = $('#bitrate').value;
  const jobId = createJobId();
  ensureStatusVisible();
  setStatus('single', {
    phase: 'metadata',
    phaseLabel: 'Fetching metadata',
    message: 'Fetching video details...',
    progress: 12,
    indeterminate: true,
    countLabel: '—',
  });
  setButtonLoading('#submit', true, 'Download');
  startPolling('single', jobId);
  try {
    setStatus('single', {
      phase: 'downloading',
      phaseLabel: 'Downloading',
      message: 'Downloading file...',
      progress: 38,
      indeterminate: true,
      countLabel: '—',
    });
    const res = await fetch('/api/v1/downloads/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, kind, resolution, bitrate, job_id: jobId })
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || 'Request failed');
    }
    setStatus('single', {
      phase: 'finishing',
      phaseLabel: 'Finalizing',
      message: 'Finalizing file...',
      progress: 72,
      indeterminate: true,
      countLabel: '—',
    });
    const data = await res.json();
    renderResult(data, false);
    showToast('Download complete', 'success');
    const fileName = data.filepath ? basename(data.filepath) : data.title || 'file';
    setStatus('single', {
      phase: 'done',
      phaseLabel: 'Completed',
      message: `Saved ${fileName}`,
      progress: 100,
      indeterminate: false,
      countLabel: '1/1',
    });
    clearInputs(['#url']);
    await loadStats();
  } catch (err) {
    showToast(err.message || 'Download failed', 'error');
    setStatus('single', {
      phase: 'error',
      phaseLabel: 'Error',
      message: err.message || 'Download failed',
      progress: 0,
      indeterminate: false,
      countLabel: '—',
    });
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
  const kind = $('#pl-kind').value;
  const resolution = $('#pl-resolution').value;
  const bitrate = $('#pl-bitrate').value;
  const jobId = createJobId();
  ensureStatusVisible();
  setStatus('playlist', {
    phase: 'metadata',
    phaseLabel: 'Fetching metadata',
    message: 'Fetching playlist details...',
    progress: 10,
    indeterminate: true,
    countLabel: '—',
  });
  setButtonLoading('#pl-submit', true, 'Download Playlist');
  startPolling('playlist', jobId);
  try {
    setStatus('playlist', {
      phase: 'downloading',
      phaseLabel: 'Downloading items',
      message: 'Downloading playlist items...',
      progress: 34,
      indeterminate: true,
      countLabel: '—',
    });
    const res = await fetch('/api/v1/downloads/playlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, kind, resolution, bitrate, job_id: jobId })
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || 'Request failed');
    }
    setStatus('playlist', {
      phase: 'finishing',
      phaseLabel: 'Finalizing',
      message: 'Finishing playlist files...',
      progress: 64,
      indeterminate: true,
      countLabel: '—',
    });
    const data = await res.json();
    const total = data.count || (data.items ? data.items.length : 0) || 0;
    if (total > 0) {
      setStatus('playlist', {
        phase: 'counting',
        phaseLabel: 'Counting items',
        message: `Collected ${total} items, preparing summary...`,
        progress: 82,
        indeterminate: false,
        countLabel: `${total}/${total}`,
      });
    }
    renderResult(data, true);
    showToast(`Playlist downloaded (${data.count} items)`, 'success');
    const playlistTitle = data.playlist_title || 'playlist';
    setStatus('playlist', {
      phase: 'done',
      phaseLabel: 'Completed',
      message: `Downloaded ${data.count} items from ${playlistTitle}`,
      progress: 100,
      indeterminate: false,
      countLabel: `${data.count}/${data.count}`,
    });
    clearInputs(['#pl-url']);
    await loadStats();
  } catch (err) {
    showToast(err.message || 'Playlist failed', 'error');
    setStatus('playlist', {
      phase: 'error',
      phaseLabel: 'Error',
      message: err.message || 'Playlist failed',
      progress: 0,
      indeterminate: false,
      countLabel: '—',
    });
  }
  stopPolling();
  setButtonLoading('#pl-submit', false, 'Download Playlist');
  $('#pl-status').textContent = '';
}

async function loadStats() {
  try {
    const res = await fetch('/api/v1/stats');
    if (!res.ok) throw new Error('Failed to load stats');
    const data = await res.json();
    $('#stats').innerHTML = `
      <span class="stat-pill">Total items: ${data.total_items}</span>
      <span class="stat-pill">Total size: ${data.total_size_mb.toFixed(2)} MB</span>
    `;
  } catch (err) {
    $('#stats').textContent = `Stats error: ${err.message}`;
  }
}

$('#submit').addEventListener('click', postDownload);
$('#pl-submit').addEventListener('click', postPlaylist);
$('#refresh-stats').addEventListener('click', loadStats);
$('#sp-submit').addEventListener('click', mirrorSpotifyPlaylist);

function toggleInputs(kindSelectId, resRowId, brRowId) {
  const kind = $(kindSelectId).value;
  const resRow = $(resRowId);
  const brRow = $(brRowId);
  const isAudio = kind === 'audio';
  // Dual-toggle hidden attribute and CSS class so browsers or cached styles can't leave both visible.
  resRow.hidden = isAudio;
  brRow.hidden = !isAudio;
  resRow.classList.toggle('hidden', isAudio);
  brRow.classList.toggle('hidden', !isAudio);
}

$('#kind').addEventListener('change', () => toggleInputs('#kind', '#res-row', '#br-row'));
$('#pl-kind').addEventListener('change', () => toggleInputs('#pl-kind', '#pl-res-row', '#pl-br-row'));

// initial state
toggleInputs('#kind', '#res-row', '#br-row');
toggleInputs('#pl-kind', '#pl-res-row', '#pl-br-row');

renderStatus();

loadStats();

async function mirrorSpotifyPlaylist() {
  const url = $('#sp-url').value.trim();
  if (!isValidUrl(url, ['https://open.spotify.com/', 'spotify:'])) {
    showToast('Enter a valid Spotify URL.', 'error');
    return;
  }
  const bitrate = $('#sp-bitrate').value || '192';
  const jobId = createJobId();
  // Stop any existing polling from other jobs so the live bar isn't overwritten while Spotify runs.
  stopPolling();
  ensureStatusVisible();
  setButtonLoading('#sp-submit', true, 'Download Spotify list');
  $('#sp-status').textContent = 'Fetching Spotify metadata...';
  setStatus('spotify', {
    phase: 'metadata',
    phaseLabel: 'Fetching Spotify',
    message: 'Gathering playlist data...',
    progress: 18,
    indeterminate: true,
    countLabel: '—',
  });
  startPolling('spotify', jobId);
  try {
    const res = await fetch('/api/v1/spotify/mirror', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, bitrate, job_id: jobId })
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || 'Spotify mirror failed');
    }
    const data = await res.json();
    setStatus('spotify', {
      phase: 'downloading',
      phaseLabel: 'Downloading',
      message: 'Collecting tracks via YouTube...',
      progress: 46,
      indeterminate: true,
      countLabel: '—',
    });
    renderSpotifyResult(data);
    const count = data.track_count || 0;
    const done = data.downloaded || 0;
    setStatus('spotify', {
      phase: 'done',
      phaseLabel: 'Completed',
      message: `${data.playlist_title}: finished ${done}/${count} tracks`,
      progress: 100,
      indeterminate: false,
      countLabel: `${done}/${count || '?'}`,
    });
    $('#sp-status').textContent = `${data.playlist_title}: finished ${done}/${count} tracks. Summary below.`;
    showToast(`${data.playlist_title}: ${done}/${count} tracks`, 'success');
    clearInputs(['#sp-url']);
  } catch (err) {
    const msg = err.message || 'Spotify mirror failed';
    $('#sp-status').textContent = msg;
    setStatus('spotify', {
      phase: 'error',
      phaseLabel: 'Error',
      message: msg,
      progress: 0,
      indeterminate: false,
      countLabel: '—',
    });
    showToast(msg, 'error');
  }
  setButtonLoading('#sp-submit', false, 'Download Spotify list');
  stopPolling();
}

function isValidUrl(value, allowedPrefixes) {
  if (!value) return false;
  return allowedPrefixes.some((p) => value.startsWith(p));
}

function renderSpotifyResult(data) {
  const tracks = data.tracks || [];
  const total = data.track_count || tracks.length || 0;
  const done = data.downloaded != null ? data.downloaded : total;
  renderResult(data, 'spotify');
  const status = `${data.playlist_title || 'Spotify list'}: finished ${done}/${total || '?'} tracks. Summary below.`;
  const statusEl = document.querySelector('#sp-status');
  if (statusEl) statusEl.textContent = status;
}

function revealFeatureChips() {
  const chips = Array.from(document.querySelectorAll('#hero-features .feature-chip'));
  chips.forEach((chip, idx) => setTimeout(() => chip.classList.add('revealed'), 140 + idx * 110));
}
revealFeatureChips();

function renderResult(data, mode) {
  const body = document.querySelector('#result-body');
  const kindBadge = document.querySelector('#result-kind');
  if (!body || !kindBadge) return;

  const variant = typeof mode === 'boolean' ? (mode ? 'playlist' : 'single') : (mode || 'single');

  if (variant === 'playlist') {
    const title = data.playlist_title || 'Playlist';
    const items = data.items || [];
    const count = data.count != null ? data.count : items.length;
    kindBadge.textContent = `${count} items`;
    const first = items[0] || {};
    const duration = data.duration_seconds != null ? `${data.duration_seconds.toFixed(1)} s` : 'n/a';
    const rows = [
      { label: 'Playlist', value: title },
      { label: 'First title', value: first.title || 'n/a' },
      { label: 'Kind', value: first.kind || 'playlist' },
      { label: 'Files', value: count },
      { label: 'Downloaded in', value: duration },
    ];
    body.innerHTML = rows.map(r => rowMarkup(r.label, r.value)).join('');
  } else if (variant === 'spotify') {
    const title = data.playlist_title || 'Spotify collection';
    const total = data.track_count || (data.tracks ? data.tracks.length : 0) || 0;
    const done = data.downloaded != null ? data.downloaded : total;
    const source = data.source_type || 'playlist';
    const manifest = data.manifest_path || data.manifest || 'n/a';
    kindBadge.textContent = `${done}/${total || '?'} tracks`;
    const rows = [
      { label: 'Collection', value: title },
      { label: 'Owner', value: data.owner || 'n/a' },
      { label: 'Source', value: source },
      { label: 'Tracks saved', value: `${done}/${total || '?'} tracks` },
      { label: 'Manifest', value: manifest },
    ];
    body.innerHTML = rows.map(r => rowMarkup(r.label, r.value)).join('');
  } else {
    kindBadge.textContent = data.kind || 'download';
    const name = data.title || 'Unknown title';
    const size = data.size_mb != null ? `${data.size_mb.toFixed(2)} MB` : 'n/a';
    const duration = data.duration_minutes != null ? `${data.duration_minutes.toFixed(2)} min` : 'n/a';
    const dlDuration = data.duration_seconds != null ? `${data.duration_seconds.toFixed(1)} s` : 'n/a';
    const path = data.filepath ? basename(data.filepath) : 'n/a';
    const rows = [
      { label: 'Title', value: name },
      { label: 'Kind', value: data.kind || 'n/a' },
      { label: 'Size', value: size },
      { label: 'Duration', value: duration },
      { label: 'Downloaded in', value: dlDuration },
      { label: 'Saved as', value: path },
    ];
    body.innerHTML = rows.map(r => rowMarkup(r.label, r.value)).join('');
  }
  document.querySelector('#result').hidden = false;
}

function rowMarkup(label, value) {
  return `<div class="result-row"><span class="muted">${label}</span><span class="value">${value}</span></div>`;
}

function basename(p) {
  if (!p) return '';
  const parts = p.split(/[/\\]/);
  return parts[parts.length - 1];
}

function clearInputs(ids) {
  (ids || []).forEach(id => {
    const el = document.querySelector(id);
    if (el) el.value = '';
  });
}

function setButtonLoading(selector, isLoading, label) {
  const btn = document.querySelector(selector);
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
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}
