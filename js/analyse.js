/* ═══════════════════════════════════════════════════
   RockAI — Analyse page logic
   ═══════════════════════════════════════════════════ */

let _currentMatch    = null;
let _currentAnalysis = null;

async function initAnalysis() {
  const params  = new URLSearchParams(window.location.search);
  const matchId = params.get('id');
  const cached  = JSON.parse(sessionStorage.getItem('pending_match') || 'null');

  if (!matchId) { window.location.href = 'agenda.html'; return; }

  // Pre-fill from cached data immediately
  if (cached && cached.match_id === matchId) {
    _currentMatch = cached;
    prefillFromMatch(cached);
  } else {
    document.getElementById('match-title').textContent = 'Chargement...';
  }

  // Then trigger AI analysis
  await runAnalysis(matchId);
}

function prefillFromMatch(m) {
  const time = new Date(m.commence_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  const date = new Date(m.commence_time).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
  const hasDraw = m.odds_draw != null;

  document.getElementById('match-title').textContent   = `${m.team_home} vs ${m.team_away}`;
  document.getElementById('match-subtitle').textContent = `${getSportIcon(m.sport_key)} ${getSportCategory(m.sport_key)} — ${m.league_label || ''} · ${date}`;
  document.getElementById('match-time').textContent    = time;

  document.getElementById('icon-home').textContent = teamEmoji(m.team_home, m.sport_key);
  document.getElementById('icon-away').textContent = teamEmoji(m.team_away, m.sport_key);
  document.getElementById('name-home').textContent = m.team_home;
  document.getElementById('name-away').textContent = m.team_away;

  document.getElementById('odd-home').querySelector('.odd-val').textContent = m.odds_home || '?';
  document.getElementById('odd-away').querySelector('.odd-val').textContent = m.odds_away || '?';
  document.getElementById('odd-home-lbl').textContent = '1 — ' + (m.team_home || '').split(' ')[0].slice(0, 4).toUpperCase();
  document.getElementById('odd-away-lbl').textContent = '2 — ' + (m.team_away || '').split(' ')[0].slice(0, 4).toUpperCase();

  const drawBlock = document.getElementById('odd-draw');
  if (hasDraw) {
    drawBlock.style.display = '';
    drawBlock.querySelector('.odd-val').textContent = m.odds_draw;
  } else {
    drawBlock.style.display = 'none';
    document.getElementById('proba-draw-row').style.display = 'none';
    document.getElementById('proba-bk-draw-row').style.display = 'none';
  }

  if (m.best_bookmaker) {
    document.getElementById('bookmaker-label').textContent = 'Meilleure cote : ' + m.best_bookmaker;
  }

  // Proba labels
  const shortHome = m.team_home.split(' ')[0];
  const shortAway = m.team_away.split(' ')[0];
  ['pl-home','pl-bk-home'].forEach(id => { const el = document.getElementById(id); if(el) el.textContent = shortHome; });
  ['pl-away','pl-bk-away'].forEach(id => { const el = document.getElementById(id); if(el) el.textContent = shortAway; });
}

async function runAnalysis(matchId) {
  const aiThinking = document.getElementById('ai-thinking');
  const aiText     = document.getElementById('ai-text');
  const verdictBet = document.getElementById('verdict-bet');

  if (aiThinking) aiThinking.style.display = 'flex';
  if (aiText)     aiText.innerHTML = '';
  if (verdictBet) verdictBet.textContent = 'Analyse IA en cours...';

  try {
    const a = await apiCall(`/matches/${matchId}/analyze`, { method: 'POST' });
    _currentAnalysis = a;
    populateAnalysis(a);
  } catch(e) {
    if (aiThinking) aiThinking.style.display = 'none';
    if (aiText)     aiText.innerHTML = `<span style="color:var(--red)">❌ ${e.message}</span>`;
    if (verdictBet) verdictBet.textContent = 'Erreur';
    showToast('Erreur analyse : ' + e.message, 'error');
  }
}

function populateAnalysis(a) {
  // Prefill match info in case we didn't have cached data
  document.getElementById('match-title').textContent   = `${a.team_home} vs ${a.team_away}`;
  const date = new Date(a.commence_time).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
  document.getElementById('match-subtitle').textContent = `${a.league || ''} · ${date}`;
  document.getElementById('match-time').textContent    = new Date(a.commence_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  document.getElementById('name-home').textContent     = a.team_home;
  document.getElementById('name-away').textContent     = a.team_away;

  // Cotes
  const hasDraw = a.odds?.draw != null;
  const bestBet = a.best_bet || 'none';

  const oddHome = document.getElementById('odd-home');
  const oddDraw = document.getElementById('odd-draw');
  const oddAway = document.getElementById('odd-away');

  oddHome.querySelector('.odd-val').textContent = a.odds?.home || '?';
  oddAway.querySelector('.odd-val').textContent = a.odds?.away || '?';
  oddHome.className = 'odd-block' + (bestBet === 'home' ? ' best' : '');
  oddAway.className = 'odd-block' + (bestBet === 'away' ? ' best' : '');

  if (hasDraw) {
    oddDraw.style.display = '';
    oddDraw.querySelector('.odd-val').textContent = a.odds.draw;
    oddDraw.className = 'odd-block' + (bestBet === 'draw' ? ' best' : '');
  } else {
    oddDraw.style.display = 'none';
    document.getElementById('proba-draw-row').style.display    = 'none';
    document.getElementById('proba-bk-draw-row').style.display = 'none';
  }

  if (a.odds?.bookmaker) document.getElementById('bookmaker-label').textContent = 'Meilleure cote : ' + a.odds.bookmaker;

  // Probas IA
  const ph = (a.ai_probabilities?.home || 0) * 100;
  const pd = (a.ai_probabilities?.draw || 0) * 100;
  const pa = (a.ai_probabilities?.away || 0) * 100;

  document.getElementById('pf-home').style.width = `${ph.toFixed(0)}%`;
  document.getElementById('pf-draw').style.width = `${pd.toFixed(0)}%`;
  document.getElementById('pf-away').style.width = `${pa.toFixed(0)}%`;
  document.getElementById('pp-home').textContent  = `${ph.toFixed(0)}%`;
  document.getElementById('pp-draw').textContent  = `${pd.toFixed(0)}%`;
  document.getElementById('pp-away').textContent  = `${pa.toFixed(0)}%`;

  // Proba labels
  const shortHome = a.team_home.split(' ')[0];
  const shortAway = a.team_away.split(' ')[0];
  ['pl-home','pl-bk-home'].forEach(id => { const el = document.getElementById(id); if(el) el.textContent = shortHome; });
  ['pl-away','pl-bk-away'].forEach(id => { const el = document.getElementById(id); if(el) el.textContent = shortAway; });

  // Probas bookmaker (implicite depuis les cotes)
  if (a.odds?.home) {
    const oh = a.odds.home, od = a.odds.draw || 999, oa = a.odds.away;
    const total = 1/oh + (hasDraw ? 1/od : 0) + 1/oa;
    const bh = (1/oh/total*100).toFixed(0);
    const bd = hasDraw ? (1/od/total*100).toFixed(0) : 0;
    const ba = (1/oa/total*100).toFixed(0);
    document.getElementById('pf-bk-home').style.width = `${bh}%`;
    document.getElementById('pf-bk-draw').style.width = `${bd}%`;
    document.getElementById('pf-bk-away').style.width = `${ba}%`;
    document.getElementById('pp-bk-home').textContent  = `${bh}%`;
    document.getElementById('pp-bk-draw').textContent  = hasDraw ? `${bd}%` : '';
    document.getElementById('pp-bk-away').textContent  = `${ba}%`;
  }

  // Stats comparées (pour le football)
  const stats = a.stats || {};
  if (stats.home && stats.away && stats.home.played) {
    const sc = document.getElementById('stats-compare');
    if (sc) {
      sc.style.display = '';
      fillStatCompare(1, 'Victoires', stats.home.wins, stats.away.wins, stats.home.played, stats.away.played);
      fillStatCompare(2, 'Buts/match', parseFloat(stats.home.goals_for)||0, parseFloat(stats.away.goals_for)||0, 3, 3);
      fillStatCompare(3, 'Clean sheets', stats.home.clean_sheets, stats.away.clean_sheets, stats.home.played, stats.away.played);
    }
  }

  // Forme
  const formHome = document.getElementById('form-home');
  const formAway = document.getElementById('form-away');
  if (formHome && a.form?.home?.length) {
    formHome.innerHTML = a.form.home.slice(-5).map(f => `<div class="form-dot ${f==='W'?'w':f==='D'?'d':'l'}">${f}</div>`).join('');
  }
  if (formAway && a.form?.away?.length) {
    formAway.innerHTML = a.form.away.slice(-5).map(f => `<div class="form-dot ${f==='W'?'w':f==='D'?'d':'l'}">${f}</div>`).join('');
  }

  // Verdict
  const evMap = { home: a.expected_values?.home||0, draw: a.expected_values?.draw||0, away: a.expected_values?.away||0 };
  const bestEv = evMap[bestBet] || 0;
  const betLabels = {
    home: `✓ Parier ${a.team_home}`, draw: '✓ Parier Nul',
    away: `✓ Parier ${a.team_away}`, none: '✗ Pas de value détecté'
  };
  document.getElementById('verdict-bet').textContent = betLabels[bestBet] || '—';
  document.getElementById('verdict-sub').innerHTML   = `Confiance : ${((a.confidence||0)*100).toFixed(0)}% · Bookmaker : ${a.odds?.bookmaker || '—'}`;
  document.getElementById('ev-big').textContent      = `${bestEv > 0 ? '+' : ''}${(bestEv*100).toFixed(1)}%`;
  document.getElementById('ev-big').style.color      = bestEv > 0 ? 'var(--accent)' : 'var(--red)';

  const kelly      = a.kelly_fraction || 0;
  const bestOdds   = (a.odds || {})[bestBet] || 1;
  const suggested  = (kelly * 100).toFixed(2);
  const gain       = (kelly * 100 * (bestOdds - 1)).toFixed(2);
  document.getElementById('kelly-pct').textContent   = `${(kelly*100).toFixed(1)}%`;
  document.getElementById('kelly-stake').textContent = `${suggested}€`;
  document.getElementById('kelly-gain').textContent  = `+${gain}€`;

  // Value badge header
  const badge = document.getElementById('value-badge-header');
  if (badge) {
    if (bestBet !== 'none' && bestEv > 0) {
      badge.className = 'value-badge hot'; badge.textContent = '🔥 Value Bet Détecté';
    } else {
      badge.className = 'value-badge neutral'; badge.textContent = '— Pas de value';
    }
  }

  // Analyse IA texte
  const aiThinking = document.getElementById('ai-thinking');
  const aiText     = document.getElementById('ai-text');
  const analysisTime = document.getElementById('analysis-time');
  if (aiThinking) aiThinking.style.display = 'none';
  if (analysisTime) analysisTime.textContent = `// généré à ${new Date().toLocaleTimeString('fr-FR', {hour:'2-digit',minute:'2-digit'})}`;
  if (aiText && a.analysis) {
    aiText.innerHTML = a.analysis
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  }
}

function fillStatCompare(idx, label, leftVal, rightVal, maxLeft, maxRight) {
  document.getElementById(`sc-label-${idx}`).textContent = label;
  document.getElementById(`sc-left-${idx}`).textContent  = leftVal;
  document.getElementById(`sc-right-${idx}`).textContent = rightVal;
  const total = (parseFloat(maxLeft)||1) + (parseFloat(maxRight)||1);
  document.getElementById(`sb-left-${idx}`).style.width  = `${Math.min(45,(parseFloat(leftVal)||0)/total*100)}%`;
  document.getElementById(`sb-right-${idx}`).style.width = `${Math.min(45,(parseFloat(rightVal)||0)/total*100)}%`;
}

async function saveBet() {
  if (!_currentAnalysis) { showToast('Lance d\'abord une analyse', 'error'); return; }
  const a = _currentAnalysis;
  if (!a.best_bet || a.best_bet === 'none') { showToast('Aucun value bet à enregistrer', 'error'); return; }

  const settings = JSON.parse(localStorage.getItem('rockai_settings') || '{}');
  const bankroll = parseFloat(settings.bankroll) || 100;
  const stake    = parseFloat((a.kelly_fraction * bankroll).toFixed(2));

  const btn = document.getElementById('save-bet-btn');
  btn.disabled = true; btn.textContent = 'Enregistrement...';
  try {
    await apiCall('/bets', {
      method: 'POST',
      body: JSON.stringify({ match_id: a.match_id, bet_type: a.best_bet, stake })
    });
    showToast(`Pari enregistré ! Mise : ${stake}€`, 'success');
    btn.textContent = '✓ Pari enregistré';
  } catch(e) {
    showToast('Erreur : ' + e.message, 'error');
    btn.disabled = false; btn.textContent = 'Enregistrer ce pari →';
  }
}
