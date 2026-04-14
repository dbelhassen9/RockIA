"""
competition_api.py
Résultats récents UCL via football-data.org (gratuit, 10 req/min).
Inscription: https://www.football-data.org/client/register

Ajouter dans .env:
    FOOTBALL_DATA_ORG_KEY=votre_cle_ici
"""

import os
import requests
import pandas as pd
from datetime import datetime, timezone
from difflib import SequenceMatcher

BASE = "https://api.football-data.org/v4"

# code football-data.co.uk → code football-data.org
EXTRA_COMPS = {
    "UCL": "CL",   # Ligue des Champions
}

# Coupes nationales (décommenter si votre abonnement les couvre)
# CUPS = {
#     "E0":  "FAC",   # FA Cup
#     "SP1": "CDP",   # Copa del Rey
#     "D1":  "DFB",   # DFB-Pokal
#     "F1":  "CDL",   # Coupe de France
#     "I1":  "CIT",   # Coppa Italia
# }


def _headers() -> dict:
    key = os.environ.get("FOOTBALL_DATA_ORG_KEY", "")
    if not key:
        raise ValueError("FOOTBALL_DATA_ORG_KEY absente dans .env")
    return {"X-Auth-Token": key}


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _best_match(name: str, candidates: list, threshold: float = 0.5) -> str | None:
    best_s, best_c = 0.0, None
    for c in candidates:
        s = _sim(name, c)
        if s > best_s:
            best_s, best_c = s, c
    return best_c if best_s >= threshold else None


def _current_season() -> int:
    now = datetime.now(timezone.utc)
    return now.year if now.month >= 7 else now.year - 1


def _fetch_finished(comp_code: str, season: int) -> list:
    """Retourne les matchs terminés d'une compétition."""
    try:
        r = requests.get(
            f"{BASE}/competitions/{comp_code}/matches",
            headers=_headers(),
            params={"season": season, "status": "FINISHED"},
            timeout=15,
        )
        if r.status_code != 200:
            return []
        return r.json().get("matches", [])
    except Exception:
        return []


def build_extra_match_df(training_teams: list) -> pd.DataFrame:
    """
    Construit un DataFrame de matchs UCL compatibles avec df pour l'affichage de forme.
    Colonnes retournées : Date, HomeTeam, AwayTeam, home_goals, away_goals, result, league
    Ne nécessite pas de clé si FOOTBALL_DATA_ORG_KEY est absente → retourne DataFrame vide.
    """
    if not os.environ.get("FOOTBALL_DATA_ORG_KEY", ""):
        return pd.DataFrame()

    season = _current_season()
    rows = []

    for our_code, fdorg_code in EXTRA_COMPS.items():
        matches = _fetch_finished(fdorg_code, season)
        for m in matches:
            score = m.get("score", {}).get("fullTime", {})
            hg, ag = score.get("home"), score.get("away")
            if hg is None or ag is None:
                continue
            try:
                dt = datetime.fromisoformat(
                    m["utcDate"].replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except Exception:
                continue

            ht_raw = m["homeTeam"]["name"]
            at_raw = m["awayTeam"]["name"]

            ht = _best_match(ht_raw, training_teams)
            at = _best_match(at_raw, training_teams)

            # On ne garde que si au moins une équipe est connue
            if ht is None and at is None:
                continue
            ht = ht or ht_raw
            at = at or at_raw

            result = "H" if hg > ag else ("A" if ag > hg else "D")
            rows.append({
                "Date":       dt,
                "HomeTeam":   ht,
                "AwayTeam":   at,
                "home_goals": int(hg),
                "away_goals": int(ag),
                "result":     result,
                "league":     our_code,
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
    df["target"] = df["result"].map({"H": 0, "D": 1, "A": 2})
    return df
