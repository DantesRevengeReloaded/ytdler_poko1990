const $ = (s) => document.querySelector(s);

async function postDownload() {
  const url = $('#url').value.trim();
  const kind = $('#kind').value;
  const resolution = $('#resolution').value;
  const bitrate = $('#bitrate').value;
  if (!url) {
    showToast('Enter a YouTube URL.', 'error');
    return;
  }
  setButtonLoading('#submit', true, 'Download');
  try {
    const res = await fetch('/api/v1/downloads/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, kind, resolution, bitrate })
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || 'Request failed');
    }
    const data = await res.json();
    renderResult(data, false);
    showToast('Download complete', 'success');
    clearInputs();
    await loadStats();
  } catch (err) {
    showToast(err.message || 'Download failed', 'error');
  }
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
  setButtonLoading('#pl-submit', true, 'Download Playlist');
  try {
    const res = await fetch('/api/v1/downloads/playlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, kind, resolution, bitrate })
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || 'Request failed');
    }
    const data = await res.json();
    renderResult(data, true);
    showToast(`Playlist downloaded (${data.count} items)`, 'success');
    clearInputs();
    await loadStats();
  } catch (err) {
    showToast(err.message || 'Playlist failed', 'error');
  }
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
    const rows = [
      { label: 'Playlist', value: title },
      { label: 'First title', value: first.title || 'n/a' },
      { label: 'Kind', value: first.kind || 'playlist' },
      { label: 'Files', value: data.count },
    ];
    body.innerHTML = rows.map(r => rowMarkup(r.label, r.value)).join('');
  } else {
    kindBadge.textContent = data.kind || 'download';
    const name = data.title || 'Unknown title';
    const size = data.size_mb != null ? `${data.size_mb.toFixed(2)} MB` : 'n/a';
    const duration = data.duration_minutes != null ? `${data.duration_minutes.toFixed(2)} min` : 'n/a';
    const path = data.filepath ? basename(data.filepath) : 'n/a';
    const rows = [
      { label: 'Title', value: name },
      { label: 'Kind', value: data.kind || 'n/a' },
      { label: 'Size', value: size },
      { label: 'Duration', value: duration },
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
