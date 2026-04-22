/* ═══════════════════════════════════════════════════
   RockAI — Shared JS (auth, API, utils)
   ═══════════════════════════════════════════════════ */

const API_BASE = 'http://localhost:8000';

// ─── Auth ─────────────────────────────────────────────────────────
function getToken()  { return localStorage.getItem('rockai_token'); }
function setToken(t) { localStorage.setItem('rockai_token', t); }
function clearToken(){ localStorage.removeItem('rockai_token'); localStorage.removeItem('rockai_user'); }

function authHeaders() {
  return { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` };
}

async function apiCall(path, options = {}) {
  const r = await fetch(API_BASE + path, { headers: authHeaders(), ...options });
  if (r.status === 401) { clearToken(); window.location.href = 'index.html'; throw new Error('Session expirée'); }
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || 'Erreur API');
  return data;
}

function requireAuth() {
  if (!getToken()) { window.location.href = 'index.html'; return false; }
  return true;
}

// ─── Toast ────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const t = document.createElement('div');
  const colors = { info: '#00d4dc', error: '#ff4757', success: '#00e87a' };
  t.style.cssText = `position:fixed;bottom:2rem;right:2rem;z-index:99999;padding:.85rem 1.4rem;
    background:#0d1318;border:1px solid ${colors[type]||colors.info};border-radius:10px;
    color:#e8edf2;font-family:'DM Mono',monospace;font-size:.8rem;
    box-shadow:0 0 30px rgba(0,0,0,.5);animation:fadeIn .3s ease;max-width:320px;`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ─── Nav user ─────────────────────────────────────────────────────
function updateNavUser(user) {
  document.querySelectorAll('.nav-user-name').forEach(el => { el.textContent = user.full_name; });
  document.querySelectorAll('.avatar').forEach(el => {
    el.textContent = user.full_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  });
  document.querySelectorAll('.plan-badge').forEach(el => {
    el.textContent = user.plan === 'pro' ? '⭐ Pro' : `🎯 ${user.credits} crédits`;
  });
}

async function initPage() {
  if (!requireAuth()) return null;
  const cached = JSON.parse(localStorage.getItem('rockai_user') || 'null');
  if (cached) updateNavUser(cached);
  try {
    const user = await apiCall('/user/me');
    localStorage.setItem('rockai_user', JSON.stringify(user));
    updateNavUser(user);
    return user;
  } catch(e) { return cached; }
}

// ─── Sport / Team helpers ─────────────────────────────────────────
const SPORT_CATEGORIES = {
  soccer:            'Football',
  basketball:        'Basketball',
  americanfootball:  'Football Américain',
  icehockey:         'Hockey sur glace',
  baseball:          'Baseball',
  mma:               'MMA / UFC',
  boxing:            'Boxe',
  rugbyleague:       'Rugby',
  rugbyunion:        'Rugby',
  tennis:            'Tennis',
  cricket:           'Cricket',
};

function getSportCategory(sport_key) {
  const prefix = sport_key.split('_')[0];
  return SPORT_CATEGORIES[prefix] || 'Sport';
}

function getSportIcon(sport_key) {
  const icons = {
    soccer: '⚽', basketball: '🏀', americanfootball: '🏈',
    icehockey: '🏒', baseball: '⚾', mma: '🥊', boxing: '🥊',
    rugbyleague: '🏉', rugbyunion: '🏉', tennis: '🎾', cricket: '🏏',
  };
  return icons[sport_key.split('_')[0]] || '🏆';
}

function teamEmoji(name, sport_key = '') {
  const prefix = sport_key.split('_')[0];
  if (prefix === 'basketball') {
    const nba = { 'Lakers':'🟡','Warriors':'🔵','Celtics':'🟢','Heat':'🔴','Bulls':'🔴',
      'Knicks':'🟠','Nets':'⚫','Bucks':'🟢','Suns':'🟣','Nuggets':'🔵',
      'Maverick':'🔵','76ers':'🔵','Raptors':'🔴','Clippers':'🔵' };
    for (const [k,v] of Object.entries(nba)) { if (name.includes(k)) return v; }
    return '🏀';
  }
  if (prefix === 'americanfootball') return '🏈';
  if (prefix === 'icehockey')        return '🏒';
  if (prefix === 'baseball')         return '⚾';
  if (prefix === 'mma' || prefix === 'boxing') return '🥊';
  if (prefix === 'rugbyleague' || prefix === 'rugbyunion') return '🏉';
  if (prefix === 'tennis')   return '🎾';
  if (prefix === 'cricket')  return '🏏';
  // Soccer
  const map = {
    'Arsenal':'🔴','Chelsea':'🔵','Liverpool':'🔴','Man City':'🔵','Man United':'🔴',
    'Tottenham':'⚪','PSG':'🔵','Lyon':'🔴','Marseille':'🔵','Monaco':'🔴',
    'Bayern':'🔴','Dortmund':'🟡','Real Madrid':'⚪','Barcelona':'🔵','Atletico':'🔴',
    'Inter':'⚫','Juventus':'⚪','Napoli':'🔵','Milan':'🔴','Ajax':'🔴',
    'Benfica':'🔴','Porto':'🔵','Celtic':'🟢','Rangers':'🔵',
  };
  for (const [k,v] of Object.entries(map)) { if (name.includes(k)) return v; }
  return '⚽';
}

// ─── EV / value helpers ───────────────────────────────────────────
function evClass(ev) {
  if (ev > 0.03) return 'hot';
  if (ev < -0.03) return 'risk';
  return 'neutral';
}
function evLabel(ev, hasAnalysis) {
  if (!hasAnalysis) return 'Non analysé';
  if (ev > 0.03) return 'Value bet ↑';
  if (ev < -0.03) return 'Risqué';
  return 'Neutre';
}

// ─── Loading helper ───────────────────────────────────────────────
function loadingHTML(msg = 'Chargement...') {
  return `<div class="loading"><div class="loading-dots"><span></span><span></span><span></span></div> ${msg}</div>`;
}
function errorHTML(msg) {
  return `<div class="empty-state"><div class="empty-icon">❌</div><p>${msg}</p></div>`;
}
