// app.js — KrishiMind v3 Frontend Logic
const API = 'http://localhost:8001';

// ── Tab Navigation ─────────────────────────────────────────────────────────
function showTab(id) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('tab-' + id).classList.remove('hidden');
  document.querySelector(`[data-tab="${id}"]`).classList.add('active');
}

// ── Helpers ────────────────────────────────────────────────────────────────
function setLoading(btnId, loading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  btn.innerHTML = loading
    ? '<span class="spinner"></span> Analyzing...'
    : btn.dataset.label;
}

function showResult(containerId, html) {
  const el = document.getElementById(containerId);
  el.innerHTML = html;
  el.classList.remove('hidden');
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function fmt(n) { return Number(n).toLocaleString('en-IN'); }

// ── Health Check ───────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`);
    const d = await r.json();
    document.getElementById('status-text').textContent = d.status;
    document.getElementById('status-badge').style.display = 'flex';
  } catch {
    document.getElementById('status-text').textContent = '⚠️ Backend offline';
  }
}

// ══════════════════════════════════════════════════════════════════════════
// CROP AGENT
// ══════════════════════════════════════════════════════════════════════════
async function runCrop() {
  setLoading('crop-btn', true);
  const body = {
    N:           +document.getElementById('c-N').value,
    P:           +document.getElementById('c-P').value,
    K:           +document.getElementById('c-K').value,
    temperature: +document.getElementById('c-temp').value,
    pH:          +document.getElementById('c-pH').value,
    humidity:    +document.getElementById('c-hum').value,
    rainfall:    +document.getElementById('c-rain').value,
    season:      document.getElementById('c-season').value || null,
  };
  try {
    const r = await fetch(`${API}/crop`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    showResult('crop-result', renderCropResult(d));
  } catch (e) {
    showResult('crop-result', `<p style="color:var(--red-400)">Error: ${e.message}</p>`);
  }
  setLoading('crop-btn', false);
}

function renderCropResult(d) {
  const cards = d.top_crops.map((c, i) => `
    <div class="crop-card" style="--confidence:${c.confidence}%">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div class="crop-name">${c.icon} ${i + 1}. ${c.crop}</div>
        <div class="crop-confidence">${c.confidence}% match</div>
      </div>
      <div style="font-size:12px;color:var(--text-muted);margin:4px 0">${c.description}</div>
      <div style="font-size:11px;color:var(--green-600);margin:4px 0">Seasons: ${c.season_fit.join(', ')}</div>
      <div class="crop-reasons">${c.reasons.map(r => `<div class="reason-item">${r}</div>`).join('')}</div>
    </div>`).join('');

  return `<div class="result-panel">
    <div class="card-title">🌾 Crop Recommendations</div>
    ${cards}
    <div class="ai-box"><strong>Soil Health:</strong> ${d.soil_health}<br><br>
    <strong>Summary:</strong> ${d.summary}</div>
  </div>`;
}

// ══════════════════════════════════════════════════════════════════════════
// IRRIGATION AGENT
// ══════════════════════════════════════════════════════════════════════════
async function runIrrigation() {
  setLoading('irr-btn', true);
  const body = {
    crop:       document.getElementById('i-crop').value,
    location:   document.getElementById('i-loc').value,
    soil_type:  document.getElementById('i-soil').value,
    land_acres: +document.getElementById('i-acres').value,
  };
  try {
    const r = await fetch(`${API}/irrigation`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    showResult('irr-result', renderIrrResult(d));
  } catch (e) {
    showResult('irr-result', `<p style="color:var(--red-400)">Error: ${e.message}</p>`);
  }
  setLoading('irr-btn', false);
}

function renderIrrResult(d) {
  const days = d.schedule.map(day => `
    <div class="day-card ${day.water_needed ? 'irrigate' : 'no-water'}">
      <div class="day-date">${day.date.slice(5)}</div>
      <div class="day-icon">${day.water_needed ? '💧' : '✅'}</div>
      <div style="font-size:10px;color:var(--text-muted)">${day.etc_mm}mm ETc</div>
      <div class="day-litres">${day.water_needed ? fmt(day.litres) + 'L' : 'Rain OK'}</div>
      <div style="font-size:9px;color:var(--text-muted);margin-top:3px">${day.temp_max}°/${day.temp_min}°</div>
    </div>`).join('');

  return `<div class="result-panel">
    <div class="card-title">💧 7-Day Irrigation Schedule</div>
    <div style="display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap">
      <div style="text-align:center">
        <div style="font-size:28px;font-weight:800;color:var(--blue-400)">${d.irrigation_days}</div>
        <div style="font-size:11px;color:var(--text-muted)">Irrigation Days</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:28px;font-weight:800;color:var(--green-400)">${fmt(d.total_water_litres)}L</div>
        <div style="font-size:11px;color:var(--text-muted)">Total Water</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:28px;font-weight:800;color:var(--amber-400)">${d.kc_used}</div>
        <div style="font-size:11px;color:var(--text-muted)">Kc (crop coeff)</div>
      </div>
      <div style="font-size:11px;color:var(--text-muted);align-self:center">
        Weather: ${d.weather_source === 'live' ? '🌐 Live API' : '🔮 Synthetic'}
      </div>
    </div>
    <div class="schedule-grid">${days}</div>
    <div class="ai-box" style="margin-top:14px">${d.summary}</div>
  </div>`;
}

// ══════════════════════════════════════════════════════════════════════════
// PEST AGENT
// ══════════════════════════════════════════════════════════════════════════
let pestFile = null;

function setupPestDrop() {
  const zone = document.getElementById('drop-zone');
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragging'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('dragging');
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith('image/')) setPestFile(f);
  });
  zone.addEventListener('click', () => document.getElementById('pest-file').click());
  document.getElementById('pest-file').addEventListener('change', e => {
    if (e.target.files[0]) setPestFile(e.target.files[0]);
  });
}

function setPestFile(f) {
  pestFile = f;
  const reader = new FileReader();
  reader.onload = ev => {
    const img = document.getElementById('pest-preview');
    img.src = ev.target.result;
    img.classList.remove('hidden');
    document.getElementById('drop-hint').textContent = f.name;
  };
  reader.readAsDataURL(f);
}

async function runPest() {
  if (!pestFile) { alert('Please upload a leaf/crop image first'); return; }
  setLoading('pest-btn', true);
  const formData = new FormData();
  formData.append('image', pestFile);
  formData.append('crop_name', document.getElementById('p-crop').value || 'unknown');
  try {
    const r = await fetch(`${API}/pest`, { method: 'POST', body: formData });
    const d = await r.json();
    showResult('pest-result', renderPestResult(d));
  } catch (e) {
    showResult('pest-result', `<p style="color:var(--red-400)">Error: ${e.message}</p>`);
  }
  setLoading('pest-btn', false);
}

function renderPestResult(d) {
  const sev = d.severity || '';
  const sevClass = sev.includes('High') ? 'severity-high' : sev.includes('Medium') ? 'severity-medium' : sev.includes('Low') ? 'severity-low' : 'severity-none';
  const bio = d.biological_treatment.map(t => `<li>${t}</li>`).join('');
  const chem = d.chemical_treatment.length
    ? `<div class="card-title" style="margin-top:14px">🧪 Chemical Treatment</div><ul class="treatment-list">${d.chemical_treatment.map(t=>`<li>${t}</li>`).join('')}</ul>` : '';

  return `<div class="result-panel">
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px">
      <div style="font-size:48px">${d.icon}</div>
      <div>
        <div style="font-size:22px;font-weight:800;color:var(--text-primary)">${d.pest}</div>
        <div class="${sevClass}" style="font-weight:600;margin:4px 0">${d.severity}</div>
        <div style="font-size:12px;color:var(--text-muted)">Confidence: ${d.confidence_pct}%</div>
      </div>
    </div>
    <div class="card-title">🌿 Biological Treatment</div>
    <ul class="treatment-list">${bio}</ul>
    ${chem}
    <div style="margin-top:12px;font-size:13px;color:var(--amber-400)">🛡️ Prevention: ${d.prevention}</div>
    <div class="ai-box" style="margin-top:14px"><strong>AI Reasoning:</strong> ${d.ai_reasoning}</div>
  </div>`;
}

// ══════════════════════════════════════════════════════════════════════════
// MARKET AGENT
// ══════════════════════════════════════════════════════════════════════════
async function runMarket() {
  setLoading('mkt-btn', true);
  const body = {
    crop:   document.getElementById('m-crop').value,
    region: document.getElementById('m-region').value,
  };
  try {
    const r = await fetch(`${API}/market`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    showResult('mkt-result', renderMarketResult(d));
    drawPriceChart(d.price_chart_data);
  } catch (e) {
    showResult('mkt-result', `<p style="color:var(--red-400)">Error: ${e.message}</p>`);
  }
  setLoading('mkt-btn', false);
}

function renderMarketResult(d) {
  const badgeClass = d.action === 'SELL' ? 'badge-sell' : d.action === 'HOLD' ? 'badge-hold' : 'badge-wait';
  const mspColor   = d.above_msp ? 'var(--green-400)' : 'var(--red-400)';

  return `<div class="result-panel">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
      <div>
        <div style="font-size:13px;color:var(--text-muted)">${d.crop} · ${d.region}</div>
        <div style="font-size:36px;font-weight:800;color:var(--text-primary)">₹${fmt(d.current_price)}<span style="font-size:14px;color:var(--text-muted)">/q</span></div>
        <div style="font-size:13px;color:${mspColor}">MSP: ₹${fmt(d.msp)} — ${d.above_msp ? '✅ Above MSP' : '⚠️ Below MSP'}</div>
      </div>
      <div class="badge ${badgeClass}" style="font-size:15px;padding:10px 18px">${d.badge}</div>
    </div>
    <div class="chart-wrap"><canvas id="priceChart"></canvas></div>
    <div class="ai-box">${d.reason}</div>
  </div>`;
}

function drawPriceChart(data) {
  const canvas = document.getElementById('priceChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth || 400;
  const H = 140;
  canvas.width = W; canvas.height = H;

  const prices = data.map(d => d.price);
  const min = Math.min(...prices) * 0.97;
  const max = Math.max(...prices) * 1.03;
  const toY = v => H - 20 - ((v - min) / (max - min)) * (H - 40);
  const toX = (i) => 40 + (i / (data.length - 1)) * (W - 60);

  // Grid
  ctx.strokeStyle = 'rgba(0,0,0,0.08)';
  ctx.lineWidth = 1;
  for (let i = 0; i < 4; i++) {
    const y = 10 + (i / 3) * (H - 30);
    ctx.beginPath(); ctx.moveTo(40, y); ctx.lineTo(W - 20, y); ctx.stroke();
  }

  // Gradient fill
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, 'rgba(33, 150, 243, 0.3)');
  grad.addColorStop(1, 'rgba(33, 150, 243, 0)');
  ctx.beginPath();
  data.forEach((d, i) => i === 0 ? ctx.moveTo(toX(i), toY(d.price)) : ctx.lineTo(toX(i), toY(d.price)));
  ctx.lineTo(toX(data.length - 1), H); ctx.lineTo(toX(0), H); ctx.closePath();
  ctx.fillStyle = grad; ctx.fill();

  // Line
  ctx.beginPath();
  data.forEach((d, i) => i === 0 ? ctx.moveTo(toX(i), toY(d.price)) : ctx.lineTo(toX(i), toY(d.price)));
  ctx.strokeStyle = '#2196F3'; ctx.lineWidth = 2.5; ctx.stroke();

  // Labels + dots
  ctx.fillStyle = 'rgba(0,0,0,0.6)';
  ctx.font = '10px Inter';
  data.forEach((d, i) => {
    const x = toX(i), y = toY(d.price);
    ctx.beginPath(); ctx.arc(x, y, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = '#2196F3'; ctx.fill();
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.fillText(d.label, x - 10, H - 2);
  });
}

// ══════════════════════════════════════════════════════════════════════════
// ADVISORY (Full Agentic Loop)
// ══════════════════════════════════════════════════════════════════════════
async function runAdvisory() {
  setLoading('adv-btn', true);
  const body = {
    farmer_name: document.getElementById('a-name').value || 'Farmer',
    location:    document.getElementById('a-loc').value,
    soil_type:   document.getElementById('a-soil').value,
    season:      document.getElementById('a-season').value,
    land_acres:  +document.getElementById('a-acres').value,
    N:           +document.getElementById('a-N').value,
    P:           +document.getElementById('a-P').value,
    K:           +document.getElementById('a-K').value,
    pH:          +document.getElementById('a-pH').value,
    temperature: +document.getElementById('a-temp').value,
    humidity:    60, rainfall: 80,
  };
  try {
    const r = await fetch(`${API}/advisory`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    showResult('adv-result', renderAdvisory(d));
  } catch (e) {
    showResult('adv-result', `<p style="color:var(--red-400)">Error: ${e.message}</p>`);
  }
  setLoading('adv-btn', false);
}

function renderAdvisory(d) {
  const actions = d.action_items.map(a => `<div class="action-item">${a}</div>`).join('');
  const topCrops = d.top_crops.slice(0,3).map((c,i) =>
    `<span style="margin-right:12px">${c.icon} ${i+1}. ${c.crop} <span style="color:var(--green-500)">${c.confidence}%</span></span>`
  ).join('');

  return `<div class="result-panel">
    <div class="card-title" style="font-size:18px">🤖 Full Advisory for ${d.farmer}</div>
    <div style="font-size:13px;color:var(--text-muted);margin-bottom:16px">${d.location} · ${d.season} · ${d.irrigation?.total_water_litres ? fmt(d.irrigation.total_water_litres)+'L/7 days' : ''}</div>
    <div style="margin-bottom:16px">${topCrops}</div>
    ${actions}
    <div style="margin-top:16px">
      <div style="font-size:12px;font-weight:600;color:var(--text-muted);margin-bottom:8px">MARKET SIGNAL</div>
      <div style="font-size:15px;color:var(--amber-400)">${d.market?.badge || ''} — ₹${fmt(d.market?.current_price || 0)}/q</div>
    </div>
    <div class="ai-box" style="margin-top:16px"><strong>AI Advisory:</strong><br>${d.ai_explanation}</div>
  </div>`;
}

// ══════════════════════════════════════════════════════════════════════════
// ASK (NLP Router)
// ══════════════════════════════════════════════════════════════════════════
async function runAsk() {
  const query = document.getElementById('ask-input').value.trim();
  if (!query) return;
  setLoading('ask-btn', true);
  const body = {
    query, location: 'Delhi', soil_type: 'loamy', land_acres: 1,
    crop: null,
  };
  try {
    const r = await fetch(`${API}/ask`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    const routed = d.routed_to || 'advisory';
    let html = `<div class="result-panel"><div style="font-size:12px;color:var(--text-muted);margin-bottom:10px">Routed to: <strong style="color:var(--green-400)">${routed}</strong> agent</div>`;
    if (routed === 'crop')         html += renderCropResult(d).replace('<div class="result-panel">', '').replace('</div>', '');
    else if (routed === 'market')  html += renderMarketResult(d).replace('<div class="result-panel">', '').replace('</div>', '');
    else html += `<pre style="white-space:pre-wrap;font-size:12px;color:var(--text-muted)">${JSON.stringify(d, null, 2)}</pre>`;
    html += '</div>';
    showResult('ask-result', html);
  } catch (e) {
    showResult('ask-result', `<p style="color:var(--red-400)">Error: ${e.message}</p>`);
  }
  setLoading('ask-btn', false);
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  setupPestDrop();
  showTab('crop');

  // Store button labels for restore
  document.querySelectorAll('.btn[id]').forEach(b => b.dataset.label = b.innerHTML);

  // Enter key for ask
  document.getElementById('ask-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); runAsk(); }
  });
});
