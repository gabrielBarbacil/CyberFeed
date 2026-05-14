// static/js/app.js
//
// Maneja toda la logica del frontend:
// - Fetch a la API de FastAPI
// - Renderizado de cards
// - Filtros y busqueda
// - Actualizacion manual

let currentTab = 'all';
let currentSeverity = 'all';
let searchQuery = '';

// ------------------------------------------------------------------------------
// Inicializacion
// ------------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  loadFeed();
});

// ------------------------------------------------------------------------------
// Carga y renderizado del feed
// ------------------------------------------------------------------------------
async function loadFeed() {
  const feed = document.getElementById('feed');
  feed.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <p>Consultando NVD y feeds RSS...</p>
    </div>`;

  try {
    const params = new URLSearchParams({
      type: currentTab,
      severity: currentSeverity,
      q: searchQuery,
    });

    const resp = await fetch(`/api/feed?${params}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    updateStats(data.stats);
    updateLastUpdated(data.last_updated);
    renderCards(data.items);

  } catch (err) {
    feed.innerHTML = `
      <div class="empty">
        <p>Error al cargar el feed. Reintentando...</p>
        <p style="margin-top:8px;font-size:11px;opacity:0.5">${err.message}</p>
      </div>`;
  }
}

// ------------------------------------------------------------------------------
// Renderizado de cards
// ------------------------------------------------------------------------------
function renderCards(items) {
  const feed = document.getElementById('feed');

  if (!items.length) {
    feed.innerHTML = '<div class="empty">No se encontraron resultados.</div>';
    return;
  }

  feed.innerHTML = items.map(item => {
    return item.type === 'cve' ? renderCveCard(item) : renderNewsCard(item);
  }).join('');
}

function renderCveCard(item) {
  const scoreClass = item.severity === 'critical' ? 'critical' : '';
  const badgeLabel = item.severity === 'critical' ? 'CRÍTICO' : 'ALTO';

  return `
    <div class="card ${item.severity}">
      <div class="card-header">
        <div class="card-title">${escapeHtml(item.title)}</div>
        <span class="badge ${item.severity}">${badgeLabel}</span>
      </div>
      <div class="card-meta">
        <span>📅 ${item.published}</span>
        ${item.cvss_score ? `<span>CVSS <strong class="cvss-score ${scoreClass}">${item.cvss_score.toFixed(1)}</strong></span>` : ''}
        ${item.affected ? `<span>🎯 ${escapeHtml(item.affected)}</span>` : ''}
      </div>
      <div class="card-summary">${escapeHtml(item.description)}</div>
      <div class="card-footer">
        <a href="${item.url}" target="_blank" rel="noopener" class="card-link">
          Ver en NVD →
        </a>
        <div class="tags">
          <span class="tag">${item.id}</span>
        </div>
      </div>
    </div>`;
}

function renderNewsCard(item) {
  const tagsHtml = (item.tags || [])
    .slice(0, 3)
    .map(t => `<span class="tag">${escapeHtml(t)}</span>`)
    .join('');

  return `
    <div class="card news">
      <div class="card-header">
        <div class="card-title">${escapeHtml(item.title)}</div>
        <span class="badge news">NOTICIA</span>
      </div>
      <div class="card-meta">
        <span>📰 ${escapeHtml(item.source)}</span>
        <span>📅 ${item.published}</span>
      </div>
      <div class="card-summary">${escapeHtml(item.summary)}</div>
      <div class="card-footer">
        <a href="${item.url}" target="_blank" rel="noopener" class="card-link">
          Leer artículo →
        </a>
        <div class="tags">${tagsHtml}</div>
      </div>
    </div>`;
}

// ------------------------------------------------------------------------------
// Stats y metadatos
// ------------------------------------------------------------------------------
function updateStats(stats) {
  if (!stats) return;
  document.getElementById('stat-critical').textContent = stats.critical ?? '—';
  document.getElementById('stat-high').textContent = stats.high ?? '—';
  document.getElementById('stat-news').textContent = stats.news ?? '—';
}

function updateLastUpdated(ts) {
  const el = document.getElementById('last-updated');
  el.textContent = ts ? `Actualizado: ${ts}` : '';
}

// ------------------------------------------------------------------------------
// Controles: tabs, filtros, busqueda
// ------------------------------------------------------------------------------
function setTab(btn, tab) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');

  // El filtro de severidad solo aplica a CVEs
  const severityFilter = document.getElementById('severity-filter');
  severityFilter.disabled = (tab === 'news');
  if (tab === 'news') {
    currentSeverity = 'all';
    severityFilter.value = 'all';
  }

  loadFeed();
}

function applyFilters() {
  currentSeverity = document.getElementById('severity-filter').value;
  searchQuery = document.getElementById('search-input').value.trim();

  // Debounce simple para la busqueda
  clearTimeout(window._searchTimer);
  window._searchTimer = setTimeout(loadFeed, 350);
}

// ------------------------------------------------------------------------------
// Actualizacion manual
// ------------------------------------------------------------------------------
async function refreshData() {
  const btn = document.querySelector('.refresh-btn');
  btn.classList.add('spinning');
  btn.disabled = true;

  try {
    await fetch('/api/refresh');
    await loadFeed();
  } catch (err) {
    console.error('Error al refrescar:', err);
  } finally {
    btn.classList.remove('spinning');
    btn.disabled = false;
  }
}

// ------------------------------------------------------------------------------
// Utilidad: escape HTML para evitar XSS al renderizar datos externos
// ------------------------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
