"""
features.py
Calcul des features glissantes + ELO + H2H + fatigue pour chaque match.
"""

import pandas as pd
import numpy as np

WINDOW       = 5   # fenêtre forme / buts / xG
H2H_WINDOW   = 3   # nombre de confrontations directes
FATIGUE_DAYS = 7   # jours pour la fenêtre fatigue


# ─── ELO ───────────────────────────────────────────────────────────
def compute_elo(df: pd.DataFrame, k: int = 32, initial: float = 1500.0):
    """
    Calcule les ratings ELO avant chaque match (pré-match).
    Retourne (df_enrichi, dict {équipe: elo_courant}).
    """
    df = df.sort_values("Date").reset_index(drop=True)
    ratings: dict = {}
    home_elo_pre, away_elo_pre = [], []

    for _, row in df.iterrows():
        rh = ratings.get(row["HomeTeam"], initial)
        ra = ratings.get(row["AwayTeam"], initial)

        home_elo_pre.append(rh)
        away_elo_pre.append(ra)

        eh = 1.0 / (1.0 + 10.0 ** ((ra - rh) / 400.0))
        ea = 1.0 - eh

        result = row["result"]
        sh = 1.0 if result == "H" else (0.5 if result == "D" else 0.0)
        sa = 1.0 - sh

        ratings[row["HomeTeam"]] = rh + k * (sh - eh)
        ratings[row["AwayTeam"]] = ra + k * (sa - ea)

    df["home_elo"] = home_elo_pre
    df["away_elo"] = away_elo_pre
    df["elo_diff"] = df["home_elo"] - df["away_elo"]

    return df, ratings


# ─── Features glissantes ───────────────────────────────────────────
def compute_team_stats(df: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """
    Features glissantes par équipe (shift(1) anti-leakage).

    Nouvelles features v2 :
        home_home_form   — forme de l'équipe dom. calculée sur ses matchs à domicile seulement
        away_away_form   — forme de l'équipe ext. calculée sur ses matchs à l'extérieur seulement
    """
    df = df.sort_values("Date").reset_index(drop=True)
    has_xg = "home_xg" in df.columns and "away_xg" in df.columns

    # ── Vue domicile ───────────────────────────────────────────────
    home = df[["Date", "HomeTeam", "home_goals", "away_goals", "result"]].copy()
    home.columns = ["Date", "Team", "goals_scored", "goals_conceded", "result"]
    home["won"]     = home["result"] == "H"
    home["drawn"]   = home["result"] == "D"
    home["is_home"] = True
    home["xg_scored"]   = df["home_xg"].values if has_xg else home["goals_scored"].astype(float).values
    home["xg_conceded"] = df["away_xg"].values if has_xg else home["goals_conceded"].astype(float).values

    # ── Vue extérieur ──────────────────────────────────────────────
    away = df[["Date", "AwayTeam", "away_goals", "home_goals", "result"]].copy()
    away.columns = ["Date", "Team", "goals_scored", "goals_conceded", "result"]
    away["won"]     = away["result"] == "A"
    away["drawn"]   = away["result"] == "D"
    away["is_home"] = False
    away["xg_scored"]   = df["away_xg"].values if has_xg else away["goals_scored"].astype(float).values
    away["xg_conceded"] = df["home_xg"].values if has_xg else away["goals_conceded"].astype(float).values

    all_records = pd.concat([home, away]).sort_values("Date")
    all_records["points"] = all_records["won"] * 3 + all_records["drawn"]

    grp = all_records.groupby("Team")

    def roll(series):
        return series.shift(1).rolling(window, min_periods=1).mean()

    all_records["form"]         = grp["points"].transform(roll)
    all_records["avg_scored"]   = grp["goals_scored"].transform(roll)
    all_records["avg_conceded"] = grp["goals_conceded"].transform(roll)
    all_records["avg_xg"]       = grp["xg_scored"].transform(roll)

    # ── Forme venue-spécifique ─────────────────────────────────────
    home_records = all_records[all_records["is_home"]].copy()
    away_records = all_records[~all_records["is_home"]].copy()

    home_records["home_venue_form"] = (
        home_records.groupby("Team")["points"].transform(roll)
    )
    away_records["away_venue_form"] = (
        away_records.groupby("Team")["points"].transform(roll)
    )

    # ── Stats domicile ─────────────────────────────────────────────
    home_stats = (
        home_records
        .rename(columns={
            "Team":             "HomeTeam",
            "form":             "home_form",
            "avg_scored":       "home_avg_scored",
            "avg_conceded":     "home_avg_conceded",
            "avg_xg":           "home_avg_xg",
            "home_venue_form":  "home_home_form",
        })[["Date", "HomeTeam", "home_form", "home_avg_scored",
            "home_avg_conceded", "home_avg_xg", "home_home_form"]]
    )

    # ── Stats extérieur ────────────────────────────────────────────
    away_stats = (
        away_records
        .rename(columns={
            "Team":             "AwayTeam",
            "form":             "away_form",
            "avg_scored":       "away_avg_scored",
            "avg_conceded":     "away_avg_conceded",
            "avg_xg":           "away_avg_xg",
            "away_venue_form":  "away_away_form",
        })[["Date", "AwayTeam", "away_form", "away_avg_scored",
            "away_avg_conceded", "away_avg_xg", "away_away_form"]]
    )

    df = df.merge(home_stats, on=["Date", "HomeTeam"], how="left")
    df = df.merge(away_stats, on=["Date", "AwayTeam"], how="left")

    df["form_diff"]    = df["home_form"]        - df["away_form"]
    df["attack_diff"]  = df["home_avg_scored"]  - df["away_avg_scored"]
    df["defense_diff"] = df["home_avg_conceded"] - df["away_avg_conceded"]
    df["xg_diff"]      = df["home_avg_xg"]      - df["away_avg_xg"]

    df = df.dropna().reset_index(drop=True)
    return df


# ─── H2H ──────────────────────────────────────────────────────────
def compute_h2h(df: pd.DataFrame, n: int = H2H_WINDOW) -> pd.DataFrame:
    """
    Pour chaque match, calcule les n dernières confrontations directes :
        h2h_home_win_rate — taux de victoires de l'équipe domicile actuelle
        h2h_draw_rate     — taux de matchs nuls
    Groupe par paire de teams (efficient vs. brute-force iterrows).
    """
    df = df.sort_values("Date").reset_index(drop=True)

    # Clé canonique de la paire (ordre alphabétique)
    df["_pair"] = [
        tuple(sorted([r["HomeTeam"], r["AwayTeam"]]))
        for _, r in df[["HomeTeam", "AwayTeam"]].iterrows()
    ]

    home_win_rates = np.full(len(df), 1 / 3)
    draw_rates     = np.full(len(df), 1 / 4)

    for _pair, grp_idx in df.groupby("_pair").groups.items():
        grp_idx = sorted(grp_idx)
        if len(grp_idx) <= 1:
            continue

        for pos, idx in enumerate(grp_idx):
            if pos == 0:
                continue

            prev_idx = grp_idx[max(0, pos - n): pos]
            prev = df.loc[prev_idx]
            if prev.empty:
                continue

            home_here = df.loc[idx, "HomeTeam"]

            wins = sum(
                (r["HomeTeam"] == home_here and r["result"] == "H") or
                (r["AwayTeam"] == home_here and r["result"] == "A")
                for _, r in prev.iterrows()
            )
            draws = sum(r["result"] == "D" for _, r in prev.iterrows())

            home_win_rates[idx] = wins / len(prev)
            draw_rates[idx]     = draws / len(prev)

    df["h2h_home_win_rate"] = home_win_rates
    df["h2h_draw_rate"]     = draw_rates
    df = df.drop(columns=["_pair"])
    return df


# ─── Fatigue / congestion calendrier ──────────────────────────────
def compute_fatigue(df: pd.DataFrame, days: int = FATIGUE_DAYS) -> pd.DataFrame:
    """
    Nombre de matchs joués dans les `days` derniers jours (fenêtre glissante).
    Utilise un index par équipe pour éviter un O(n²) pur.
    """
    df = df.sort_values("Date").reset_index(drop=True)

    all_teams = set(df["HomeTeam"].unique()) | set(df["AwayTeam"].unique())
    team_dates: dict = {}
    for team in all_teams:
        mask = (df["HomeTeam"] == team) | (df["AwayTeam"] == team)
        team_dates[team] = df.loc[mask, "Date"].values  # sorted numpy array

    home_fat = np.zeros(len(df), dtype=int)
    away_fat = np.zeros(len(df), dtype=int)

    for i, row in df.iterrows():
        cutoff = row["Date"] - pd.Timedelta(days=days)

        ht = row["HomeTeam"]
        hd = team_dates[ht]
        home_fat[i] = int(np.sum((hd > cutoff) & (hd < row["Date"])))

        at = row["AwayTeam"]
        ad = team_dates[at]
        away_fat[i] = int(np.sum((ad > cutoff) & (ad < row["Date"])))

    df["home_fatigue"] = home_fat
    df["away_fatigue"] = away_fat
    return df


# ── Colonnes utilisées pour l'entraînement ────────────────────────
FEATURE_COLS = [
    # Forme récente (tous matchs)
    "home_form", "away_form", "form_diff",
    # Attaque / défense (buts)
    "home_avg_scored", "home_avg_conceded",
    "away_avg_scored", "away_avg_conceded",
    "attack_diff", "defense_diff",
    # ELO
    "home_elo", "away_elo", "elo_diff",
    # xG
    "home_avg_xg", "away_avg_xg", "xg_diff",
    # Forme venue-spécifique (NEW)
    "home_home_form", "away_away_form",
    # H2H (NEW)
    "h2h_home_win_rate", "h2h_draw_rate",
    # Fatigue (NEW)
    "home_fatigue", "away_fatigue",
]
