"""
dixon_coles.py
Modèle de Dixon-Coles avec décroissance temporelle pour la prédiction de buts.

Référence : Dixon & Coles (1997) "Modelling Association Football Scores
and Inefficiencies in the Football Betting Market"

Usage :
    dc = DixonColesModel(xi=0.0065).fit(df)
    proba = dc.predict_proba("Arsenal", "Chelsea")  # [P(H), P(D), P(A)]
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson


# ─── Correction faibles scores ────────────────────────────────────────
def _tau(x: int, y: int, lam1: float, lam2: float, rho: float) -> float:
    """Facteur correctif Dixon-Coles pour les scores faibles (x+y ≤ 2)."""
    if x == 0 and y == 0:
        return 1.0 - lam1 * lam2 * rho
    elif x == 1 and y == 0:
        return 1.0 + lam2 * rho
    elif x == 0 and y == 1:
        return 1.0 + lam1 * rho
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


# ─── Modèle ───────────────────────────────────────────────────────────
class DixonColesModel:
    """
    Modèle de Dixon-Coles par équipe.

    Paramètres estimés :
        attack[team]  : force offensive (normalisée, moyenne = 1)
        defense[team] : solidité défensive (plus élevé = meilleure défense)
        home_adv      : multiplicateur avantage domicile
        rho           : correction corrélation scores faibles
    """

    def __init__(self, xi: float = 0.0065):
        """
        xi : taux de décroissance temporelle (par jour).
             0.0065 ≈ demi-vie ~107 jours (~3,5 mois).
             Mettre 0 pour ignorer le temps.
        """
        self.xi = xi
        self.attack: dict    = {}
        self.defense: dict   = {}
        self.home_adv: float = 1.3
        self.rho: float      = -0.1
        self.teams: list     = []
        self._fitted: bool   = False

    # ── Fit ───────────────────────────────────────────────────────────
    def fit(self, df: pd.DataFrame) -> "DixonColesModel":
        """
        Entraîne le modèle sur l'historique.

        df doit contenir : Date, HomeTeam, AwayTeam, home_goals, away_goals
        """
        df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam",
                                "home_goals", "away_goals"]).copy()
        df = df.sort_values("Date").reset_index(drop=True)

        if len(df) < 30:
            return self   # pas assez de données

        self.teams = sorted(set(df["HomeTeam"]) | set(df["AwayTeam"]))
        n   = len(self.teams)
        idx = {t: i for i, t in enumerate(self.teams)}

        ref_date = df["Date"].max()
        days_ago = (ref_date - df["Date"]).dt.days.values.astype(float)
        weights  = np.exp(-self.xi * days_ago)

        hg = df["home_goals"].values.astype(int)
        ag = df["away_goals"].values.astype(int)
        hi = np.array([idx[t] for t in df["HomeTeam"]])
        ai = np.array([idx[t] for t in df["AwayTeam"]])

        # ── Vecteur initial ──────────────────────────────────────────
        # [log_atk × n, log_def × n, log_home_adv, rho]
        # Contrainte : attack[0] fixé à 0 (log) pour identifiabilité
        x0 = np.zeros(2 * n + 2)
        x0[2 * n]     = np.log(1.3)    # home_adv init
        x0[2 * n + 1] = -0.1           # rho init

        def neg_loglik(params: np.ndarray) -> float:
            log_atk = params[:n]
            log_def = params[n:2 * n]
            h_adv   = np.exp(params[2 * n])
            rho     = params[2 * n + 1]

            # Fixer l'échelle : log_atk[0] = 0
            log_atk = log_atk - log_atk[0]

            lam1 = np.exp(log_atk[hi] + log_def[ai]) * h_adv
            lam2 = np.exp(log_atk[ai] + log_def[hi])

            lam1 = np.clip(lam1, 1e-6, 20.0)
            lam2 = np.clip(lam2, 1e-6, 20.0)

            log_p = poisson.logpmf(hg, lam1) + poisson.logpmf(ag, lam2)

            # Correction tau vectorisée
            tau = np.ones(len(df))
            m00 = (hg == 0) & (ag == 0)
            m10 = (hg == 1) & (ag == 0)
            m01 = (hg == 0) & (ag == 1)
            m11 = (hg == 1) & (ag == 1)

            tau[m00] = 1.0 - lam1[m00] * lam2[m00] * rho
            tau[m10] = 1.0 + lam2[m10] * rho
            tau[m01] = 1.0 + lam1[m01] * rho
            tau[m11] = 1.0 - rho

            tau = np.clip(tau, 1e-10, None)

            ll = weights * (log_p + np.log(tau))
            return -ll.sum()

        result = minimize(
            neg_loglik,
            x0,
            method="L-BFGS-B",
            options={"maxiter": 500, "ftol": 1e-9, "gtol": 1e-6},
        )

        params  = result.x
        log_atk = params[:n] - params[0]   # normalise attack[0] = 1
        log_def = params[n:2 * n]

        atk = np.exp(log_atk)
        dfs = np.exp(log_def)

        self.attack   = dict(zip(self.teams, atk))
        self.defense  = dict(zip(self.teams, dfs))
        self.home_adv = float(np.exp(params[2 * n]))
        self.rho      = float(np.clip(params[2 * n + 1], -0.5, 0.5))
        self._fitted  = True
        return self

    # ── Prédiction ────────────────────────────────────────────────────
    def predict_proba(self, home_team: str, away_team: str,
                      max_goals: int = 10) -> np.ndarray:
        """
        Retourne np.array([P(victoire domicile), P(nul), P(victoire extérieur)]).
        Retourne [1/3, 1/3, 1/3] si une équipe est inconnue ou si le modèle
        n'est pas entraîné.
        """
        neutral = np.array([1 / 3, 1 / 3, 1 / 3])

        if not self._fitted:
            return neutral

        atk_h = self.attack.get(home_team)
        def_h = self.defense.get(home_team)
        atk_a = self.attack.get(away_team)
        def_a = self.defense.get(away_team)

        if any(v is None for v in [atk_h, def_h, atk_a, def_a]):
            return neutral

        lam1 = max(atk_h * def_a * self.home_adv, 1e-6)
        lam2 = max(atk_a * def_h, 1e-6)

        # Matrice des scores (x buts dom., y buts ext.)
        xs = np.arange(max_goals + 1)
        ys = np.arange(max_goals + 1)
        pmf1 = poisson.pmf(xs, lam1)   # shape (max_goals+1,)
        pmf2 = poisson.pmf(ys, lam2)
        score_matrix = np.outer(pmf1, pmf2)   # [x, y]

        # Correction tau pour les 4 cas faibles scores
        for (x, y) in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            score_matrix[x, y] *= _tau(x, y, lam1, lam2, self.rho)

        total = score_matrix.sum()
        if total <= 0:
            return neutral
        score_matrix /= total

        p_home = float(np.sum(np.tril(score_matrix, -1)))   # x > y
        p_draw = float(np.trace(score_matrix))
        p_away = float(np.sum(np.triu(score_matrix, 1)))    # y > x

        proba = np.clip([p_home, p_draw, p_away], 1e-6, 1.0)
        return proba / proba.sum()

    def is_known(self, team: str) -> bool:
        return team in self.attack

    # ── Infos debug ───────────────────────────────────────────────────
    def team_strength(self, team: str) -> dict | None:
        if team not in self.attack:
            return None
        return {
            "attack":  round(self.attack[team], 3),
            "defense": round(self.defense[team], 3),
        }
