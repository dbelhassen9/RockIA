#!/usr/bin/env python3
"""
RockAI Backend v3.0
════════════════════════════════════════════════════════════
Méthode : Pinnacle comme référence (identique à StatsnBet)
  1. Fetch toutes les cotes via The Odds API (multi-bookmakers)
  2. Extrait Pinnacle comme "fair odds" (cote juste du marché)
  3. Compare chaque bookmaker contre Pinnacle → EV
  4. Si EV > seuil → value bet avec recommandation de mise (Kelly)
  5. Tout est exposé au frontend via /matches (agenda live)
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import jwt, bcrypt, sqlite3, os, time, asyncio, aiohttp, json, logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
SECRET_KEY        = os.getenv("SECRET_KEY", "change-this!")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ODDS_API_KEY      = os.getenv("ODDS_API_KEY", "")
DATABASE_PATH     = os.getenv("DATABASE_PATH", "rockai.db")
ALGORITHM         = "HS256"
TOKEN_EXPIRE_DAYS = 30

# Pinnacle a ~2-3% de marge → on retire ça pour avoir la fair odd
PINNACLE_MARGIN   = 0.02
# Seuil minimum pour afficher comme value bet
EV_MIN_DISPLAY    = 0.02   # 2%  → apparaît dans l'agenda
EV_MIN_ALERT      = 0.05   # 5%  → badge "VALUE BET" rouge
# Cache
ODDS_CACHE_SEC    = 180    # 3 min (cotes changent vite)

# Ligues supportées (the-odds-api.com sport keys)
LEAGUES = {
    "soccer_france_ligue_one":       "🇫🇷 Ligue 1",
    "soccer_epl":                    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League",
    "soccer_spain_la_liga":          "🇪🇸 La Liga",
    "soccer_germany_bundesliga":     "🇩🇪 Bundesliga",
    "soccer_italy_serie_a":          "🇮🇹 Serie A",
    "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_portugal_primeira_liga": "🇵🇹 Primeira Liga",
    "soccer_uefa_champs_league":     "🏆 Champions League",
    "soccer_uefa_europa_league":     "⚽ Europa League",
    "basketball_nba":                "🏀 NBA",
    "basketball_euroleague":         "🏀 Euroleague",
    "icehockey_nhl":                 "🏒 NHL",
    "baseball_mlb":                  "⚾ MLB",
    "tennis_atp_french_open":        "🎾 Roland Garros ATP",
    "mma_mixed_martial_arts":        "🥊 MMA/UFC",
}

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("rockai")

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="RockAI API", version="3.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
security = HTTPBearer()

# ── Cache mémoire ──────────────────────────────────────────────────────────────
_cache: Dict[str, Any] = {}

def cache_set(key: str, val: Any, ttl: int):
    _cache[key] = {"v": val, "exp": time.time() + ttl}

def cache_get(key: str) -> Optional[Any]:
    e = _cache.get(key)
    if e and e["exp"] > time.time(): return e["v"]
    _cache.pop(key, None); return None

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════════════
def get_db():
    c = sqlite3.connect(DATABASE_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = get_db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        email         TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name     TEXT,
        plan          TEXT DEFAULT 'free',
        bankroll      REAL DEFAULT 1000,
        created_at    TEXT DEFAULT (datetime('now')),
        last_login    TEXT
    );
    CREATE TABLE IF NOT EXISTS bets (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER NOT NULL,
        match_id       TEXT NOT NULL,
        sport          TEXT,
        team_home      TEXT,
        team_away      TEXT,
        bet_on         TEXT,
        bet_label      TEXT,
        bookmaker      TEXT,
        odds           REAL,
        fair_odds      REAL,
        ev             REAL,
        kelly_pct      REAL,
        stake          REAL,
        status         TEXT DEFAULT 'pending',
        result         TEXT,
        profit         REAL DEFAULT 0,
        placed_at      TEXT DEFAULT (datetime('now')),
        match_date     TEXT
    );
    """)
    c.commit(); c.close()
    logger.info("✓ DB ready")

# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class BetCreate(BaseModel):
    match_id:  str
    bet_on:    str    # "home" | "draw" | "away"
    bookmaker: str
    odds:      float
    stake:     float

class BetSettle(BaseModel):
    result: str   # "won" | "lost"

def hash_pw(pw): return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
def verify_pw(pw, h): return bcrypt.checkpw(pw.encode(), h.encode())
def make_token(email):
    exp = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": email, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

async def get_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        p = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email = p["sub"]
    except:
        raise HTTPException(401, "Token invalide")
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    db.close()
    if not row: raise HTTPException(401, "Utilisateur introuvable")
    return dict(row)

# ══════════════════════════════════════════════════════════════════════════════
# ⭐ MÉTHODE PINNACLE — CŒUR DU SYSTÈME
# ══════════════════════════════════════════════════════════════════════════════

def extract_odds_by_bookmaker(event: dict) -> Dict[str, Dict]:
    """
    Pour un événement, retourne les cotes par bookmaker :
    { "pinnacle": {"home": 1.85, "draw": 3.40, "away": 4.10},
      "bet365":   {"home": 1.90, "draw": 3.50, "away": 4.20}, ... }
    """
    home_team = event["home_team"]
    away_team = event["away_team"]
    result = {}

    for bk in event.get("bookmakers", []):
        bk_key = bk["key"].lower()
        for mkt in bk.get("markets", []):
            if mkt["key"] != "h2h":
                continue
            odds = {}
            for o in mkt["outcomes"]:
                if o["name"] == home_team:
                    odds["home"] = float(o["price"])
                elif o["name"] == away_team:
                    odds["away"] = float(o["price"])
                elif o["name"] == "Draw":
                    odds["draw"] = float(o["price"])
            if "home" in odds and "away" in odds:
                result[bk_key] = odds
    return result

def calc_fair_odds_pinnacle(pinnacle_odds: Dict) -> Dict[str, float]:
    """
    Retire la marge de Pinnacle (~2%) pour obtenir les "fair odds".
    C'est notre référence de la vraie probabilité du match.

    Exemple :
      Pinnacle : home=1.85  draw=3.40  away=4.10
      Marge Pinnacle ≈ 1/1.85 + 1/3.40 + 1/4.10 - 1 = 2.1%
      Fair odds home = 1.85 × (1 + marge) = 1.89
    """
    h = pinnacle_odds.get("home", 0)
    d = pinnacle_odds.get("draw")
    a = pinnacle_odds.get("away", 0)

    if h < 1.01 or a < 1.01:
        return {}

    # Calcule la marge réelle de Pinnacle
    implied = 1/h + (1/d if d else 0) + 1/a
    margin = implied - 1  # ex: 0.021 pour 2.1%

    # Fair odds = cote Pinnacle corrigée de sa marge
    fair = {
        "home": round(h * (1 + margin), 3),
        "away": round(a * (1 + margin), 3),
    }
    if d:
        fair["draw"] = round(d * (1 + margin), 3)

    return fair

def calc_ev_vs_pinnacle(bk_odds: float, fair_odds: float) -> float:
    """
    EV = (cote_bookmaker / fair_odds) - 1

    Exemple :
      Bet365 propose 1.95 sur home
      Fair odds Pinnacle = 1.89
      EV = (1.95 / 1.89) - 1 = +3.17% ✅ VALUE BET

    Si EV > 0 → le bookmaker paie trop cher → value bet
    Si EV < 0 → le bookmaker a moins bien prix → pas intéressant
    """
    if fair_odds < 1.01 or bk_odds < 1.01:
        return -1.0
    return round((bk_odds / fair_odds) - 1, 4)

def calc_kelly(ev: float, odds: float, fraction: float = 0.5) -> float:
    """
    Critère de Kelly (demi-Kelly par défaut = plus prudent)

    Kelly = ((odds - 1) × prob - (1 - prob)) / (odds - 1)
    où prob = (ev + 1) / odds (notre estimation de la vraie proba)

    fraction = 0.5 → demi-Kelly (recommandé pour limiter la variance)
    """
    if ev <= 0 or odds <= 1.01:
        return 0.0
    prob = (ev + 1) / odds
    b = odds - 1
    kelly = (b * prob - (1 - prob)) / b
    return round(max(0, kelly * fraction) * 100, 2)  # en %

def find_value_bets(event: dict, sport_key: str) -> List[Dict]:
    """
    Analyse un événement et retourne toutes les value bets trouvées.

    Algo :
    1. Extrait les cotes Pinnacle → calcule les fair odds
    2. Pour chaque autre bookmaker :
       - Compare leurs cotes contre les fair odds
       - Si EV > seuil → c'est une value bet
    3. Retourne la liste triée par EV décroissant
    """
    bk_odds = extract_odds_by_bookmaker(event)

    # Cherche Pinnacle (clé "pinnacle" dans l'API)
    pinnacle = bk_odds.get("pinnacle")
    if not pinnacle:
        # Fallback : utilise la moyenne des 3 meilleurs bookmakers comme référence
        sharp_bks = ["betfair", "betfair_ex_eu", "betfair_ex_uk", "matchbook",
                     "nordicbet", "unibet_eu", "williamhill"]
        for bk in sharp_bks:
            if bk in bk_odds:
                pinnacle = bk_odds[bk]
                break

    if not pinnacle:
        return []

    fair = calc_fair_odds_pinnacle(pinnacle)
    if not fair:
        return []

    home_team = event["home_team"]
    away_team = event["away_team"]
    label     = LEAGUES.get(sport_key, sport_key)
    value_bets = []

    for bk_name, odds in bk_odds.items():
        if bk_name == "pinnacle":
            continue  # on compare les autres contre Pinnacle

        for side in ["home", "draw", "away"]:
            bk_price  = odds.get(side)
            fair_price = fair.get(side)

            if not bk_price or not fair_price:
                continue

            ev = calc_ev_vs_pinnacle(bk_price, fair_price)

            if ev < EV_MIN_DISPLAY:
                continue  # pas assez intéressant

            kelly_pct = calc_kelly(ev, bk_price)

            # Label lisible du pari
            if side == "home":
                bet_label = f"Victoire {home_team}"
            elif side == "away":
                bet_label = f"Victoire {away_team}"
            else:
                bet_label = "Match nul"

            value_bets.append({
                "match_id":      event["id"],
                "sport_key":     sport_key,
                "league":        label,
                "team_home":     home_team,
                "team_away":     away_team,
                "commence_time": event["commence_time"],
                "bet_on":        side,
                "bet_label":     bet_label,
                "bookmaker":     bk_name.replace("_", " ").title(),
                "bookmaker_key": bk_name,
                "odds":          bk_price,
                "fair_odds":     fair_price,
                "pinnacle_odds": pinnacle.get(side),
                "ev":            ev,
                "ev_pct":        round(ev * 100, 2),
                "kelly_pct":     kelly_pct,
                "is_strong":     ev >= EV_MIN_ALERT,
                # Calcul de mise recommandée pour différentes bankrolls
                "stake_100":     round(100  * kelly_pct / 100, 2),
                "stake_500":     round(500  * kelly_pct / 100, 2),
                "stake_1000":    round(1000 * kelly_pct / 100, 2),
            })

    # Trie : meilleur EV en premier
    value_bets.sort(key=lambda x: x["ev"], reverse=True)
    return value_bets

# ══════════════════════════════════════════════════════════════════════════════
# THE ODDS API — FETCH
# ══════════════════════════════════════════════════════════════════════════════

async def fetch_league(session: aiohttp.ClientSession, sport_key: str) -> List[Dict]:
    """Fetch les cotes pour une ligue — TOUS les bookmakers en une requête"""
    ck = f"raw:{sport_key}"
    cached = cache_get(ck)
    if cached is not None:
        return cached

    if not ODDS_API_KEY:
        return _demo_events(sport_key)

    # On demande TOUS les bookmakers (pas de filtre) pour avoir Pinnacle + les autres
    url = (
        f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
        f"?apiKey={ODDS_API_KEY}"
        f"&regions=eu,uk"           # bookmakers européens + UK (Pinnacle est là)
        f"&markets=h2h"             # 1X2 pour commencer
        f"&oddsFormat=decimal"
        f"&dateFormat=iso"
    )

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=12)) as r:
            remaining = r.headers.get("x-requests-remaining", "?")
            logger.info(f"OddsAPI [{sport_key}] → {r.status} | quota restant: {remaining}")

            if r.status == 401:
                raise HTTPException(500, "Clé OddsAPI invalide")
            if r.status == 422:
                return []  # sport hors saison
            if r.status == 429:
                logger.warning("Rate limit OddsAPI !")
                await asyncio.sleep(3)
                return []
            if r.status != 200:
                return []

            data = await r.json()
            cache_set(ck, data, ODDS_CACHE_SEC)
            return data

    except asyncio.TimeoutError:
        logger.error(f"Timeout: {sport_key}")
        return []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fetch error {sport_key}: {e}")
        return []

def _demo_events(sport_key: str) -> List[Dict]:
    """Données de démo réalistes avec Pinnacle pour tester sans clé API"""
    t = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    label = LEAGUES.get(sport_key, sport_key)

    demos = {
        "soccer_epl": [
            {
                "id": "demo_ars_che", "sport_key": sport_key,
                "home_team": "Arsenal", "away_team": "Chelsea",
                "commence_time": t, "bookmakers": [
                    {"key": "pinnacle", "title": "Pinnacle", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Arsenal", "price": 1.87},
                        {"name": "Chelsea", "price": 4.15},
                        {"name": "Draw",    "price": 3.42},
                    ]}]},
                    {"key": "bet365", "title": "Bet365", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Arsenal", "price": 1.95},   # ← plus haut que Pinnacle → EV+
                        {"name": "Chelsea", "price": 4.00},
                        {"name": "Draw",    "price": 3.40},
                    ]}]},
                    {"key": "williamhill", "title": "William Hill", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Arsenal", "price": 1.91},
                        {"name": "Chelsea", "price": 4.20},   # ← EV+ sur Chelsea
                        {"name": "Draw",    "price": 3.35},
                    ]}]},
                    {"key": "unibet_eu", "title": "Unibet", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Arsenal", "price": 1.89},
                        {"name": "Chelsea", "price": 4.10},
                        {"name": "Draw",    "price": 3.50},   # ← EV+ sur nul
                    ]}]},
                ]
            },
            {
                "id": "demo_mci_liv", "sport_key": sport_key,
                "home_team": "Man City", "away_team": "Liverpool",
                "commence_time": t, "bookmakers": [
                    {"key": "pinnacle", "title": "Pinnacle", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Man City",   "price": 1.95},
                        {"name": "Liverpool",  "price": 3.90},
                        {"name": "Draw",       "price": 3.55},
                    ]}]},
                    {"key": "bet365", "title": "Bet365", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Man City",  "price": 1.93},
                        {"name": "Liverpool", "price": 3.95},
                        {"name": "Draw",      "price": 3.50},
                    ]}]},
                    {"key": "bwin", "title": "Bwin", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Man City",  "price": 2.05},  # ← EV+ fort !
                        {"name": "Liverpool", "price": 3.80},
                        {"name": "Draw",      "price": 3.45},
                    ]}]},
                ]
            },
        ],
        "soccer_france_ligue_one": [
            {
                "id": "demo_psg_lyo", "sport_key": sport_key,
                "home_team": "PSG", "away_team": "Lyon",
                "commence_time": t, "bookmakers": [
                    {"key": "pinnacle", "title": "Pinnacle", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "PSG",  "price": 1.38},
                        {"name": "Lyon", "price": 7.80},
                        {"name": "Draw", "price": 4.65},
                    ]}]},
                    {"key": "winamax", "title": "Winamax", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "PSG",  "price": 1.36},
                        {"name": "Lyon", "price": 8.25},  # ← EV+ Lyon
                        {"name": "Draw", "price": 4.80},
                    ]}]},
                    {"key": "unibet_eu", "title": "Unibet", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "PSG",  "price": 1.40},  # ← EV+ PSG
                        {"name": "Lyon", "price": 7.50},
                        {"name": "Draw", "price": 4.70},
                    ]}]},
                ]
            },
        ],
        "basketball_nba": [
            {
                "id": "demo_lal_bos", "sport_key": sport_key,
                "home_team": "Lakers", "away_team": "Celtics",
                "commence_time": t, "bookmakers": [
                    {"key": "pinnacle", "title": "Pinnacle", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Lakers",  "price": 2.10},
                        {"name": "Celtics", "price": 1.78},
                    ]}]},
                    {"key": "bet365", "title": "Bet365", "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Lakers",  "price": 2.20},  # ← EV+ Lakers
                        {"name": "Celtics", "price": 1.75},
                    ]}]},
                ]
            },
        ],
    }

    # Complète les autres ligues avec des matchs génériques
    for sk in LEAGUES:
        if sk not in demos:
            demos[sk] = []

    return demos.get(sport_key, [])

# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL — construit la réponse agenda
# ══════════════════════════════════════════════════════════════════════════════

async def get_all_matches_with_ev(leagues: List[str]) -> List[Dict]:
    """
    Fetch tous les matchs et calcule les value bets via méthode Pinnacle.
    Retourne une liste de matchs enrichis avec leurs value bets.
    """
    ck = f"agenda:{','.join(sorted(leagues))}"
    cached = cache_get(ck)
    if cached is not None:
        return cached

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_league(session, sk) for sk in leagues]
        all_events = await asyncio.gather(*tasks)

    matches = []
    for i, events in enumerate(all_events):
        sport_key = leagues[i]
        for event in events:
            value_bets = find_value_bets(event, sport_key)

            # Meilleure value bet du match (pour affichage résumé)
            best_vb = value_bets[0] if value_bets else None

            # Cotes de référence (Pinnacle si dispo)
            bk_data = extract_odds_by_bookmaker(event)
            pin = bk_data.get("pinnacle", {})
            # Sinon première dispo
            if not pin and bk_data:
                pin = next(iter(bk_data.values()))

            match = {
                "match_id":      event["id"],
                "sport_key":     sport_key,
                "league":        LEAGUES.get(sport_key, sport_key),
                "team_home":     event["home_team"],
                "team_away":     event["away_team"],
                "commence_time": event["commence_time"],
                # Cotes Pinnacle (référence)
                "odds_home":     pin.get("home"),
                "odds_draw":     pin.get("draw"),
                "odds_away":     pin.get("away"),
                # Résumé value bet
                "has_value":     len(value_bets) > 0,
                "value_count":   len(value_bets),
                "best_ev":       best_vb["ev"] if best_vb else None,
                "best_ev_pct":   best_vb["ev_pct"] if best_vb else None,
                "best_bet_label":best_vb["bet_label"] if best_vb else None,
                "best_bookmaker":best_vb["bookmaker"] if best_vb else None,
                "best_odds":     best_vb["odds"] if best_vb else None,
                "best_kelly":    best_vb["kelly_pct"] if best_vb else None,
                "is_strong":     best_vb["is_strong"] if best_vb else False,
                # Toutes les value bets du match
                "value_bets":    value_bets,
            }
            matches.append(match)

    # Tri : value bets forts d'abord, puis par heure
    matches.sort(key=lambda m: (
        0 if m["is_strong"] else (1 if m["has_value"] else 2),
        m["commence_time"]
    ))

    cache_set(ck, matches, ODDS_CACHE_SEC)
    return matches

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    init_db()
    logger.info("🚀 RockAI v3.0 — Méthode Pinnacle activée")

@app.get("/")
async def root():
    return {
        "service": "RockAI API", "version": "3.0.0",
        "method": "Pinnacle-based value bet detection",
        "integrations": {
            "odds_api":  "live" if ODDS_API_KEY else "demo",
            "anthropic": "ok"   if ANTHROPIC_API_KEY else "missing",
        }
    }

# ── Auth ───────────────────────────────────────────────────────────────────────
@app.post("/auth/register")
async def register(b: UserRegister):
    db = get_db()
    if db.execute("SELECT id FROM users WHERE email=?", (b.email,)).fetchone():
        db.close(); raise HTTPException(400, "Email déjà utilisé")
    db.execute("INSERT INTO users (email,password_hash,full_name) VALUES (?,?,?)",
               (b.email, hash_pw(b.password), b.full_name))
    db.commit(); db.close()
    return {"access_token": make_token(b.email), "token_type": "bearer"}

@app.post("/auth/login")
async def login(b: UserLogin):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE email=?", (b.email,)).fetchone()
    if not row or not verify_pw(b.password, row["password_hash"]):
        db.close(); raise HTTPException(401, "Email ou mot de passe incorrect")
    db.execute("UPDATE users SET last_login=datetime('now') WHERE email=?", (b.email,))
    db.commit(); db.close()
    return {"access_token": make_token(b.email), "token_type": "bearer"}

@app.get("/user/me")
async def me(user=Depends(get_user)):
    return user

# ── Matches / Agenda ───────────────────────────────────────────────────────────
@app.get("/matches")
async def get_matches(
    leagues:    Optional[str] = None,
    value_only: bool = False,
    strong_only: bool = False,
    user=Depends(get_user)
):
    """
    Retourne tous les matchs avec détection de value bets (méthode Pinnacle).
    Chaque match contient :
    - Les cotes Pinnacle (référence)
    - La meilleure value bet trouvée (bookmaker, cote, EV%, mise Kelly)
    - La liste complète de toutes les value bets du match
    """
    target = [l.strip() for l in leagues.split(",")] if leagues else list(LEAGUES.keys())
    # Limite aux ligues connues
    target = [l for l in target if l in LEAGUES]

    matches = await get_all_matches_with_ev(target)

    if strong_only:
        matches = [m for m in matches if m["is_strong"]]
    elif value_only:
        matches = [m for m in matches if m["has_value"]]

    return {
        "count":        len(matches),
        "value_count":  sum(1 for m in matches if m["has_value"]),
        "strong_count": sum(1 for m in matches if m["is_strong"]),
        "mode":         "live" if ODDS_API_KEY else "demo",
        "updated_at":   datetime.now(timezone.utc).isoformat(),
        "matches":      matches,
    }

@app.get("/matches/{match_id}")
async def get_match(match_id: str, user=Depends(get_user)):
    """Détails complets d'un match avec toutes ses value bets"""
    matches = await get_all_matches_with_ev(list(LEAGUES.keys()))
    match = next((m for m in matches if m["match_id"] == match_id), None)
    if not match:
        raise HTTPException(404, "Match introuvable")
    return match

# ── Bets ───────────────────────────────────────────────────────────────────────
@app.post("/bets")
async def place_bet(b: BetCreate, user=Depends(get_user)):
    """Enregistre un pari placé"""
    # Retrouve le match pour les infos
    matches = await get_all_matches_with_ev(list(LEAGUES.keys()))
    match = next((m for m in matches if m["match_id"] == b.match_id), None)

    # Cherche la value bet correspondante
    vb = None
    if match:
        vb = next((v for v in match["value_bets"]
                   if v["bet_on"] == b.bet_on and v["bookmaker_key"] == b.bookmaker.lower().replace(" ","_")),
                  None)
        # Fallback : cherche par bookmaker
        if not vb:
            vb = next((v for v in match["value_bets"] if v["bet_on"] == b.bet_on), None)

    ev = vb["ev"] if vb else 0
    fair_odds = vb["fair_odds"] if vb else None
    kelly = calc_kelly(ev, b.odds)

    db = get_db()
    cur = db.execute("""
        INSERT INTO bets
        (user_id, match_id, sport, team_home, team_away, bet_on, bet_label,
         bookmaker, odds, fair_odds, ev, kelly_pct, stake, match_date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        user["id"], b.match_id,
        match["sport_key"] if match else "",
        match["team_home"] if match else "",
        match["team_away"] if match else "",
        b.bet_on,
        vb["bet_label"] if vb else b.bet_on,
        b.bookmaker, b.odds, fair_odds, ev, kelly, b.stake,
        match["commence_time"] if match else None
    ))
    db.commit()
    bid = cur.lastrowid
    db.close()

    return {
        "bet_id":           bid,
        "ev_pct":           round(ev * 100, 2),
        "kelly_pct":        kelly,
        "suggested_stake":  round(user["bankroll"] * kelly / 100, 2),
        "potential_return": round(b.stake * b.odds, 2),
        "potential_profit": round(b.stake * (b.odds - 1), 2),
    }

@app.patch("/bets/{bet_id}")
async def settle_bet(bet_id: int, b: BetSettle, user=Depends(get_user)):
    """Clôture un pari avec son résultat"""
    db = get_db()
    row = db.execute("SELECT * FROM bets WHERE id=? AND user_id=?",
                     (bet_id, user["id"])).fetchone()
    if not row:
        db.close(); raise HTTPException(404, "Pari introuvable")
    row = dict(row)
    profit = round(row["stake"] * (row["odds"] - 1), 2) if b.result == "won" else -row["stake"]
    db.execute("UPDATE bets SET result=?,profit=?,status='settled' WHERE id=?",
               (b.result, profit, bet_id))
    db.commit(); db.close()
    return {"bet_id": bet_id, "result": b.result, "profit": profit}

@app.get("/bets")
async def get_bets(limit: int = 50, user=Depends(get_user)):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM bets WHERE user_id=? ORDER BY placed_at DESC LIMIT ?",
        (user["id"], limit)
    ).fetchall()
    db.close()
    return {"bets": [dict(r) for r in rows]}

# ── Stats ──────────────────────────────────────────────────────────────────────
@app.get("/stats")
async def get_stats(user=Depends(get_user)):
    db = get_db()
    o = dict(db.execute("""
        SELECT COUNT(*) total,
               SUM(result='won') won, SUM(result='lost') lost,
               SUM(status='pending') pending,
               COALESCE(SUM(profit),0) profit,
               COALESCE(SUM(stake),0)  staked,
               COALESCE(AVG(CASE WHEN ev>0 THEN ev END),0) avg_ev
        FROM bets WHERE user_id=?
    """, (user["id"],)).fetchone())

    monthly = [dict(r) for r in db.execute("""
        SELECT strftime('%Y-%m',placed_at) month,
               COUNT(*) bets, SUM(result='won') wins,
               COALESCE(SUM(profit),0) profit
        FROM bets WHERE user_id=?
        AND placed_at > date('now','-12 months')
        GROUP BY month ORDER BY month
    """, (user["id"],)).fetchall()]

    by_sport = [dict(r) for r in db.execute("""
        SELECT sport, COUNT(*) bets, SUM(result='won') wins,
               COALESCE(SUM(profit),0) profit
        FROM bets WHERE user_id=? GROUP BY sport ORDER BY profit DESC
    """, (user["id"],)).fetchall()]

    db.close()

    settled = (o["won"] or 0) + (o["lost"] or 0)
    roi = round((o["profit"]/o["staked"])*100, 1) if o["staked"] > 0 else 0

    # Projection long terme (simulation Kelly)
    bankroll = user["bankroll"] or 1000
    avg_ev   = o["avg_ev"] or 0.05
    avg_kelly = 2.0  # % de bankroll moyen
    projected_500 = round(bankroll * ((1 + avg_kelly/100 * avg_ev) ** 500 - 1), 0)

    return {
        "total_bets":    o["total"] or 0,
        "won":           o["won"] or 0,
        "lost":          o["lost"] or 0,
        "pending":       o["pending"] or 0,
        "win_rate":      round((o["won"] or 0)/settled*100, 1) if settled else 0,
        "roi":           roi,
        "total_profit":  round(o["profit"], 2),
        "total_staked":  round(o["staked"], 2),
        "avg_ev_pct":    round(o["avg_ev"]*100, 2),
        "bankroll":      bankroll,
        "projection_500_bets": projected_500,
        "monthly":       monthly,
        "by_sport":      by_sport,
    }

@app.get("/leagues")
async def get_leagues():
    return {"leagues": [{"key": k, "label": v} for k, v in LEAGUES.items()]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app",
                host=os.getenv("HOST", "0.0.0.0"),
                port=int(os.getenv("PORT", 8000)),
                reload=True)
