/* ============================================================
   LexAra — Frontend Script
   Tab-based contract analysis hitting api.lexara.tech
   ============================================================ */

const API_BASE = 'https://api.lexara.tech/v1';
const API_KEY  = 'Bearer demo-api-key-lexara';

/* ── Nav toggle (mobile) ───────────────────────────────────── */
const navToggle = document.querySelector('.nav-toggle');
const navMenu   = document.querySelector('nav[aria-label="Main navigation"]');
if (navToggle && navMenu) {
  navToggle.addEventListener('click', () => {
    const open = navMenu.classList.toggle('nav-open');
    navToggle.setAttribute('aria-expanded', String(open));
  });
}

/* ── Clear & Download buttons ──────────────────────────────── */
const clearBtn    = document.getElementById('clear-btn');
const downloadBtn = document.getElementById('download-btn');

if (clearBtn) {
  clearBtn.addEventListener('click', () => {
    if (textarea) textarea.value = '';
    cache = {};
    panels.forEach(p => { p.innerHTML = ''; p.classList.remove('tab-panel--active'); });
    if (placeholder) placeholder.style.display = 'flex';
    if (downloadBtn) downloadBtn.disabled = true;
    // Reset upload zone label
    const uploadLabel = document.querySelector('.upload-label');
    if (uploadLabel) uploadLabel.innerHTML = `Drop a file here or <span class="upload-link">browse</span>`;
    const uploadZoneEl = document.getElementById('upload-zone');
    if (uploadZoneEl) uploadZoneEl.classList.remove('upload-success');
    showToast('Cleared. Ready for a new contract.');
  });
}

/* ── Demo: Tab system ──────────────────────────────────────── */
const tabs        = document.querySelectorAll('.tab-btn');
const panels      = document.querySelectorAll('.tab-panel');
const placeholder = document.getElementById('demo-placeholder');
const textarea    = document.getElementById('contract-input');
const typeSelect  = document.getElementById('contract-type');
const jurisSelect = document.getElementById('jurisdiction');

let activeTab = 'summary';
let cache = {};  // tab -> result cache per contract text

function getPayload() {
  return {
    text:          textarea.value.trim(),
    contract_type: typeSelect.value,
    jurisdiction:  jurisSelect.value,
  };
}

function cacheKey(tab, payload) {
  return `${tab}__${payload.text.slice(0, 80)}__${payload.contract_type}__${payload.jurisdiction}`;
}

function setActiveTab(tabName) {
  activeTab = tabName;
  tabs.forEach(btn => {
    const isActive = btn.dataset.tab === tabName;
    btn.classList.toggle('tab-active', isActive);
    btn.setAttribute('aria-selected', String(isActive));
  });
  panels.forEach(panel => {
    panel.classList.remove('tab-panel--active');
  });
  const activePanel = document.getElementById(`tab-${tabName}`);
  if (activePanel) activePanel.classList.add('tab-panel--active');
}

function showPlaceholder() {
  if (placeholder) placeholder.style.display = 'flex';
  panels.forEach(p => { p.style.display = 'none'; p.innerHTML = ''; });
}

function hidePlaceholder() {
  if (placeholder) placeholder.style.display = 'none';
  panels.forEach(p => { p.style.display = ''; });
}

tabs.forEach(btn => {
  btn.addEventListener('click', async () => {
    const tab = btn.dataset.tab;
    setActiveTab(tab);

    const payload = getPayload();
    if (payload.text.length < 100) {
      showToast('Please paste at least 100 characters of contract text.', 'warn');
      return;
    }

    await runAnalysis(tab, payload);
  });
});

async function runAnalysis(tab, payload) {
  const key = cacheKey(tab, payload);
  if (cache[key]) {
    renderResult(tab, cache[key]);
    return;
  }

  hidePlaceholder();
  const panel = document.getElementById(`tab-${tab}`);
  panel.innerHTML = `<div class="loading-state" role="status" aria-live="polite">
    <div class="spinner" aria-hidden="true"></div>
    <span>Analyzing contract…</span>
  </div>`;

  try {
    const res = await fetch(`${API_BASE}/${tab}`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': API_KEY },
      body:    JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    cache[key] = { tab, data };
    renderResult(tab, { tab, data });

  } catch (err) {
    panel.innerHTML = `<div class="result-error" role="alert">
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20" aria-hidden="true">
        <circle cx="10" cy="10" r="8"/><path d="M10 6v4M10 14v.5"/>
      </svg>
      ${escHtml(err.message || 'Analysis failed. Please try again.')}
    </div>`;
  }
}

/* ── Renderers ─────────────────────────────────────────────── */
let lastResults = {};

function renderResult(tab, { data }) {
  const panel = document.getElementById(`tab-${tab}`);
  switch (tab) {
    case 'summary':        panel.innerHTML = renderSummary(data); break;
    case 'risk-score':     panel.innerHTML = renderRiskScore(data); break;
    case 'key-risks':      panel.innerHTML = renderKeyRisks(data); break;
    case 'missing-clauses':panel.innerHTML = renderMissingClauses(data); break;
    case 'extract-clauses':panel.innerHTML = renderClauseRevisions(data); break;
  }
  lastResults[tab] = data;
  if (downloadBtn) downloadBtn.disabled = false;
}

if (downloadBtn) {
  downloadBtn.addEventListener('click', () => {
    const lines = ['LexAra Contract Analysis Results', '='.repeat(40), ''];
    Object.entries(lastResults).forEach(([tab, data]) => {
      lines.push(`## ${tab.replace(/-/g,' ').toUpperCase()}`);
      lines.push(JSON.stringify(data, null, 2));
      lines.push('');
    });
    lines.push('---');
    lines.push('DISCLAIMER: This analysis is for informational purposes only and does not constitute legal advice.');
    lines.push('Generated by LexAra — https://lexara.tech');
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `lexara-analysis-${Date.now()}.txt`;
    a.click(); URL.revokeObjectURL(url);
  });
}

function renderSummary(d) {
  return `<div class="result-summary">
    <p class="summary-text">${escHtml(d.summary || 'No summary returned.')}</p>
    <div class="result-meta">
      <span class="meta-chip">Type: ${escHtml(d.contract_type || '—')}</span>
      <span class="meta-chip">Jurisdiction: ${escHtml(d.jurisdiction || '—')}</span>
      <span class="meta-chip">Confidence: ${Math.round((d.confidence || 0) * 100)}%</span>
    </div>
    ${resultFooter(d)}
  </div>`;
}

function renderRiskScore(d) {
  const level = (d.risk_level || 'medium').toLowerCase();
  const score = d.overall_risk_score ?? 50;
  const cats  = d.scores_by_category || {};

  const bars = Object.entries(cats).map(([k, v]) => `
    <div class="score-cat-row">
      <div class="score-cat-label">
        <span>${escHtml(k.replace(/_/g,' '))}</span>
        <span class="score-cat-val">${v}</span>
      </div>
      <div class="score-bar-track" role="progressbar" aria-valuenow="${v}" aria-valuemin="0" aria-valuemax="100" aria-label="${k} score: ${v}">
        <div class="score-bar-fill" style="width:${v}%; background:${scoreColor(v)}"></div>
      </div>
    </div>`).join('');

  return `<div>
    <div class="risk-score-display">
      <div class="score-circle score-circle--${level}" aria-label="Overall risk score: ${score} out of 100, level ${level}">
        <span class="score-num">${score}</span>
        <span class="score-label">${level.toUpperCase()}</span>
      </div>
      <div class="score-categories">${bars}</div>
    </div>
    <p class="score-interpretation">${escHtml(d.interpretation || '')}</p>
    ${resultFooter(d)}
  </div>`;
}

function renderKeyRisks(d) {
  const risks = d.key_risks || [];
  if (!risks.length) return `<p style="color:var(--text-muted)">No significant risks identified.</p>`;

  const items = risks.map(r => {
    const sev = (r.severity || 'medium').toLowerCase();
    return `<article class="risk-item risk-item--${sev}">
      <div class="risk-header">
        <span class="risk-badge badge--${sev}">${escHtml(sev)}</span>
        <h3 class="risk-title">${escHtml(r.title || '')}</h3>
        ${r.section ? `<span class="risk-section">${escHtml(r.section)}</span>` : ''}
      </div>
      <p class="risk-desc">${escHtml(r.description || '')}</p>
      ${r.recommendation ? `<p class="risk-rec"><strong>Fix: </strong>${escHtml(r.recommendation)}</p>` : ''}
    </article>`;
  }).join('');

  return `<div class="risks-list">${items}</div>${resultFooter(d)}`;
}

function renderMissingClauses(d) {
  const clauses = d.missing_clauses || [];
  if (!clauses.length) return `<p style="color:var(--text-muted)">No missing clauses detected.</p>`;

  const items = clauses.map(c => {
    const imp = (c.importance || 'medium').toLowerCase();
    return `<div class="clause-item">
      <span class="clause-importance imp--${imp}" aria-label="${imp} importance"></span>
      <div>
        <p class="clause-name">${escHtml(c.clause || '')}</p>
        <p class="clause-rationale">${escHtml(c.rationale || '')}</p>
      </div>
    </div>`;
  }).join('');

  return `<div class="clauses-list">${items}</div>${resultFooter(d)}`;
}

function renderClauseRevisions(d) {
  const clauses = d.clauses || [];
  if (!clauses.length) return `<p style="color:var(--text-muted)">No high/medium risk clauses found requiring revision.</p>`;

  const items = clauses.map(c => {
    const sev = (c.severity || c.risk || 'medium').toLowerCase();
    return `
    <div class="extract-item revision-item">
      <div class="extract-meta" style="margin-bottom:var(--space-2)">
        <span class="extract-type">${escHtml(c.type || 'clause')}</span>
        <span class="risk-badge badge--${sev}" style="font-size:.7rem">${escHtml(sev)}</span>
      </div>
      ${c.original ? `<p class="revision-original"><span class="revision-label">Original:</span> ${escHtml(c.original)}</p>` : ''}
      ${c.revised  ? `<p class="revision-revised"><span class="revision-label">Suggested:</span> ${escHtml(c.revised)}</p>` : ''}
      ${c.rationale ? `<p class="extract-summary" style="margin-top:var(--space-2)">${escHtml(c.rationale)}</p>` : ''}
    </div>`;
  }).join('');

  return `<div class="extract-list">${items}
    <p class="revision-disclaimer">⚖️ These suggested revisions are for informational purposes only and do not constitute legal advice. Consult a qualified legal professional before modifying any contract.</p>
  </div>${resultFooter(d)}`;
}

function renderExtractClauses(d) {
  return renderClauseRevisions(d);
}

function resultFooter(d) {
  const parts = [];
  if (d.tokens_used)        parts.push(`${d.tokens_used} tokens used`);
  if (d.processing_time_ms) parts.push(`${(d.processing_time_ms / 1000).toFixed(1)}s`);
  if (!parts.length)        return '';
  return `<div class="result-footer" aria-label="Analysis metadata">${parts.map(p => `<span>${escHtml(p)}</span>`).join('')}</div>`;
}

/* ── Helpers ───────────────────────────────────────────────── */
function scoreColor(v) {
  if (v >= 75) return 'var(--critical)';
  if (v >= 50) return 'var(--high)';
  if (v >= 25) return 'var(--medium)';
  return 'var(--low)';
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* ── Toast ─────────────────────────────────────────────────── */
function showToast(msg, type = 'info') {
  const t = document.createElement('div');
  t.setAttribute('role', 'alert');
  t.setAttribute('aria-live', 'assertive');
  t.style.cssText = `
    position:fixed; bottom:24px; left:50%; transform:translateX(-50%);
    background:${type === 'warn' ? 'var(--high)' : 'var(--gold)'};
    color:var(--text-inverse); padding:12px 24px; border-radius:8px;
    font-size:.9375rem; font-weight:600; z-index:9999;
    box-shadow:0 4px 20px rgba(0,0,0,.4);
    animation: fadeIn .2s ease;
  `;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

/* ── Stripe Checkout ───────────────────────────────────────── */
document.querySelectorAll('.checkout-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const plan = btn.dataset.plan;

    // Show email modal
    const email = await promptEmail(`Enter your email to subscribe to the ${capitalize(plan)} plan:`);
    if (!email) return;

    const orig = btn.textContent;
    btn.textContent = 'Redirecting to checkout…';
    btn.disabled = true;

    try {
      const res = await fetch(`${API_BASE}/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': API_KEY },
        body: JSON.stringify({ plan_id: plan, email }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Checkout failed');
      }

      const data = await res.json();
      window.location.href = data.checkout_url;

    } catch (err) {
      showToast(err.message || 'Could not start checkout. Please try again.', 'warn');
      btn.textContent = orig;
      btn.disabled = false;
    }
  });
});

function promptEmail(message) {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.style.cssText = `position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;`;
    overlay.innerHTML = `
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:32px;max-width:420px;width:90%;box-shadow:var(--shadow-lg)">
        <h3 style="font-family:var(--font-display);font-size:1.25rem;color:var(--text-primary);margin-bottom:8px">Subscribe to LexAra</h3>
        <p style="font-size:.9375rem;color:var(--text-secondary);margin-bottom:20px">${escHtml(message)}</p>
        <label for="modal-email" style="font-size:.875rem;color:var(--text-secondary);display:block;margin-bottom:6px">Email address</label>
        <input id="modal-email" type="email" autocomplete="email" placeholder="your@email.com" style="width:100%;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius);color:var(--text-primary);font-size:.9375rem;padding:10px 14px;margin-bottom:16px;box-sizing:border-box"/>
        <div style="display:flex;gap:10px">
          <button id="modal-confirm" class="btn btn-gold" style="flex:1">Continue to Checkout</button>
          <button id="modal-cancel" class="btn btn-ghost">Cancel</button>
        </div>
        <p style="font-size:.75rem;color:var(--text-muted);margin-top:12px">You'll be redirected to Stripe's secure checkout. All prices in CAD.</p>
      </div>`;
    document.body.appendChild(overlay);
    const input = overlay.querySelector('#modal-email');
    input.focus();
    overlay.querySelector('#modal-confirm').addEventListener('click', () => {
      const val = input.value.trim();
      if (!val || !val.includes('@')) { input.style.borderColor='var(--critical)'; return; }
      document.body.removeChild(overlay);
      resolve(val);
    });
    overlay.querySelector('#modal-cancel').addEventListener('click', () => { document.body.removeChild(overlay); resolve(null); });
    input.addEventListener('keydown', e => { if (e.key === 'Enter') overlay.querySelector('#modal-confirm').click(); if (e.key === 'Escape') overlay.querySelector('#modal-cancel').click(); });
  });
}

function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

/* ── Handle checkout return ────────────────────────────────── */
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get('checkout') === 'success') {
  showToast('🎉 Subscription activated! Welcome to LexAra.');
  window.history.replaceState({}, '', '/');
} else if (urlParams.get('checkout') === 'cancelled') {
  showToast('Checkout cancelled — no charge was made.', 'warn');
  window.history.replaceState({}, '', '/');
}

/* ── CTA Form ──────────────────────────────────────────────── */
const ctaForm = document.querySelector('.cta-form');
if (ctaForm) {
  ctaForm.addEventListener('submit', e => {
    e.preventDefault();
    const email = document.getElementById('cta-email');
    if (!email.value || !email.value.includes('@')) {
      showToast('Please enter a valid email address.', 'warn');
      email.focus();
      return;
    }
    showToast(`Welcome! We'll be in touch at ${email.value} 🎉`);
    email.value = '';
  });
}

/* ── File Upload ───────────────────────────────────────────── */
const uploadZone = document.getElementById('upload-zone');
const fileInput  = document.getElementById('file-input');

if (uploadZone && fileInput) {
  // Drag-over highlight
  uploadZone.addEventListener('dragover', e => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
  });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFileUpload(file);
  });

  fileInput.addEventListener('change', () => {
    const file = fileInput.files?.[0];
    if (file) handleFileUpload(file);
  });

  // Keyboard accessibility
  uploadZone.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
  });
}

async function handleFileUpload(file) {
  const label = uploadZone.querySelector('.upload-label');
  const originalLabel = label.innerHTML;

  // Show loading state
  label.innerHTML = `<span style="color:var(--gold)">Extracting text from ${escHtml(file.name)}…</span>`;
  uploadZone.classList.remove('upload-success');

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      headers: { 'Authorization': API_KEY },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed (HTTP ${res.status})`);
    }

    const data = await res.json();
    textarea.value = data.text;
    uploadZone.classList.add('upload-success');
    label.innerHTML = `<strong style="color:var(--low)">✓ ${escHtml(file.name)}</strong> — ${data.word_count.toLocaleString()} words extracted`;
    showToast(`File loaded — ${data.word_count.toLocaleString()} words ready to analyze`);

  } catch (err) {
    label.innerHTML = originalLabel;
    showToast(err.message || 'Upload failed. Please try again.', 'warn');
  }

  // Reset input so same file can be re-uploaded
  fileInput.value = '';
}

/* ── Sample contract for quick testing ───────────────────── */
const SAMPLE = `This Service Agreement is entered into as of January 1, 2026 between LexCorp Inc. ("Service Provider") and Maple Ventures Ltd. ("Client").

1. SERVICES. Service Provider agrees to provide software development services as requested by Client from time to time.

2. PAYMENT. Client agrees to pay $5,000 per month, due on the 1st of each month.

3. TERM & TERMINATION. Either party may terminate this agreement with 30 days written notice.

4. LIABILITY. Service Provider shall not be liable for any indirect, incidental, or consequential damages arising out of this agreement.

5. INTELLECTUAL PROPERTY. All intellectual property created under this agreement belongs exclusively to Service Provider.

6. GOVERNING LAW. This agreement shall be governed by the laws of Ontario, Canada.`;

// Add sample button hint to textarea
if (textarea) {
  const hint = document.createElement('button');
  hint.type = 'button';
  hint.className = 'btn btn-ghost';
  hint.style.cssText = 'font-size:.8125rem; padding:6px 12px; margin-top:8px;';
  hint.textContent = 'Load sample contract';
  hint.addEventListener('click', () => {
    textarea.value = SAMPLE;
    textarea.dispatchEvent(new Event('input'));
    showToast('Sample contract loaded. Click a tab to analyze.');
  });
  textarea.parentNode.insertBefore(hint, textarea.nextSibling.nextSibling);
}

/* ============================================================
   Auth — show/hide demo based on token; update nav state
   ============================================================ */

const GATE_API = 'https://api.lexara.tech/v1';

function switchAuthTab(tab) {
  // legacy — kept for any inline calls
}

function doGateLogout() {
  localStorage.removeItem('pai_token');
  localStorage.removeItem('pai_role');
  localStorage.removeItem('pai_user');
  showGuestState();
}

function showGuestState() {
  const demoContent  = document.getElementById('demo-content');
  const demoGate     = document.getElementById('demo-auth-gate');
  const navUser      = document.getElementById('nav-user');
  const navSignout   = document.getElementById('nav-signout');
  const navCtaBtn    = document.getElementById('nav-cta-btn');
  if (demoContent) demoContent.style.display = 'none';
  if (demoGate)    demoGate.style.display = '';
  if (navUser)     navUser.style.display = 'none';
  if (navSignout)  navSignout.style.display = 'none';
  if (navCtaBtn)   navCtaBtn.style.display = '';
}

function showAuthenticatedState(username, role) {
  const demoContent  = document.getElementById('demo-content');
  const demoGate     = document.getElementById('demo-auth-gate');
  const navUser      = document.getElementById('nav-user');
  const navSignout   = document.getElementById('nav-signout');
  const navCtaBtn    = document.getElementById('nav-cta-btn');
  if (demoContent) demoContent.style.display = '';
  if (demoGate)    demoGate.style.display = 'none';
  if (navUser)   { navUser.textContent = `${username} · ${role}`; navUser.style.display = ''; }
  if (navSignout)  navSignout.style.display = '';
  if (navCtaBtn)   navCtaBtn.style.display = 'none';
}

// On every page load — check token
document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('pai_token');
  const user  = localStorage.getItem('pai_user');
  const role  = localStorage.getItem('pai_role');
  if (token && user) {
    showAuthenticatedState(user, role);
  } else {
    showGuestState();
  }
  // Enter key in old gate forms (noop now but harmless)
  ['gate-username','gate-password'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('keydown', e => { if (e.key === 'Enter') {} });
  });
});
