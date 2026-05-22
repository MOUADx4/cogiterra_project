/* ============================================================================
 * Cogiterra Bounces · Dashboard PHP — Front JS
 * Plotly + interactions + AJAX
 * ============================================================================ */

const CATEGORY_COLORS = {
  hard_bounce:     '#ef4444',
  soft_bounce:     '#f59e0b',
  address_change:  '#3b82f6',
  technical_error: '#a855f7',
  unknown:         '#64748b',
};
const CATEGORY_LABELS = {
  hard_bounce:     'Hard bounce',
  soft_bounce:     'Soft bounce',
  address_change:  'Changement',
  technical_error: 'Technique',
  unknown:         'Non classifié',
};

const plotlyDark = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { color: '#cbd5e1', family: 'Inter, sans-serif', size: 12 },
  margin: { l: 50, r: 20, t: 30, b: 50 },
  xaxis: {
    gridcolor: 'rgba(255,255,255,0.04)',
    zerolinecolor: 'rgba(255,255,255,0.05)',
    tickfont: { color: '#94a3b8' },
  },
  yaxis: {
    gridcolor: 'rgba(255,255,255,0.04)',
    zerolinecolor: 'rgba(255,255,255,0.05)',
    tickfont: { color: '#94a3b8' },
  },
  hoverlabel: {
    bgcolor: '#1e293b',
    bordercolor: 'rgba(255,255,255,0.1)',
    font: { color: '#f1f5f9', family: 'Inter' },
  },
  legend: { font: { color: '#cbd5e1' }, bgcolor: 'rgba(0,0,0,0)' },
};

const PLOTLY_CFG = { displayModeBar: false, responsive: true, locale: 'fr' };

// ---------- Toast ----------
function toast(msg, type = 'ok') {
  const el = document.createElement('div');
  el.className = 'toast' + (type === 'error' ? ' error' : '');
  el.textContent = msg;
  document.body.appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => el.remove(), 250);
  }, 2800);
}

// ---------- Donut catégories ----------
function chartDonut(elId, distrib) {
  const labels = Object.keys(distrib);
  const values = labels.map(k => distrib[k]);
  const colors = labels.map(k => CATEGORY_COLORS[k] || '#64748b');
  const niceLabels = labels.map(k => CATEGORY_LABELS[k] || k);

  Plotly.newPlot(elId, [{
    type: 'pie',
    labels: niceLabels,
    values,
    hole: 0.62,
    marker: { colors, line: { color: 'rgba(0,0,0,0.5)', width: 2 } },
    textinfo: 'percent',
    textfont: { color: '#fafafa', size: 13, family: 'Inter' },
    hovertemplate: '%{label}<br>%{value} bounces (%{percent})<extra></extra>',
  }], {
    ...plotlyDark,
    showlegend: true,
    legend: { ...plotlyDark.legend, orientation: 'v', y: 0.5, x: 1.05 },
    margin: { l: 10, r: 110, t: 20, b: 10 },
    height: 340,
  }, PLOTLY_CFG);
}

// ---------- Stacked area historique 30j ----------
function chartHistory(elId, history) {
  if (!history.length) return;
  const dates = history.map(h => h.report_date);
  const cats = [
    ['n_hard_bounce',    'Hard',     '#ef4444'],
    ['n_soft_bounce',    'Soft',     '#f59e0b'],
    ['n_address_change', 'Change',   '#3b82f6'],
    ['n_technical',      'Technique','#a855f7'],
    ['n_unknown',        'Unknown',  '#64748b'],
  ];
  const traces = cats.map(([k, name, color]) => ({
    x: dates,
    y: history.map(h => +h[k] || 0),
    name,
    type: 'scatter',
    mode: 'lines',
    stackgroup: 'one',
    line: { width: 0.5, color },
    fillcolor: color + 'aa',
    hovertemplate: `<b>${name}</b><br>%{y} bounces<extra></extra>`,
  }));
  Plotly.newPlot(elId, traces, {
    ...plotlyDark,
    height: 360,
    legend: { ...plotlyDark.legend, orientation: 'h', y: -0.18 },
  }, PLOTLY_CFG);
}

// ---------- Méthodes : rules vs llm ----------
function chartMethods(elId, stats) {
  const labels = ['Règles', 'LLM Claude'];
  const values = [stats.n_rules, stats.n_llm];
  Plotly.newPlot(elId, [{
    type: 'bar',
    x: labels,
    y: values,
    marker: {
      color: ['#3b82f6', '#a855f7'],
      line: { color: 'rgba(0,0,0,0.4)', width: 1 },
    },
    text: values.map(v => v.toLocaleString('fr-FR')),
    textposition: 'outside',
    textfont: { color: '#fafafa', size: 14, family: 'Inter' },
    hovertemplate: '%{x}: %{y} bounces<extra></extra>',
  }], {
    ...plotlyDark,
    height: 260,
    margin: { l: 40, r: 20, t: 30, b: 40 },
    yaxis: { ...plotlyDark.yaxis, title: '' },
  }, PLOTLY_CFG);
}

// ---------- Top domaines ----------
function chartDomains(elId, domains) {
  if (!domains.length) return;
  // Inverse pour avoir le top en haut
  const sorted = [...domains].reverse();
  Plotly.newPlot(elId, [{
    type: 'bar',
    orientation: 'h',
    y: sorted.map(d => d.domain),
    x: sorted.map(d => +d.n),
    marker: {
      color: '#60a5fa',
      line: { color: 'rgba(0,0,0,0.4)', width: 1 },
    },
    text: sorted.map(d => d.n),
    textposition: 'outside',
    textfont: { color: '#fafafa', family: 'Inter' },
    hovertemplate: '<b>%{y}</b><br>%{x} bounces<extra></extra>',
  }], {
    ...plotlyDark,
    height: Math.max(260, sorted.length * 32 + 40),
    margin: { l: 140, r: 30, t: 20, b: 30 },
  }, PLOTLY_CFG);
}

// ---------- Health gauge (SVG natif, pas Plotly) ----------
function renderGauge(score) {
  const el = document.getElementById('healthGauge');
  if (!el) return;
  let color = '#34d399';
  if (score < 50) color = '#f87171';
  else if (score < 70) color = '#fbbf24';
  else if (score < 85) color = '#60a5fa';
  const r = 70;
  const c = 2 * Math.PI * r;
  const off = c * (1 - score / 100);
  el.innerHTML = `
    <svg viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="${r}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="14"/>
      <circle cx="100" cy="100" r="${r}" fill="none" stroke="${color}" stroke-width="14"
              stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${off}"
              transform="rotate(-90 100 100)" style="transition:stroke-dashoffset 0.6s"/>
    </svg>
    <div class="gauge-text">
      <div class="v gradient-green">${score}<span style="font-size:1rem;color:#71717a;">/100</span></div>
      <div class="l">Health score</div>
    </div>
  `;
}

// ---------- AJAX helpers ----------
async function postAction(url, body = {}) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return r.json();
}

// ---------- Actions sidebar ----------
async function actionPoll(btn) {
  btn.disabled = true;
  const orig = btn.innerHTML;
  btn.innerHTML = '<span class="mi">sync</span><span>Polling…</span>';
  try {
    const r = await postAction('api/poll.php');
    if (r.code === 0) toast('✅ Poll IMAP terminé');
    else toast('Échec du poll (code ' + r.code + ')', 'error');
  } catch (e) { toast('Erreur réseau', 'error'); }
  btn.innerHTML = orig; btn.disabled = false;
  setTimeout(() => location.reload(), 800);
}
async function actionReport(btn) {
  btn.disabled = true;
  const orig = btn.innerHTML;
  btn.innerHTML = '<span class="mi">sync</span><span>Génération…</span>';
  try {
    const r = await postAction('api/report.php');
    if (r.code === 0) toast('✅ Rapport envoyé');
    else toast('Échec du rapport (code ' + r.code + ')', 'error');
  } catch (e) { toast('Erreur réseau', 'error'); }
  btn.innerHTML = orig; btn.disabled = false;
  setTimeout(() => location.reload(), 800);
}
async function actionDemo(btn) {
  if (!confirm('Injecter les données démo ? Cela écrase la base actuelle.')) return;
  btn.disabled = true;
  try {
    const r = await postAction('api/demo.php');
    if (r.ok) toast('✨ Données démo injectées');
    else toast('Erreur injection', 'error');
  } catch (e) { toast('Erreur réseau', 'error'); }
  btn.disabled = false;
  setTimeout(() => location.reload(), 600);
}

// ---------- Adopter/rejeter une règle ----------
async function adoptRule(id, btn) {
  btn.disabled = true;
  const r = await postAction('api/adopt.php', { id });
  if (r.ok) {
    toast('✅ Règle adoptée');
    btn.closest('.suggestion').style.opacity = '0.4';
    setTimeout(() => btn.closest('.suggestion').remove(), 400);
  } else {
    toast('Erreur : pattern invalide', 'error');
    btn.disabled = false;
  }
}
async function rejectRule(id, btn) {
  btn.disabled = true;
  const r = await postAction('api/reject.php', { id });
  if (r.ok) {
    toast('Règle rejetée');
    btn.closest('.suggestion').style.opacity = '0.4';
    setTimeout(() => btn.closest('.suggestion').remove(), 400);
  }
}

// ---------- Filtres : reload la table aujourd'hui ----------
function applyFilter() {
  const f = (id) => document.getElementById(id)?.value || '';
  const params = new URLSearchParams({
    category: f('fltCat'),
    method:   f('fltMethod'),
    search:   f('fltSearch'),
  });
  fetch('api/today.php?' + params.toString())
    .then(r => r.json())
    .then(d => {
      const tbody = document.querySelector('#todayTable tbody');
      if (!tbody) return;
      tbody.innerHTML = '';
      if (!d.rows.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="center muted" style="padding:40px;">Aucun résultat</td></tr>';
        return;
      }
      d.rows.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="mono">${escapeHtml(r.email_address || '')}</td>
          <td><span class="badge ${categoryBadgeClass(r.category)}">${CATEGORY_LABELS[r.category] || r.category}</span></td>
          <td>${r.confidence ? (+r.confidence).toFixed(2) : '—'}</td>
          <td>${r.method || ''}</td>
          <td class="muted">${truncate(r.reason || '', 60)}</td>
          <td class="font-mono">${formatDate(r.processed_at)}</td>
        `;
        tbody.appendChild(tr);
      });
      document.getElementById('todayCount').textContent = d.rows.length;
    });
}

function categoryBadgeClass(cat) {
  return {
    hard_bounce:     'badge-danger',
    soft_bounce:     'badge-warn',
    address_change:  'badge-info',
    technical_error: 'badge-violet',
  }[cat] || 'badge-muted';
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, m => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[m]);
}
function truncate(s, n) { return s.length <= n ? s : s.slice(0, n - 1) + '…'; }
function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

// ---------- Refresh auto pour activité live ----------
function startLiveRefresh() {
  if (!document.getElementById('liveFeed')) return;
  setInterval(async () => {
    try {
      const r = await fetch('api/live.php').then(r => r.json());
      const feed = document.getElementById('liveFeed');
      feed.innerHTML = r.rows.map(item => `
        <div class="suggestion" style="margin-bottom:8px;">
          <div>
            <div class="row gap-2">
              <span class="mono">${escapeHtml(item.email_address || '')}</span>
              <span class="badge ${categoryBadgeClass(item.category)}">${CATEGORY_LABELS[item.category] || item.category}</span>
            </div>
            <div class="sample">${escapeHtml(truncate(item.reason || '', 100))}</div>
          </div>
          <div class="dim font-mono">${formatDate(item.processed_at)}</div>
        </div>
      `).join('');
    } catch (e) {}
  }, 5000);
}

// Auto-bind les filtres au chargement
document.addEventListener('DOMContentLoaded', () => {
  ['fltCat', 'fltMethod', 'fltSearch'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      const evt = id === 'fltSearch' ? 'input' : 'change';
      el.addEventListener(evt, debounce(applyFilter, 200));
    }
  });
  startLiveRefresh();
});

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
