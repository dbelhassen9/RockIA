/* ═══════════════════════════════════════════════════
   RockAI — Agenda page logic
   ═══════════════════════════════════════════════════ */

let _allMatches   = [];
let _activeFilter = 'all';

async function loadMatches() {
  const container = document.getElementById('matches-container');
  const btn       = document.getElementById('refresh-btn');
  container.innerHTML = loadingHTML('Chargement des matchs depuis toutes les ligues...');
  if (btn) btn.disabled = true;

  try {
    const data = await apiCall('/matches');
    _allMatches = data.matches || [];

    const sub = document.getElementById('agenda-sub');
    if (sub) sub.textContent = `// ${_allMatches.length} matchs · mode ${data.mode === 'live' ? '🔴 LIVE' : '🟡 démo'} · actualisé à ${new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`;

    renderMatchList(_activeFilter);
    initFilters();
  } catch(e) {
    container.innerHTML = errorHTML(e.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function initFilters() {
  document.querySelectorAll('#filter-bar .filter-chip').forEach(chip => {
    chip.addEventListener('click', function() {
      document.querySelectorAll('#filter-bar .filter-chip').forEach(c => c.classList.remove('active'));
      this.classList.add('active');
      _activeFilter = this.dataset.filter || 'all';
      renderMatchList(_activeFilter);
    });
  });
}

function renderMatchList(filter) {
  const container = document.getElementById('matches-container');
  let matches = _allMatches;

  if (filter === 'value') {
    matches = matches.filter(m => m.best_bet && m.best_bet !== 'none' && (m.ev_home || 0) > 0.03);
  } else if (filter && filter !== 'all') {
    matches = matches.filter(m => getSportCategory(m.sport_key) === filter);
  }

  if (!matches.length) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">${filter === 'value' ? '🔥' : '📭'}</div><p>${filter === 'value' ? 'Aucun value bet détecté pour le moment.<br>L\'IA surveille en continu.' : 'Aucun match pour ce filtre.'}</p></div>`;
    return;
  }

  // Groupe par date
  const byDate = {};
  matches.forEach(m => {
    const d = new Date(m.commence_time);
    const key = d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
    if (!byDate[key]) byDate[key] = [];
    byDate[key].push(m);
  });

  container.innerHTML = '';

  Object.entries(byDate).forEach(([date, dayMatches]) => {
    // Date label
    const label = document.createElement('div');
    label.className = 'date-label';
    label.textContent = date.charAt(0).toUpperCase() + date.slice(1);
    container.appendChild(label);

    // Group by sport within the day
    const bySport = {};
    dayMatches.forEach(m => {
      const cat = getSportCategory(m.sport_key);
      if (!bySport[cat]) bySport[cat] = [];
      bySport[cat].push(m);
    });

    Object.entries(bySport).forEach(([cat, sportMatches]) => {
      if (Object.keys(bySport).length > 1) {
        const sportLabel = document.createElement('div');
        sportLabel.className = 'sport-section-label';
        sportLabel.textContent = `${getSportIcon(sportMatches[0].sport_key)} ${cat}`;
        container.appendChild(sportLabel);
      }

      const listEl = document.createElement('div');
      listEl.className = 'matches-list';
      sportMatches.forEach(m => listEl.appendChild(buildMatchCard(m)));
      container.appendChild(listEl);
    });
  });
}

function buildMatchCard(m) {
  const ev      = m.ev_home || 0;
  const isValue = m.best_bet && m.best_bet !== 'none' && ev > 0.03;
  const time    = new Date(m.commence_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  const evSign  = ev > 0 ? '+' : '';
  const hasDraw = m.odds_draw != null;

  const card = document.createElement('div');
  card.className = 'match-card' + (isValue ? ' value' : '');

  card.innerHTML = `
    <div class="match-meta">
      <div class="match-sport-cat">${getSportIcon(m.sport_key)} ${getSportCategory(m.sport_key)}</div>
      <div class="match-league">${m.league_label || ''}</div>
      <div class="match-time">${time}</div>
    </div>
    <div class="match-center">
      <div class="team">
        <div class="team-icon">${teamEmoji(m.team_home, m.sport_key)}</div>
        <div class="team-name">${m.team_home}</div>
      </div>
      <div class="vs-block">
        <div class="vs-text">VS</div>
        <div class="match-odds-row">
          <div class="odd-pill">${m.odds_home || '?'}</div>
          ${hasDraw ? `<div class="odd-pill">${m.odds_draw}</div>` : ''}
          <div class="odd-pill">${m.odds_away || '?'}</div>
        </div>
      </div>
      <div class="team">
        <div class="team-icon">${teamEmoji(m.team_away, m.sport_key)}</div>
        <div class="team-name">${m.team_away}</div>
      </div>
    </div>
    <div class="match-right">
      <div class="value-badge ${evClass(ev)}">${evLabel(ev, m.has_analysis)}</div>
      ${m.has_analysis
        ? `<div class="ev-value${ev < 0 ? ' neg' : ''}">${evSign}${(ev * 100).toFixed(1)}%</div><div class="ev-label">Expected Value</div>`
        : `<div class="ev-label" style="margin-top:.5rem;">Clique pour analyser</div>`}
    </div>`;

  card.addEventListener('click', () => openMatch(m));
  return card;
}

function openMatch(m) {
  sessionStorage.setItem('pending_match', JSON.stringify(m));
  window.location.href = `analyse.html?id=${encodeURIComponent(m.match_id)}`;
}
