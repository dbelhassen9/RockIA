"""
odds_api.py
Récupération des fixtures à venir et cotes Winamax via The Odds API.
https://the-odds-api.com/
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from difflib import get_close_matches


# ─── Chargement de la clé API depuis .env ────────────────────────
def _load_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()


# ─── Constantes ───────────────────────────────────────────────────
BASE_URL = "https://api.the-odds-api.com/v4"
BOOKMAKER = "winamax_fr"

# Correspondance code ligue (football-data.co.uk) ↔ clé API
SPORT_KEYS = {
    "E0":  "soccer_epl",
    "F1":  "soccer_france_ligue_one",
    "D1":  "soccer_germany_bundesliga",
    "SP1": "soccer_spain_la_liga",
    "I1":  "soccer_italy_serie_a",
    "UCL": "soccer_uefa_champs_league",
}


# ─── Récupération des matchs à venir ─────────────────────────────
def get_upcoming_matches(league: str = "E0", days: int = 7) -> tuple:
    """
    Récupère les matchs à venir avec cotes Winamax pour les prochains `days` jours.

    Args:
        league: code ligue football-data.co.uk (ex: 'E0', 'F1')
        days: fenêtre en jours (défaut: 7)

    Returns:
        (matches, remaining) où matches est une liste de dicts:
            id, commence_time (datetime UTC), home_team, away_team,
            odds_H, odds_D, odds_A
        et remaining est le nombre de requêtes API restantes.
    """
    sport_key = SPORT_KEYS.get(league, "soccer_epl")
    api_key = os.environ.get("ODDS_API_KEY", "")
    if not api_key:
        raise ValueError("ODDS_API_KEY introuvable. Vérifiez votre fichier .env.")

    url = (
        f"{BASE_URL}/sports/{sport_key}/odds/"
        f"?apiKey={api_key}"
        f"&regions=eu"
        f"&bookmakers={BOOKMAKER}"
        f"&markets=h2h"
        f"&oddsFormat=decimal"
        f"&dateFormat=iso"
    )

    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
            remaining = int(r.headers.get("x-requests-remaining", 0))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Erreur API {e.code}: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Erreur réseau: {e}")

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)

    matches = []
    for m in data:
        dt = datetime.fromisoformat(m["commence_time"].replace("Z", "+00:00"))

        # Filtre: dans les 7 prochains jours, pas déjà commencé
        if dt < now or dt > cutoff:
            continue

        # Extraction des cotes Winamax
        odds_H = odds_D = odds_A = None
        for bk in m.get("bookmakers", []):
            if bk["key"] == BOOKMAKER:
                for mkt in bk.get("markets", []):
                    if mkt["key"] == "h2h":
                        for o in mkt["outcomes"]:
                            if o["name"] == m["home_team"]:
                                odds_H = o["price"]
                            elif o["name"] == m["away_team"]:
                                odds_A = o["price"]
                            else:
                                odds_D = o["price"]
                        break
                break

        # On garde uniquement les matchs avec cotes complètes
        if odds_H and odds_D and odds_A:
            matches.append({
                "id": m["id"],
                "commence_time": dt,
                "home_team": m["home_team"],
                "away_team": m["away_team"],
                "odds_H": odds_H,
                "odds_D": odds_D,
                "odds_A": odds_A,
            })

    matches.sort(key=lambda x: x["commence_time"])
    return matches, remaining


# ─── Fuzzy matching des noms d'équipes ───────────────────────────
# ─── Table d'alias (API → football-data.co.uk) ───────────────────
TEAM_ALIASES = {
    # Angleterre
    "Manchester United":          "Man United",
    "Manchester City":            "Man City",
    "Newcastle United":           "Newcastle",
    "Tottenham Hotspur":          "Tottenham",
    "Wolverhampton Wanderers":    "Wolves",
    "Brighton and Hove Albion":   "Brighton",
    "Brighton & Hove Albion":     "Brighton",
    "Nottingham Forest":          "Nott'm Forest",
    "Queens Park Rangers":        "QPR",
    "West Bromwich Albion":       "West Brom",
    "Sheffield Wednesday":        "Sheffield Weds",
    "Leeds United":               "Leeds",
    "Leicester City":             "Leicester",
    "Norwich City":               "Norwich",
    "Huddersfield Town":          "Huddersfield",
    "Stoke City":                 "Stoke",
    "Swansea City":               "Swansea",
    "Cardiff City":               "Cardiff",
    "Coventry City":              "Coventry",
    "Millwall":                   "Millwall",
    "Ipswich Town":               "Ipswich",
    "Sunderland":                 "Sunderland",
    # France
    "Paris Saint-Germain":        "Paris SG",
    "Olympique de Marseille":     "Marseille",
    "Olympique Lyonnais":         "Lyon",
    "AS Monaco":                  "Monaco",
    "Stade Rennais FC":           "Rennes",
    "Stade Brestois 29":          "Brest",
    "Le Havre AC":                "Le Havre",
    "FC Nantes":                  "Nantes",
    "OGC Nice":                   "Nice",
    "Montpellier HSC":            "Montpellier",
    "Toulouse FC":                "Toulouse",
    "Clermont Foot":              "Clermont",
    "Angers SCO":                 "Angers",
    "RC Strasbourg":              "Strasbourg",
    "FC Lorient":                 "Lorient",
    "AC Ajaccio":                 "Ajaccio",
    "Auxerre":                    "Auxerre",
    "Saint-Etienne":              "St Etienne",
    "LOSC Lille":                 "Lille",
    "Girondins de Bordeaux":      "Bordeaux",
    # Allemagne
    "FC Bayern Munich":           "Bayern Munich",
    "Borussia Dortmund":          "Dortmund",
    "Bayer 04 Leverkusen":        "Leverkusen",
    "Eintracht Frankfurt":        "Ein Frankfurt",
    "VfL Wolfsburg":              "Wolfsburg",
    "Borussia Monchengladbach":   "Monchengladbach",
    "SC Freiburg":                "Freiburg",
    "TSG Hoffenheim":             "Hoffenheim",
    "1. FC Union Berlin":         "Union Berlin",
    "VfB Stuttgart":              "Stuttgart",
    "FC Augsburg":                "Augsburg",
    "Hertha BSC":                 "Hertha",
    "FC St. Pauli":               "St Pauli",
    "Holstein Kiel":              "Kiel",
    "1. FC Koln":                 "Cologne",
    "1. FC Köln":                 "Cologne",
    "Hamburger SV":               "Hamburg",
    "Hannover 96":                "Hannover",
    "Schalke 04":                 "Schalke",
    "Werder Bremen":              "Werder",
    # Espagne
    "Athletic Club":              "Ath Bilbao",
    "Atletico Madrid":            "Ath Madrid",
    "Atlético de Madrid":         "Ath Madrid",
    "Real Betis":                 "Betis",
    "Real Sociedad":              "Sociedad",
    "Celta Vigo":                 "Celta",
    "Deportivo Alaves":           "Alaves",
    "Deportivo Alavés":           "Alaves",
    "Rayo Vallecano":             "Vallecano",
    "RCD Espanyol":               "Espanol",
    "Cadiz":                      "Cadiz",
    "UD Almeria":                 "Almeria",
    "Girona":                     "Girona",
    "Las Palmas":                 "Las Palmas",
    "Leganes":                    "Leganes",
    "Valladolid":                 "Valladolid",
    # Italie
    "Inter Milan":                "Inter",
    "AC Milan":                   "Milan",
    "SS Lazio":                   "Lazio",
    "Atalanta BC":                "Atalanta",
    "ACF Fiorentina":             "Fiorentina",
    "Torino FC":                  "Torino",
    "Genoa CFC":                  "Genoa",
    "Cagliari Calcio":            "Cagliari",
    "US Lecce":                   "Lecce",
    "Hellas Verona":              "Verona",
    "Udinese Calcio":             "Udinese",
    "Empoli FC":                  "Empoli",
    "Frosinone Calcio":           "Frosinone",
    "Bologna FC 1909":            "Bologna",
    "US Salernitana":             "Salernitana",
    "Venezia FC":                 "Venezia",
}


def match_team_name(api_name: str, training_teams: list) -> str:
    """
    Trouve le nom d'équipe le plus proche dans les données d'entraînement.
    Priorité : table d'alias → difflib → correspondance partielle → chevauchement de mots.

    Args:
        api_name: nom retourné par The Odds API (ex: 'Manchester United')
        training_teams: liste des noms dans les données d'entraînement (ex: ['Man United', ...])

    Returns:
        Nom matché dans training_teams, ou api_name si aucune correspondance trouvée.
    """
    # 0. Correspondance exacte
    if api_name in training_teams:
        return api_name

    # 1. Table d'alias
    alias = TEAM_ALIASES.get(api_name)
    if alias:
        if alias in training_teams:
            return alias
        # L'alias lui-même n'est pas exact → continuer avec l'alias comme base
        api_name = alias

    # 2. difflib (similarité de chaîne)
    close = get_close_matches(api_name, training_teams, n=1, cutoff=0.4)
    if close:
        return close[0]

    api_lower = api_name.lower()

    # 3. Correspondance partielle (l'un contient l'autre)
    for t in training_teams:
        t_lower = t.lower()
        if t_lower in api_lower or api_lower in t_lower:
            return t

    # 4. Chevauchement de mots
    api_words = set(api_lower.split())
    best_score, best_team = 0, api_name
    for t in training_teams:
        overlap = len(api_words & set(t.lower().split()))
        if overlap > best_score:
            best_score, best_team = overlap, t

    return best_team
