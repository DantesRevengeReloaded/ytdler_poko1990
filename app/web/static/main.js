const $ = (s) => document.querySelector(s);

const defaultStatus = { phase: 'idle', phaseLabel: 'Idle', message: 'No work in progress', progress: 0, indeterminate: false };
const statusState = {
  single: { ...defaultStatus },
  playlist: { ...defaultStatus },
};
const progressTimers = { single: null, playlist: null };

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
  ['single', 'playlist'].forEach((type) => {
    const state = statusState[type];
    const progressEl = document.querySelector(`#${type}-progress`);
    const textEl = document.querySelector(`#${type}-progress-text`);
    const labelEl = document.querySelector(`#${type}-status-label`);
    if (!progressEl || !textEl || !labelEl) return;
    progressEl.classList.toggle('indeterminate', !!state.indeterminate);
    progressEl.style.width = state.indeterminate ? '42%' : `${state.progress || 0}%`;
    textEl.textContent = state.message;
    labelEl.textContent = state.phaseLabel || state.phase || 'Idle';
  });
  const pill = document.querySelector('#status-pill');
  if (!pill) return;
  const working = ['single', 'playlist'].some((t) => {
    const p = statusState[t].phase;
    return p && !['idle', 'done', 'error'].includes(p);
  });
  pill.textContent = working ? 'In progress' : 'No work in progress';
  pill.classList.toggle('pill-busy', working);
  pill.classList.toggle('pill-soft', !working);
}

function startPolling(type, jobId) {
  stopPolling(type);
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
      const percent = data.progress_percent != null ? data.progress_percent : total ? (completed / total) * 100 : (statusState[type].progress || 0);
      const label = data.phase === 'done' ? 'Completed' : data.phase === 'error' ? 'Error' : data.phase || 'Working';
      const baseTitle = data.playlist_title || '';
      const counts = total ? `${completed}/${total}` : '';
      let message = data.message || 'Working...';
      if (data.job_type === 'playlist' && total) {
        const titlePart = baseTitle ? `${baseTitle}:` : 'Playlist:';
        message = `${titlePart} Total ${total} songs ${counts} downloaded`;
      } else if (counts) {
        message = `${counts} • ${message}`;
      }
      setStatus(type, {
        phase: data.phase,
        phaseLabel: label,
        message,
        progress: percent,
        indeterminate: !total,
      });
      if (data.phase === 'done' || data.phase === 'error') {
        stopPolling(type);
      }
    } catch (err) {
      stopPolling(type);
    }
  };
  tick();
  progressTimers[type] = setInterval(tick, 900);
}

function stopPolling(type) {
  if (progressTimers[type]) {
    clearInterval(progressTimers[type]);
    progressTimers[type] = null;
  }
}

function setStatus(type, patch) {
  statusState[type] = { ...statusState[type], ...patch };
  renderStatus();
}

function resetStatus(type) {
  setStatus(type, { phase: 'idle', phaseLabel: 'Idle', message: 'No work in progress', progress: 0, indeterminate: false });
}

async function postDownload() {
  const url = $('#url').value.trim();
  const kind = $('#kind').value;
  const resolution = $('#resolution').value;
  const bitrate = $('#bitrate').value;
  if (!url) {
    showToast('Enter a YouTube URL.', 'error');
    return;
  }
  const jobId = createJobId();
  ensureStatusVisible();
  setStatus('single', {
    phase: 'metadata',
    phaseLabel: 'Fetching metadata',
    message: 'Fetching video details...',
    progress: 12,
    indeterminate: true,
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
    });
    clearInputs();
    await loadStats();
  } catch (err) {
    showToast(err.message || 'Download failed', 'error');
    setStatus('single', {
      phase: 'error',
      phaseLabel: 'Error',
      message: err.message || 'Download failed',
      progress: 0,
      indeterminate: false,
    });
  }
  stopPolling('single');
  setButtonLoading('#submit', false, 'Download');
  $('#status').textContent = '';
}

async function postPlaylist() {
  const url = $('#pl-url').value.trim();
  const kind = $('#pl-kind').value;
  const resolution = $('#pl-resolution').value;
  const bitrate = $('#pl-bitrate').value;
  if (!url) {
    showToast('Enter a playlist URL.', 'error');
    return;
  }
  const jobId = createJobId();
  ensureStatusVisible();
  setStatus('playlist', {
    phase: 'metadata',
    phaseLabel: 'Fetching metadata',
    message: 'Fetching playlist details...',
    progress: 10,
    indeterminate: true,
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
    });
    clearInputs();
    await loadStats();
  } catch (err) {
    showToast(err.message || 'Playlist failed', 'error');
    setStatus('playlist', {
      phase: 'error',
      phaseLabel: 'Error',
      message: err.message || 'Playlist failed',
      progress: 0,
      indeterminate: false,
    });
  }
  stopPolling('playlist');
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

function revealFeatureChips() {
  const chips = Array.from(document.querySelectorAll('#hero-features .feature-chip'));
  chips.forEach((chip, idx) => setTimeout(() => chip.classList.add('revealed'), 140 + idx * 110));
}
revealFeatureChips();

function renderResult(data, isPlaylist) {
  const body = document.querySelector('#result-body');
  const kindBadge = document.querySelector('#result-kind');
  if (!body || !kindBadge) return;

  if (isPlaylist) {
    const title = data.playlist_title || 'Playlist';
    kindBadge.textContent = `${data.count} items`;
    const items = data.items || [];
    const first = items[0] || {};
    const duration = data.duration_seconds != null ? `${data.duration_seconds.toFixed(1)} s` : 'n/a';
    const rows = [
      { label: 'Playlist', value: title },
      { label: 'First title', value: first.title || 'n/a' },
      { label: 'Kind', value: first.kind || 'playlist' },
      { label: 'Files', value: data.count },
      { label: 'Downloaded in', value: duration },
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

function clearInputs() {
  const ids = ['#url', '#pl-url'];
  ids.forEach(id => {
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
