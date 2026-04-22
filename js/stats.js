/* ═══════════════════════════════════════════════════
   RockAI — Stats page logic
   ═══════════════════════════════════════════════════ */

async function loadStats() {
  try {
    const [s, bets] = await Promise.all([
      apiCall('/stats'),
      apiCall('/bets?limit=20')
    ]);
    renderKPIs(s);
    renderROIChart(s.monthly || []);
    renderLeagueDist(s.by_league || []);
    renderBetsTable(bets.bets || []);
  } catch(e) {
    showToast('Erreur stats : ' + e.message, 'error');
    document.getElementById('stats-sub').textContent = '// Erreur de chargement';
  }
}

function renderKPIs(s) {
  document.getElementById('stats-sub').textContent =
    `// ${s.total_bets} paris · depuis le début`;

  const roi    = s.roi    || 0;
  const wr     = s.win_rate || 0;
  const profit = s.total_profit || 0;

  document.getElementById('kpi-roi').textContent     = `${roi >= 0 ? '+' : ''}${roi}%`;
  document.getElementById('kpi-winrate').textContent  = `${wr}%`;
  document.getElementById('kpi-profit').textContent   = `${profit >= 0 ? '+' : ''}${profit}€`;
  document.getElementById('kpi-bets').textContent     = s.total_bets || 0;

  document.getElementById('kpi-roi-trend').innerHTML    = `EV moyen <span class="${roi>=0?'up':'down'}">${roi>=0?'↑':'↓'} ${roi}%</span>`;
  document.getElementById('kpi-winrate-trend').innerHTML = `${s.won||0} <span class="up">✓</span> · ${s.lost||0} <span class="down">✗</span>`;
  document.getElementById('kpi-profit-trend').innerHTML  = `Misé : ${s.total_staked||0}€`;
  document.getElementById('kpi-bets-detail').innerHTML   = `${s.won||0} <span class="up">✓</span> · ${s.lost||0} <span class="down">✗</span> · ${s.pending||0} en cours`;
}

function renderROIChart(monthly) {
  const chart = document.getElementById('roi-chart');
  if (!monthly.length) {
    chart.innerHTML = '<div class="empty-state" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;"><p>Aucune donnée mensuelle</p></div>';
    chart.style.position = 'relative';
    return;
  }

  const profits = monthly.map(m => m.profit || 0);
  const maxAbs  = Math.max(...profits.map(Math.abs), 1);
  const chartH  = 140;

  chart.innerHTML = '<div class="chart-zero"></div>';

  monthly.forEach(m => {
    const p    = m.profit || 0;
    const pct  = Math.abs(p) / maxAbs * 100;
    const isPos = p >= 0;
    const mon  = m.month?.slice(5) || '—';

    const wrap = document.createElement('div');
    wrap.className = 'roi-bar-wrap';
    if (!isPos) {
      wrap.style.justifyContent = 'flex-start';
      wrap.style.alignItems = 'center';
      wrap.style.flexDirection = 'column-reverse';
      wrap.style.paddingBottom = '22px';
    }

    const bar = document.createElement('div');
    bar.className = 'roi-bar ' + (isPos ? 'pos' : 'neg');
    bar.style.height = `${Math.max(2, pct * 0.6)}%`;
    bar.title = `${isPos?'+':''}${p.toFixed(0)}€`;

    const label = document.createElement('div');
    label.className = 'roi-month';
    label.textContent = mon;

    wrap.appendChild(bar);
    wrap.appendChild(label);
    chart.appendChild(wrap);
  });
}

function renderLeagueDist(byLeague) {
  const container = document.getElementById('sport-dist');
  if (!byLeague.length) {
    container.innerHTML = '<div class="empty-state"><p>Aucun pari enregistré</p></div>';
    return;
  }

  const colors = ['var(--accent)','#00b8ff','var(--gold)','#ff8c42','#a855f7','var(--red)','#22d3ee'];
  const maxBets = Math.max(...byLeague.map(l => l.bets), 1);

  container.innerHTML = byLeague.slice(0, 8).map((l, i) => {
    const wr  = l.bets > 0 ? Math.round(l.wins / l.bets * 100) : 0;
    const pct = Math.round(l.bets / maxBets * 100);
    const col = colors[i % colors.length];
    return `
      <div class="dist-row">
        <div class="dist-label" title="${l.league}">${l.league.replace(/🇫🇷|🏴󠁧󠁢󠁥󠁮󠁧󠁿|🇪🇸|🇩🇪|🇮🇹|🏆|⚽|🏀|🏈|🏒|⚾|🥊|🏉|🎾|🇺🇸|🇳🇱|🇵🇹/g,'').trim().slice(0,15)}</div>
        <div class="dist-bar-bg"><div class="dist-bar-fill" style="width:${wr}%;background:${col};"></div></div>
        <div class="dist-pct" style="color:${col}">${wr}%</div>
      </div>`;
  }).join('');
}

function renderBetsTable(bets) {
  const wrap = document.getElementById('bets-table-wrap');
  if (!bets.length) {
    wrap.innerHTML = `<div class="empty-state"><div class="empty-icon">📭</div><p>Aucun pari enregistré pour l'instant.<br>Analyse un match et enregistre ton premier pari.</p></div>`;
    return;
  }

  wrap.innerHTML = `
    <table class="bet-table">
      <thead>
        <tr>
          <th>Match</th>
          <th>Pari</th>
          <th>Cote</th>
          <th>EV</th>
          <th>Mise</th>
          <th>Résultat</th>
          <th>P&L</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        ${bets.slice(0, 20).map(b => {
          const betStr = b.bet_type === 'home' ? '1 ' + b.team_home :
                         b.bet_type === 'away' ? '2 ' + b.team_away : 'X Nul';
          const rClass = b.result === 'won' ? 'win' : b.result === 'lost' ? 'loss' : 'pending';
          const rLabel = b.result === 'won' ? 'Gagné' : b.result === 'lost' ? 'Perdu' : 'En cours';
          const ev     = b.expected_value || 0;
          return `<tr>
            <td>
              <div class="bet-team">${b.team_home} vs ${b.team_away}</div>
              <div class="bet-league-tag">${b.league} · ${new Date(b.placed_at).toLocaleDateString('fr-FR')}</div>
            </td>
            <td style="font-family:var(--font-mono);font-size:.78rem;">${betStr}</td>
            <td style="font-family:var(--font-mono);font-size:.78rem;">${b.odds}</td>
            <td style="color:var(--accent);font-family:var(--font-mono);font-size:.78rem;">${ev>0?'+':''}${(ev*100).toFixed(1)}%</td>
            <td style="font-family:var(--font-mono);font-size:.78rem;">${b.stake}€</td>
            <td><span class="result-badge ${rClass}">${rLabel}</span></td>
            <td class="${b.profit>=0?'pnl-pos':'pnl-neg'}">${b.profit>=0?'+':''}${b.profit}€</td>
            <td>${b.status === 'pending' ? `<button class="btn-outline" style="font-size:.65rem;padding:.25rem .6rem;" onclick="markBet(${b.id},'won')">V</button> <button class="btn-outline" style="font-size:.65rem;padding:.25rem .6rem;" onclick="markBet(${b.id},'lost')">X</button>` : ''}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

async function markBet(betId, result) {
  const profit = result === 'won' ? 0 : 0;
  try {
    await apiCall(`/bets/${betId}`, {
      method: 'PATCH',
      body: JSON.stringify({ result, profit })
    });
    showToast(`Pari marqué comme : ${result === 'won' ? 'Gagné ✓' : 'Perdu ✗'}`, result === 'won' ? 'success' : 'error');
    await loadStats();
  } catch(e) {
    showToast('Erreur : ' + e.message, 'error');
  }
}
