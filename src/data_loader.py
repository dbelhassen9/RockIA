"""
data_loader.py
Téléchargement et nettoyage des données depuis football-data.co.uk
"""

import pandas as pd
import requests
import os

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"

LEAGUES = {
    "E0": "Premier League",
    "F1": "Ligue 1",
    "D1": "Bundesliga",
    "SP1": "La Liga",
    "I1": "Serie A",
}

COLS_BASE  = ["Season", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]
COLS_ODDS  = ["B365H", "B365D", "B365A"]
COLS_XG    = ["HxG", "AxG"]        # Expected goals (top 5 ligues depuis ~2020)
COLS_SHOTS = ["HST", "AST"]        # Shots on target (proxy xG si HxG absent)


def download_data(league: str = "E0", seasons: list = None) -> pd.DataFrame:
    if seasons is None:
        seasons = ["2425", "2526"]

    dfs = []
    for season in seasons:
        url = BASE_URL.format(season=season, league=league)
        try:
            df = pd.read_csv(url, encoding="latin-1")
            df["Season"] = season
            dfs.append(df)
            print(f"[OK] {LEAGUES.get(league, league)} - saison {season} : {len(df)} matchs")
        except Exception as e:
            print(f"[WARN] Saison {season} indisponible : {e}")

    if not dfs:
        raise ValueError("Aucune donnée chargée.")

    return pd.concat(dfs, ignore_index=True)


def clean_data(raw: pd.DataFrame) -> pd.DataFrame:
    want = COLS_BASE + COLS_ODDS + COLS_XG + COLS_SHOTS
    cols = [c for c in want if c in raw.columns]
    df = raw[cols].copy()

    df = df.rename(columns={
        "FTHG": "home_goals",  "FTAG": "away_goals",  "FTR":  "result",
        "B365H": "odds_H",     "B365D": "odds_D",      "B365A": "odds_A",
        "HxG":  "home_xg",    "AxG":  "away_xg",
        "HST":  "home_sot",   "AST":  "away_sot",
    })

    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "result",
                            "home_goals", "away_goals",
                            "odds_H", "odds_D", "odds_A"]).reset_index(drop=True)
    df = df.sort_values("Date").reset_index(drop=True)

    # ── xG : vraies valeurs > proxy SOT > proxy buts ────────────────
    if "home_xg" not in df.columns or df["home_xg"].isna().all():
        if "home_sot" in df.columns and not df["home_sot"].isna().all():
            # 1 tir cadré ≈ 0.29 xG (ratio empirique football-data)
            df["home_xg"] = df["home_sot"] / 3.5
            df["away_xg"] = df["away_sot"] / 3.5
        else:
            df["home_xg"] = df["home_goals"].astype(float)
            df["away_xg"] = df["away_goals"].astype(float)
    else:
        df["home_xg"] = pd.to_numeric(df["home_xg"], errors="coerce").fillna(df["home_goals"])
        df["away_xg"] = pd.to_numeric(df["away_xg"], errors="coerce").fillna(df["away_goals"])

    # Encodage cible
    df["target"] = df["result"].map({"H": 0, "D": 1, "A": 2})

    return df
