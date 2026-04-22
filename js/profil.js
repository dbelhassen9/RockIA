/* ═══════════════════════════════════════════════════
   RockAI — Profil page logic
   ═══════════════════════════════════════════════════ */

const DEFAULT_SETTINGS = {
  bankroll:      1000,
  maxStakePct:   5,
  kellyFraction: 0.5,
  minEv:         3,
  sportsFilter:  'all',
  notifSetting:  'off',
};

function loadProfil(user) {
  if (!user) { window.location.href = 'index.html'; return; }

  // Avatar
  const initials = user.full_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  document.getElementById('profil-avatar-big').textContent = initials;
  document.getElementById('profil-name').textContent  = user.full_name;
  document.getElementById('profil-email').textContent = user.email || '—';
  document.getElementById('profil-plan').textContent  = user.plan === 'pro' ? '⭐ Plan Pro' : `🎯 Plan Gratuit`;

  // Credits (free plan only)
  if (user.plan !== 'pro') {
    const creditsWrap = document.getElementById('credits-wrap');
    if (creditsWrap) creditsWrap.style.display = '';
    document.getElementById('credits-val').textContent = user.credits;
    const bar = document.getElementById('credits-bar');
    if (bar) bar.style.width = `${Math.min(100, (user.credits / 50) * 100)}%`;

    const upgradeCard = document.getElementById('upgrade-card');
    if (upgradeCard) upgradeCard.style.display = '';
  }

  loadSettings();
}

function loadSettings() {
  const s = JSON.parse(localStorage.getItem('rockai_settings') || '{}');
  const merged = { ...DEFAULT_SETTINGS, ...s };

  document.getElementById('bankroll').value       = merged.bankroll;
  document.getElementById('max-stake-pct').value  = merged.maxStakePct;
  document.getElementById('kelly-fraction').value = merged.kellyFraction;
  document.getElementById('min-ev').value         = merged.minEv;
  document.getElementById('sports-filter').value  = merged.sportsFilter;
  document.getElementById('notif-setting').value  = merged.notifSetting;
}

function saveSettings() {
  const s = {
    bankroll:      parseFloat(document.getElementById('bankroll').value) || DEFAULT_SETTINGS.bankroll,
    maxStakePct:   parseFloat(document.getElementById('max-stake-pct').value) || DEFAULT_SETTINGS.maxStakePct,
    kellyFraction: parseFloat(document.getElementById('kelly-fraction').value) || DEFAULT_SETTINGS.kellyFraction,
    minEv:         parseFloat(document.getElementById('min-ev').value) || DEFAULT_SETTINGS.minEv,
    sportsFilter:  document.getElementById('sports-filter').value,
    notifSetting:  document.getElementById('notif-setting').value,
  };
  localStorage.setItem('rockai_settings', JSON.stringify(s));
  showToast('Paramètres sauvegardés ✓', 'success');
}

function resetSettings() {
  localStorage.removeItem('rockai_settings');
  loadSettings();
  showToast('Paramètres réinitialisés', 'info');
}

function confirmLogout() {
  if (confirm('Se déconnecter de RockAI ?')) {
    clearToken();
    window.location.href = 'index.html';
  }
}
