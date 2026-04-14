"""
injuries_api.py
Blessés & suspendus via API-Football (plan gratuit : 100 req/jour).
Inscription gratuite : https://dashboard.api-football.com/register

Ajouter dans .env :
    API_FOOTBALL_KEY=votre_cle_ici
"""

import os
import time
import requests
import numpy as np
from datetime import datetime, timezone
from difflib import SequenceMatcher

BASE_URL = "https://v3.football.api-sports.io"

# Mapping code football-data.co.uk → id API-Football
LEAGUE_IDS = {
    "E0":  39,   # Premier League
    "F1":  61,   # Ligue 1
    "D1":  78,   # Bundesliga
    "SP1": 140,  # La Liga
    "I1":  135,  # Serie A
    "UCL": 2,    # Ligue des Champions
}


# ─── Helpers bas niveau ───────────────────────────────────────────
def _headers() -> dict:
    key = os.environ.get("API_FOOTBALL_KEY", "")
    if not key:
        raise ValueError("API_FOOTBALL_KEY introuvable dans .env")
    return {"x-apisports-key": key}


def _current_season() -> int:
    """Retourne l'année de début de la saison en cours (ex: 2025 pour 2025/2026)."""
    now = datetime.now(timezone.utc)
    return now.year if now.month >= 7 else now.year - 1


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


# ─── Requêtes API ─────────────────────────────────────────────────
def get_next_fixtures(league_code: str, n: int = 20) -> tuple[list, int]:
    """
    Prochains fixtures d'une ligue (1 requête API).
    Retourne (fixtures, remaining_quota).
    """
    lid = LEAGUE_IDS.get(league_code)
    if not lid:
        return [], 100
    try:
        r = requests.get(
            f"{BASE_URL}/fixtures",
            headers=_headers(),
            params={"league": lid, "season": _current_season(), "next": n},
            timeout=10,
        )
        remaining = int(r.headers.get("x-ratelimit-requests-remaining", 100))
        return r.json().get("response", []), remaining
    except Exception:
        return [], 100


def get_fixture_injuries(fixture_id: int) -> list:
    """
    Joueurs absents (blessés + suspendus) pour un fixture (1 requête API).
    Chaque item : {player: {name}, team: {id}, type: 'Injury'|'Suspension', reason: str}
    """
    try:
        r = requests.get(
            f"{BASE_URL}/injuries",
            headers=_headers(),
            params={"fixture": fixture_id},
            timeout=10,
        )
        return r.json().get("response", [])
    except Exception:
        return []


# ─── Matching fixture ─────────────────────────────────────────────
def _find_fixture(match: dict, fixtures: list) -> dict | None:
    """
    Trouve le fixture api-football correspondant à un match odds-API.
    Critères : écart de date ≤ 2j ET similarité de nom ≥ 0.45.
    """
    match_dt = match["commence_time"]
    best_score, best_fix = 0.0, None

    for fix in fixtures:
        try:
            fix_dt = datetime.fromisoformat(
                fix["fixture"]["date"].replace("Z", "+00:00")
            )
        except Exception:
            continue

        if abs((fix_dt - match_dt).total_seconds()) > 2 * 86400:
            continue

        score = (
            _similarity(match["home_team"], fix["teams"]["home"]["name"])
            + _similarity(match["away_team"], fix["teams"]["away"]["name"])
        ) / 2

        if score > best_score:
            best_score, best_fix = score, fix

    return best_fix if best_score >= 0.45 else None


# ─── Fonction principale ──────────────────────────────────────────
def build_injury_reports(upcoming_matches: list,
                          league_by_id: dict,
                          delay: float = 0.35) -> dict:
    """
    Construit les rapports de blessures pour tous les matchs à venir.

    Args:
        upcoming_matches : liste issue de get_upcoming_matches()
        league_by_id     : {match_id: league_code}
        delay            : pause entre requêtes (secondes)

    Returns:
        {match_id: {
            "home_out"   : int,          # nombre de joueurs absents domicile
            "away_out"   : int,          # nombre de joueurs absents extérieur
            "home_names" : [{"name":…, "type":…, "reason":…}],
            "away_names" : [{"name":…, "type":…, "reason":…}],
            "quota"      : int,          # requêtes restantes après ce rapport
        }}
    """
    if not os.environ.get("API_FOOTBALL_KEY", ""):
        return {}   # clé absente → pas de données, pas d'erreur

    # 1. Fixtures par ligue (1 req / ligue)
    fixtures_by_league: dict[str, list] = {}
    quota = 100
    for code in set(league_by_id.values()):
        fixes, quota = get_next_fixtures(code, n=25)
        fixtures_by_league[code] = fixes
        time.sleep(delay)

    # 2. Injuries par fixture (1 req / match unique)
    cache: dict[int, list] = {}
    reports: dict[str, dict] = {}

    for match in upcoming_matches:
        mid  = match["id"]
        code = league_by_id.get(mid)
        if not code or code not in fixtures_by_league:
            continue

        fix = _find_fixture(match, fixtures_by_league[code])
        if not fix:
            continue

        fid      = fix["fixture"]["id"]
        home_tid = fix["teams"]["home"]["id"]
        away_tid = fix["teams"]["away"]["id"]

        if fid not in cache:
            cache[fid] = get_fixture_injuries(fid)
            quota -= 1
            time.sleep(delay)

        home_out, away_out = [], []
        for p in cache[fid]:
            entry = {
                "name":   p["player"]["name"],
                "type":   p.get("type", "?"),
                "reason": p.get("reason", ""),
            }
            if p["team"]["id"] == home_tid:
                home_out.append(entry)
            elif p["team"]["id"] == away_tid:
                away_out.append(entry)

        reports[mid] = {
            "home_out":   len(home_out),
            "away_out":   len(away_out),
            "home_names": home_out,
            "away_names": away_out,
            "quota":      max(quota, 0),
        }

    return reports


# ─── Ajustement des probabilités ─────────────────────────────────
def adjust_proba_for_injuries(proba: np.ndarray,
                               home_out: int,
                               away_out: int) -> np.ndarray:
    """
    Ajuste les probabilités selon le nombre d'absents.

    Heuristique : chaque joueur absent ≈ -2.5 % de force pour son équipe,
    redistribué sur match nul (35 %) et l'adversaire (65 %).
    Capé à 15 % max par équipe.
    """
    p = proba.astype(float).copy()
    K = 0.025   # impact par joueur absent
    CAP = 0.15  # cap total

    if home_out > 0:
        adj = min(home_out * K, CAP)
        p[0] -= adj
        p[1] += adj * 0.35
        p[2] += adj * 0.65

    if away_out > 0:
        adj = min(away_out * K, CAP)
        p[2] -= adj
        p[1] += adj * 0.35
        p[0] += adj * 0.65

    p = np.clip(p, 0.01, 1.0)
    return p / p.sum()
