"""
backtest.py
Simulation de stratégie value betting sur le jeu de test.

Logique identique à compute_prediction dans app.py :
  - Fair edge (overround retiré avant comparaison)
  - Blend XGBoost + Dixon-Coles
  - Quart-Kelly pour le sizing
  - Accord des deux modèles obligatoire
"""

import numpy as np
import pandas as pd


def run_backtest(
    df_test: pd.DataFrame,
    value_threshold: float = 0.05,   # MIN_FAIR_EDGE
    mise: float = 1.0,
    dc_weight: float = 0.45,
    kelly_frac: float = 0.25,
    min_kelly: float = 0.02,
    min_prob: float = 0.40,
) -> pd.DataFrame:
    """
    Simule la stratégie value betting sur le jeu de test.

    Filtres cumulatifs :
        1. Fair edge (edge vs cotes justes sans overround) ≥ value_threshold
        2. Quart-Kelly ≥ min_kelly
        3. Proba modèle ≥ min_prob
        4. XGBoost et Dixon-Coles d'accord (si DC disponible)

    Args:
        df_test          : DataFrame avec prob_H/D/A, odds_H/D/A, result
                           et optionnellement dc_prob_H/D/A
        value_threshold  : fair edge minimal (défaut : 5 %)
        mise             : mise unitaire en € (défaut : 1 €)
        dc_weight        : poids Dixon-Coles dans le blend (défaut : 0.45)
        kelly_frac       : fraction Kelly (0.25 = quart-Kelly)
        min_kelly        : Kelly minimum après fraction (défaut : 2 %)
        min_prob         : probabilité minimale du modèle (défaut : 40 %)

    Returns:
        DataFrame trié par date avec le détail de chaque pari retenu.
    """
    required = ["prob_H", "prob_D", "prob_A", "odds_H", "odds_D", "odds_A", "result"]
    missing = [c for c in required if c not in df_test.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans df_test : {missing}")

    has_dc = all(c in df_test.columns for c in ["dc_prob_H", "dc_prob_D", "dc_prob_A"])

    bets = []

    for _, row in df_test.iterrows():
        odds = [float(row["odds_H"]), float(row["odds_D"]), float(row["odds_A"])]

        # ── Probas XGBoost ─────────────────────────────────────────
        proba_xgb = np.array([row["prob_H"], row["prob_D"], row["prob_A"]], dtype=float)

        # ── Blend avec Dixon-Coles ─────────────────────────────────
        proba_dc = None
        if has_dc:
            dc_raw = np.array([row["dc_prob_H"], row["dc_prob_D"], row["dc_prob_A"]], dtype=float)
            if not np.allclose(dc_raw, 1 / 3):
                proba_dc = dc_raw

        if proba_dc is not None:
            proba = (1 - dc_weight) * proba_xgb + dc_weight * proba_dc
            proba = proba / proba.sum()
        else:
            proba = proba_xgb

        # ── Fair edge ──────────────────────────────────────────────
        overround = sum(1.0 / o for o in odds)
        fair  = [1.0 / o / overround for o in odds]
        edges = [proba[i] - fair[i] for i in range(3)]

        # ── Accord des modèles ─────────────────────────────────────
        xgb_best = int(np.argmax(proba_xgb))
        dc_best  = int(np.argmax(proba_dc)) if proba_dc is not None else xgb_best

        # ── Sélection du meilleur pari ─────────────────────────────
        best_bet   = None
        best_kelly = -1.0

        for i, outcome in enumerate(["H", "D", "A"]):
            p = float(proba[i])
            b = odds[i] - 1.0
            full_kelly    = max(0.0, (p * b - (1.0 - p)) / b)
            quarter_kelly = min(full_kelly * kelly_frac, 0.25)

            models_agree = (proba_dc is None) or (xgb_best == dc_best == i)

            if (edges[i]    >= value_threshold
                    and quarter_kelly >= min_kelly
                    and p           >= min_prob
                    and models_agree):
                if quarter_kelly > best_kelly:
                    best_kelly = quarter_kelly
                    best_bet = {
                        "outcome":      outcome,
                        "idx":          i,
                        "proba":        p,
                        "odds":         odds[i],
                        "edge":         edges[i],
                        "kelly":        quarter_kelly,
                    }

        if best_bet is None:
            continue

        won    = row["result"] == best_bet["outcome"]
        profit = (best_bet["odds"] - 1.0) * mise if won else -mise

        bets.append({
            "Date":             row.get("Date"),
            "Match":            f"{row['HomeTeam']} vs {row['AwayTeam']}",
            "Pari":             best_bet["outcome"],
            "Cote":             round(best_bet["odds"], 2),
            "Proba_modele":     round(best_bet["proba"], 3),
            "Edge":             round(best_bet["edge"], 3),
            "Kelly":            round(best_bet["kelly"], 3),
            "Résultat":         row["result"],
            "Gagné":            won,
            "Profit":           round(profit, 2),
        })

    if not bets:
        return pd.DataFrame()

    return pd.DataFrame(bets).sort_values("Date").reset_index(drop=True)
