#!/usr/bin/env python3
"""
RockAI Backend v2.0 - Sports Betting AI Platform
═══════════════════════════════════════════════════
Intégrations :
  - The Odds API  → cotes multi-bookmakers en temps réel
  - API-Football  → statistiques, forme, xG, compos
  - Anthropic     → analyse IA et calcul de value bet
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import jwt
import bcrypt
import sqlite3
import os
import time
from datetime import datetime, timedelta, timezone
import asyncio
import aiohttp
import anthropic
from dotenv import load_dotenv
import logging
import json

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
SECRET_KEY          = os.getenv("SECRET_KEY", "change-this-in-production!")
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
ODDS_API_KEY        = os.getenv("ODDS_API_KEY", "")       # the-odds-api.com
API_FOOTBALL_KEY    = os.getenv("API_FOOTBALL_KEY", "")   # RapidAPI → api-football
DATABASE_PATH       = os.getenv("DATABASE_PATH", "rockai.db")
ALGORITHM           = "HS256"
TOKEN_EXPIRE_DAYS   = 30

ODDS_CACHE_SECONDS     = 300    # 5 min
STATS_CACHE_SECONDS    = 3600   # 1 h
ANALYSIS_CACHE_SECONDS = 1800   # 30 min

SUPPORTED_LEAGUES = {
    "soccer_france_ligue_one":      "🇫🇷 Ligue 1",
    "soccer_epl":                   "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League",
    "soccer_spain_la_liga":         "🇪🇸 La Liga",
    "soccer_germany_bundesliga":    "🇩🇪 Bundesliga",
    "soccer_italy_serie_a":         "🇮🇹 Serie A",
    "soccer_uefa_champs_league":    "🏆 Champions League",
    "soccer_uefa_europa_league":    "⚽ Europa League",
}

AFL_LEAGUE_IDS = {
    "soccer_france_ligue_one":   61,
    "soccer_epl":                39,
    "soccer_spain_la_liga":      140,
    "soccer_germany_bundesliga": 78,
    "soccer_italy_serie_a":      135,
    "soccer_uefa_champs_league": 2,
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("rockai")

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="RockAI API", version="2.0.0", docs_url="/docs")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

security = HTTPBearer()
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Cache mémoire ──────────────────────────────────────────────────────────────
_cache: Dict[str, Dict] = {}

def cache_set(key: str, value: Any, ttl: int):
    _cache[key] = {"value": value, "expires": time.time() + ttl}

def cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry and entry["expires"] > time.time():
        return entry["value"]
    _cache.pop(key, None)
    return None

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name     TEXT,
            plan          TEXT DEFAULT 'free',
            credits       INTEGER DEFAULT 50,
            created_at    TEXT DEFAULT (datetime('now')),
            last_login    TEXT
        )""")
    c.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            match_id       TEXT NOT NULL,
            team_home      TEXT NOT NULL,
            team_away      TEXT NOT NULL,
            league         TEXT NOT NULL,
            bet_type       TEXT NOT NULL,
            odds           REAL NOT NULL,
            stake          REAL NOT NULL,
            expected_value REAL NOT NULL,
            kelly_fraction REAL,
            status         TEXT DEFAULT 'pending',
            result         TEXT,
            profit         REAL DEFAULT 0,
            placed_at      TEXT DEFAULT (datetime('now')),
            match_date     TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )""")
    c.execute("""
        CREATE TABLE IF NOT EXISTS match_cache (
            match_id       TEXT PRIMARY KEY,
            sport_key      TEXT,
            team_home      TEXT,
            team_away      TEXT,
            league_label   TEXT,
            commence_time  TEXT,
            odds_home      REAL,
            odds_draw      REAL,
            odds_away      REAL,
            best_bookmaker TEXT,
            prob_home      REAL,
            prob_draw      REAL,
            prob_away      REAL,
            ev_home        REAL,
            ev_draw        REAL,
            ev_away        REAL,
            best_bet       TEXT,
            kelly_fraction REAL,
            confidence     REAL,
            ai_analysis    TEXT,
            stats_json     TEXT,
            form_home      TEXT,
            form_away      TEXT,
            cached_at      TEXT DEFAULT (datetime('now'))
        )""")
    conn.commit()
    conn.close()
    logger.info("✓ Database ready")

# ══════════════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════════════

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class BetCreate(BaseModel):
    match_id: str
    bet_type: str
    stake:    float

class BetUpdate(BaseModel):
    result: str
    profit: float

# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())

def create_token(email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": email, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

async def current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(401, "Token invalide ou expiré")
    conn = get_db()
    row = conn.execute(
        "SELECT id, email, full_name, plan, credits FROM users WHERE email=?", (email,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(401, "Utilisateur introuvable")
    return dict(row)

# ══════════════════════════════════════════════════════════════════════════════
# THE ODDS API
# ══════════════════════════════════════════════════════════════════════════════

async def fetch_odds_for_league(session: aiohttp.ClientSession, sport_key: str) -> List[Dict]:
    ck = f"odds:{sport_key}"
    cached = cache_get(ck)
    if cached is not None:
        return cached

    if not ODDS_API_KEY:
        data = _demo_odds(sport_key)
        cache_set(ck, data, ODDS_CACHE_SECONDS)
        return data

    url = (
        f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
        f"?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal&dateFormat=iso"
    )
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            remaining = r.headers.get("x-requests-remaining", "?")
            logger.info(f"OddsAPI [{sport_key}] remaining={remaining}")
            if r.status == 401:
                raise HTTPException(500, "Clé OddsAPI invalide")
            if r.status != 200:
                logger.error(f"OddsAPI {r.status} for {sport_key}")
                return []
            raw = await r.json()
            parsed = _parse_odds(raw, sport_key)
            cache_set(ck, parsed, ODDS_CACHE_SECONDS)
            return parsed
    except asyncio.TimeoutError:
        logger.error(f"OddsAPI timeout {sport_key}")
        return []

def _parse_odds(raw: List[Dict], sport_key: str) -> List[Dict]:
    label = SUPPORTED_LEAGUES.get(sport_key, sport_key)
    result = []
    for event in raw:
        if not event.get("bookmakers"):
            continue
        ht, at = event["home_team"], event["away_team"]
        best_h = best_d = best_a = 0.0
        best_bk = ""
        for bk in event["bookmakers"]:
            for mkt in bk.get("markets", []):
                if mkt["key"] != "h2h":
                    continue
                for o in mkt["outcomes"]:
                    p = float(o["price"])
                    if o["name"] == ht and p > best_h:
                        best_h, best_bk = p, bk["title"]
                    elif o["name"] == "Draw" and p > best_d:
                        best_d = p
                    elif o["name"] == at and p > best_a:
                        best_a = p
        if best_h < 1.01 or best_a < 1.01:
            continue
        result.append({
            "match_id":       event["id"],
            "sport_key":      sport_key,
            "team_home":      ht,
            "team_away":      at,
            "league_label":   label,
            "commence_time":  event["commence_time"],
            "odds_home":      round(best_h, 2),
            "odds_draw":      round(best_d, 2) if best_d > 1 else None,
            "odds_away":      round(best_a, 2),
            "best_bookmaker": best_bk,
        })
    return result

def _demo_odds(sport_key: str) -> List[Dict]:
    label = SUPPORTED_LEAGUES.get(sport_key, sport_key)
    base_time = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    demos = {
        "soccer_epl": [
            {"match_id": "demo_ars_che", "team_home": "Arsenal",   "team_away": "Chelsea",    "odds_home": 1.85, "odds_draw": 3.40, "odds_away": 4.20, "best_bookmaker": "Pinnacle"},
            {"match_id": "demo_mci_liv", "team_home": "Man City",  "team_away": "Liverpool",  "odds_home": 1.90, "odds_draw": 3.60, "odds_away": 4.00, "best_bookmaker": "Bet365"},
            {"match_id": "demo_tot_mun", "team_home": "Tottenham", "team_away": "Man United", "odds_home": 2.05, "odds_draw": 3.40, "odds_away": 3.55, "best_bookmaker": "William Hill"},
        ],
        "soccer_france_ligue_one": [
            {"match_id": "demo_psg_lyo", "team_home": "PSG",       "team_away": "Lyon",    "odds_home": 1.35, "odds_draw": 4.50, "odds_away": 8.00, "best_bookmaker": "Unibet"},
            {"match_id": "demo_om_asm",  "team_home": "Marseille", "team_away": "Monaco",  "odds_home": 2.10, "odds_draw": 3.30, "odds_away": 3.50, "best_bookmaker": "Winamax"},
        ],
        "soccer_germany_bundesliga": [
            {"match_id": "demo_bay_bvb", "team_home": "Bayern",    "team_away": "Dortmund", "odds_home": 1.55, "odds_draw": 4.00, "odds_away": 5.50, "best_bookmaker": "Bwin"},
        ],
        "soccer_spain_la_liga": [
            {"match_id": "demo_rma_atm", "team_home": "Real Madrid", "team_away": "Atletico", "odds_home": 1.80, "odds_draw": 3.60, "odds_away": 4.50, "best_bookmaker": "Bet365"},
        ],
        "soccer_italy_serie_a": [
            {"match_id": "demo_int_juve", "team_home": "Inter", "team_away": "Juventus", "odds_home": 2.00, "odds_draw": 3.30, "odds_away": 3.75, "best_bookmaker": "Snai"},
        ],
        "soccer_uefa_champs_league": [
            {"match_id": "demo_mci_ben", "team_home": "Man City", "team_away": "Benfica", "odds_home": 1.45, "odds_draw": 4.20, "odds_away": 7.00, "best_bookmaker": "Pinnacle"},
        ],
    }
    return [
        {**m, "sport_key": sport_key, "league_label": label, "commence_time": base_time}
        for m in demos.get(sport_key, [])
    ]

# ══════════════════════════════════════════════════════════════════════════════
# API-FOOTBALL
# ══════════════════════════════════════════════════════════════════════════════

async def fetch_team_stats(session: aiohttp.ClientSession, team_name: str, sport_key: str) -> Dict:
    ck = f"stats:{sport_key}:{team_name}"
    cached = cache_get(ck)
    if cached:
        return cached

    if not API_FOOTBALL_KEY:
        return _demo_stats(team_name)

    league_id = AFL_LEAGUE_IDS.get(sport_key)
    if not league_id:
        return _demo_stats(team_name)

    season = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
    headers = {
        "X-RapidAPI-Key":  API_FOOTBALL_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    # Cherche l'ID équipe
    try:
        async with session.get(
            f"https://api-football-v1.p.rapidapi.com/v3/teams?name={team_name}&league={league_id}&season={season}",
            headers=headers, timeout=aiohttp.ClientTimeout(total=8)
        ) as r:
            if r.status != 200:
                return _demo_stats(team_name)
            data = await r.json()
            teams = data.get("response", [])
            if not teams:
                return _demo_stats(team_name)
            team_id = teams[0]["team"]["id"]
    except Exception as e:
        logger.error(f"API-Football team search: {e}")
        return _demo_stats(team_name)

    # Stats de la saison
    try:
        async with session.get(
            f"https://api-football-v1.p.rapidapi.com/v3/teams/statistics?league={league_id}&season={season}&team={team_id}",
            headers=headers, timeout=aiohttp.ClientTimeout(total=8)
        ) as r:
            if r.status != 200:
                return _demo_stats(team_name)
            data = await r.json()
            resp = data.get("response", {})
            fx   = resp.get("fixtures", {})
            gls  = resp.get("goals", {})
            form = resp.get("form", "")
            stats = {
                "team_name":     team_name,
                "played":        fx.get("played", {}).get("total", 0),
                "wins":          fx.get("wins", {}).get("total", 0),
                "draws":         fx.get("draws", {}).get("total", 0),
                "losses":        fx.get("losses", {}).get("total", 0),
                "goals_for":     gls.get("for", {}).get("average", {}).get("total", "?"),
                "goals_against": gls.get("against", {}).get("average", {}).get("total", "?"),
                "form_str":      form[-5:] if form else "N/A",
                "clean_sheets":  resp.get("clean_sheet", {}).get("total", 0),
            }
            cache_set(ck, stats, STATS_CACHE_SECONDS)
            return stats
    except Exception as e:
        logger.error(f"API-Football stats: {e}")
        return _demo_stats(team_name)

def _demo_stats(team_name: str) -> Dict:
    import random
    random.seed(hash(team_name) % 9999)
    w, d, l = random.randint(8,18), random.randint(3,8), random.randint(2,8)
    pool = ["W","W","W","D","L"]; random.shuffle(pool)
    return {
        "team_name": team_name, "played": w+d+l,
        "wins": w, "draws": d, "losses": l,
        "goals_for":     round(random.uniform(1.2, 2.5), 2),
        "goals_against": round(random.uniform(0.8, 1.8), 2),
        "form_str":      "".join(pool),
        "clean_sheets":  random.randint(4, 12),
        "_demo": True,
    }

# ══════════════════════════════════════════════════════════════════════════════
# IA — Claude
# ══════════════════════════════════════════════════════════════════════════════

def _remove_vig(h: float, d: Optional[float], a: float) -> Dict:
    ph = 1/h if h > 1 else 0
    pd = 1/d if d and d > 1 else 0
    pa = 1/a if a > 1 else 0
    total = ph + pd + pa
    if total <= 0:
        return {"home": 1/3, "draw": 1/3, "away": 1/3}
    return {"home": round(ph/total, 4), "draw": round(pd/total, 4), "away": round(pa/total, 4)}

def _calc_ev(prob: float, odds: float) -> float:
    return round((prob * odds) - 1, 4)

def _kelly(ev: float, odds: float) -> float:
    if ev <= 0 or odds <= 1:
        return 0.0
    b = odds - 1
    p = (ev + 1) / odds
    q = 1 - p
    k = (b * p - q) / b
    return round(max(0, k * 0.5), 4)  # demi-Kelly

async def analyze_with_claude(match: Dict, sh: Dict, sa: Dict) -> Dict:
    ck = f"ai:{match['match_id']}"
    cached = cache_get(ck)
    if cached:
        return cached

    bk = _remove_vig(match["odds_home"], match.get("odds_draw"), match["odds_away"])

    prompt = f"""Tu es expert en football et value betting (15 ans d'expérience).

MATCH : {match['team_home']} vs {match['team_away']} | {match['league_label']} | {match['commence_time'][:10]}
COTES : 1={match['odds_home']} X={match.get('odds_draw','N/D')} 2={match['odds_away']} (source: {match.get('best_bookmaker','?')})
PROB. IMPLICITES (sans marge) : {match['team_home']}={bk['home']:.1%} Nul={bk['draw']:.1%} {match['team_away']}={bk['away']:.1%}

STATS {match['team_home'].upper()} : {sh.get('played','?')}J V{sh.get('wins','?')} N{sh.get('draws','?')} D{sh.get('losses','?')} | buts: {sh.get('goals_for','?')}/{sh.get('goals_against','?')} | forme: {sh.get('form_str','?')} | CS: {sh.get('clean_sheets','?')}
STATS {match['team_away'].upper()} : {sa.get('played','?')}J V{sa.get('wins','?')} N{sa.get('draws','?')} D{sa.get('losses','?')} | buts: {sa.get('goals_for','?')}/{sa.get('goals_against','?')} | forme: {sa.get('form_str','?')} | CS: {sa.get('clean_sheets','?')}

Réponds UNIQUEMENT en JSON valide (sans markdown) :
{{"prob_home":0.XX,"prob_draw":0.XX,"prob_away":0.XX,"ev_home":0.XX,"ev_draw":0.XX,"ev_away":0.XX,"best_bet":"home|draw|away|none","confidence":0.XX,"analysis":"..."}}

EV = (ta_prob × cote) - 1. best_bet = EV le plus élevé si > 0, sinon "none". Analysis en français, 3 phrases max."""

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1][4:] if parts[1].startswith("json") else parts[1]
        result = json.loads(raw)
        cache_set(ck, result, ANALYSIS_CACHE_SECONDS)
        return result
    except Exception as e:
        logger.error(f"Claude error: {e}")
        return {
            "prob_home": bk["home"], "prob_draw": bk["draw"], "prob_away": bk["away"],
            "ev_home": 0.0, "ev_draw": 0.0, "ev_away": 0.0,
            "best_bet": "none", "confidence": 0.2,
            "analysis": "Analyse indisponible — vérifiez la clé Anthropic."
        }

# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE COMPLET
# ══════════════════════════════════════════════════════════════════════════════

async def full_analysis(match: Dict) -> Dict:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM match_cache WHERE match_id=? AND cached_at > datetime('now',?)",
        (match["match_id"], f"-{ANALYSIS_CACHE_SECONDS} seconds")
    ).fetchone()
    if row:
        conn.close()
        return dict(row)

    async with aiohttp.ClientSession() as session:
        sh, sa = await asyncio.gather(
            fetch_team_stats(session, match["team_home"], match["sport_key"]),
            fetch_team_stats(session, match["team_away"], match["sport_key"])
        )
        ai = await analyze_with_claude(match, sh, sa)

    od = match.get("odds_draw") or 3.5
    ev_h = _calc_ev(ai["prob_home"], match["odds_home"])
    ev_d = _calc_ev(ai["prob_draw"], od)
    ev_a = _calc_ev(ai["prob_away"], match["odds_away"])

    bb = ai.get("best_bet", "none")
    best_odds = {"home": match["odds_home"], "draw": od, "away": match["odds_away"]}.get(bb, 1)
    best_ev   = {"home": ev_h, "draw": ev_d, "away": ev_a}.get(bb, 0)
    kelly     = _kelly(best_ev, best_odds)

    result = {
        **match,
        "prob_home": ai["prob_home"], "prob_draw": ai["prob_draw"], "prob_away": ai["prob_away"],
        "ev_home": ev_h, "ev_draw": ev_d, "ev_away": ev_a,
        "best_bet": bb, "kelly_fraction": kelly,
        "confidence": ai["confidence"], "ai_analysis": ai["analysis"],
        "stats_json": json.dumps({"home": sh, "away": sa}),
        "form_home": sh.get("form_str", ""),
        "form_away": sa.get("form_str", ""),
    }

    try:
        conn.execute("""
            INSERT OR REPLACE INTO match_cache
            (match_id,sport_key,team_home,team_away,league_label,commence_time,
             odds_home,odds_draw,odds_away,best_bookmaker,
             prob_home,prob_draw,prob_away,ev_home,ev_draw,ev_away,
             best_bet,kelly_fraction,confidence,ai_analysis,
             stats_json,form_home,form_away)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            result["match_id"], result["sport_key"], result["team_home"], result["team_away"],
            result["league_label"], result["commence_time"],
            result["odds_home"], result.get("odds_draw"), result["odds_away"], result.get("best_bookmaker"),
            result["prob_home"], result["prob_draw"], result["prob_away"],
            result["ev_home"], result["ev_draw"], result["ev_away"],
            result["best_bet"], result["kelly_fraction"], result["confidence"],
            result["ai_analysis"], result["stats_json"], result["form_home"], result["form_away"]
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Cache save error: {e}")
    finally:
        conn.close()

    return result

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    init_database()
    logger.info("🚀 RockAI v2.0 — prêt")

@app.get("/", tags=["Status"])
async def root():
    return {
        "service": "RockAI API", "version": "2.0.0", "status": "running",
        "integrations": {
            "odds_api":    "live" if ODDS_API_KEY else "demo",
            "api_football":"live" if API_FOOTBALL_KEY else "demo",
            "anthropic":   "ok"   if ANTHROPIC_API_KEY else "missing",
        }
    }

# ── Auth ───────────────────────────────────────────────────────────────────────
@app.post("/auth/register", tags=["Auth"])
async def register(body: UserRegister):
    conn = get_db()
    if conn.execute("SELECT id FROM users WHERE email=?", (body.email,)).fetchone():
        conn.close()
        raise HTTPException(400, "Email déjà utilisé")
    conn.execute("INSERT INTO users (email,password_hash,full_name) VALUES (?,?,?)",
                 (body.email, hash_password(body.password), body.full_name))
    conn.commit(); conn.close()
    return {"access_token": create_token(body.email), "token_type": "bearer"}

@app.post("/auth/login", tags=["Auth"])
async def login(body: UserLogin):
    conn = get_db()
    row = conn.execute("SELECT email,password_hash FROM users WHERE email=?", (body.email,)).fetchone()
    if not row or not verify_password(body.password, row["password_hash"]):
        conn.close()
        raise HTTPException(401, "Email ou mot de passe incorrect")
    conn.execute("UPDATE users SET last_login=datetime('now') WHERE email=?", (body.email,))
    conn.commit(); conn.close()
    return {"access_token": create_token(body.email), "token_type": "bearer"}

@app.get("/user/me", tags=["User"])
async def me(user=Depends(current_user)):
    return user

# ── Matches ────────────────────────────────────────────────────────────────────
@app.get("/matches", tags=["Matches"])
async def get_matches(
    leagues:    Optional[str] = None,
    value_only: bool = False,
    user=Depends(current_user)
):
    target = [l.strip() for l in leagues.split(",")] if leagues else list(SUPPORTED_LEAGUES.keys())
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[fetch_odds_for_league(session, sk) for sk in target])
    all_matches = [m for sub in results for m in sub]

    conn = get_db()
    enriched = []
    for m in all_matches:
        row = conn.execute(
            "SELECT ev_home,ev_draw,ev_away,best_bet,kelly_fraction FROM match_cache WHERE match_id=?",
            (m["match_id"],)
        ).fetchone()
        if row:
            m.update(dict(row)); m["has_analysis"] = True
        else:
            m.update({"has_analysis": False, "best_bet": None, "ev_home": None})
        if value_only and m.get("best_bet") not in ("home","draw","away"):
            continue
        enriched.append(m)
    conn.close()

    enriched.sort(key=lambda x: (
        0 if x.get("best_bet") in ("home","draw","away") else 1,
        x["commence_time"]
    ))
    return {"count": len(enriched), "matches": enriched,
            "mode": "live" if ODDS_API_KEY else "demo"}

@app.post("/matches/{match_id}/analyze", tags=["Matches"])
async def analyze_match(match_id: str, user=Depends(current_user)):
    if user["plan"] == "free" and user["credits"] <= 0:
        raise HTTPException(402, "Plus de crédits — passe au plan Pro")

    match_data = None
    async with aiohttp.ClientSession() as session:
        for sk in SUPPORTED_LEAGUES:
            for m in await fetch_odds_for_league(session, sk):
                if m["match_id"] == match_id:
                    match_data = m; break
            if match_data:
                break

    if not match_data:
        conn = get_db()
        row = conn.execute("SELECT * FROM match_cache WHERE match_id=?", (match_id,)).fetchone()
        conn.close()
        if row:
            return dict(row)
        raise HTTPException(404, "Match introuvable")

    result = await full_analysis(match_data)

    if user["plan"] == "free":
        conn = get_db()
        conn.execute("UPDATE users SET credits=credits-1 WHERE id=?", (user["id"],))
        conn.commit(); conn.close()

    stats = json.loads(result.get("stats_json") or "{}")
    return {
        "match_id": result["match_id"],
        "team_home": result["team_home"],
        "team_away": result["team_away"],
        "league": result["league_label"],
        "commence_time": result["commence_time"],
        "odds": {
            "home": result["odds_home"], "draw": result.get("odds_draw"),
            "away": result["odds_away"], "bookmaker": result.get("best_bookmaker"),
        },
        "ai_probabilities": {
            "home": result["prob_home"], "draw": result["prob_draw"], "away": result["prob_away"]
        },
        "expected_values": {
            "home": result["ev_home"], "draw": result["ev_draw"], "away": result["ev_away"]
        },
        "best_bet":       result["best_bet"],
        "kelly_fraction": result["kelly_fraction"],
        "confidence":     result["confidence"],
        "analysis":       result["ai_analysis"],
        "form": {"home": list(result.get("form_home","")), "away": list(result.get("form_away",""))},
        "stats": stats,
        "credits_remaining": user["credits"] - (1 if user["plan"] == "free" else 0),
    }

# ── Bets ───────────────────────────────────────────────────────────────────────
@app.post("/bets", tags=["Bets"])
async def create_bet(body: BetCreate, user=Depends(current_user)):
    conn = get_db()
    m = conn.execute("SELECT * FROM match_cache WHERE match_id=?", (body.match_id,)).fetchone()
    if not m:
        conn.close()
        raise HTTPException(404, "Match non analysé")
    m = dict(m)
    odds_map = {"home": m["odds_home"], "draw": m.get("odds_draw"), "away": m["odds_away"]}
    ev_map   = {"home": m["ev_home"],   "draw": m.get("ev_draw"),   "away": m["ev_away"]}
    if body.bet_type not in odds_map:
        conn.close()
        raise HTTPException(400, "bet_type invalide")
    odds = odds_map[body.bet_type]
    ev   = ev_map[body.bet_type] or 0
    kf   = _kelly(ev, odds)
    cur  = conn.execute("""
        INSERT INTO bets (user_id,match_id,team_home,team_away,league,bet_type,
                          odds,stake,expected_value,kelly_fraction,match_date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (user["id"],body.match_id,m["team_home"],m["team_away"],m["league_label"],
          body.bet_type, odds, body.stake, ev, kf, m["commence_time"]))
    conn.commit()
    bid = cur.lastrowid
    conn.close()
    return {"bet_id": bid, "odds": odds, "expected_value": ev,
            "kelly_fraction": kf, "suggested_stake": round(body.stake*kf, 2),
            "potential_return": round(body.stake*odds, 2)}

@app.patch("/bets/{bet_id}", tags=["Bets"])
async def update_bet(bet_id: int, body: BetUpdate, user=Depends(current_user)):
    conn = get_db()
    row = conn.execute("SELECT user_id FROM bets WHERE id=?", (bet_id,)).fetchone()
    if not row or row["user_id"] != user["id"]:
        conn.close()
        raise HTTPException(404, "Pari introuvable")
    conn.execute("UPDATE bets SET result=?,profit=?,status='settled' WHERE id=?",
                 (body.result, body.profit, bet_id))
    conn.commit(); conn.close()
    return {"message": "Pari mis à jour", "bet_id": bet_id}

@app.get("/bets", tags=["Bets"])
async def get_bets(limit: int = 50, user=Depends(current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM bets WHERE user_id=? ORDER BY placed_at DESC LIMIT ?",
        (user["id"], limit)
    ).fetchall()
    conn.close()
    return {"bets": [dict(r) for r in rows]}

# ── Stats ──────────────────────────────────────────────────────────────────────
@app.get("/stats", tags=["Stats"])
async def get_stats(user=Depends(current_user)):
    conn = get_db()
    o = dict(conn.execute("""
        SELECT COUNT(*) total, SUM(result='won') won, SUM(result='lost') lost,
               SUM(status='pending') pending,
               COALESCE(SUM(profit),0) profit, COALESCE(SUM(stake),0) staked,
               COALESCE(AVG(expected_value),0) avg_ev
        FROM bets WHERE user_id=?
    """, (user["id"],)).fetchone())
    monthly = [dict(r) for r in conn.execute("""
        SELECT strftime('%Y-%m',placed_at) month, COUNT(*) bets,
               COALESCE(SUM(profit),0) profit, SUM(result='won') wins
        FROM bets WHERE user_id=? AND placed_at>date('now','-12 months')
        GROUP BY month ORDER BY month
    """, (user["id"],)).fetchall()]
    by_league = [dict(r) for r in conn.execute("""
        SELECT league, COUNT(*) bets, SUM(result='won') wins, COALESCE(SUM(profit),0) profit
        FROM bets WHERE user_id=? GROUP BY league ORDER BY profit DESC
    """, (user["id"],)).fetchall()]
    conn.close()
    settled = (o["won"] or 0) + (o["lost"] or 0)
    return {
        "total_bets":   o["total"] or 0,
        "won":          o["won"] or 0,
        "lost":         o["lost"] or 0,
        "pending":      o["pending"] or 0,
        "win_rate":     round((o["won"] or 0)/settled*100, 1) if settled else 0,
        "roi":          round((o["profit"]/o["staked"])*100, 1) if o["staked"] else 0,
        "total_profit": round(o["profit"], 2),
        "total_staked": round(o["staked"], 2),
        "avg_ev":       round(o["avg_ev"], 4),
        "monthly":      monthly,
        "by_league":    by_league,
    }

@app.get("/leagues", tags=["Misc"])
async def get_leagues():
    return {"leagues": [{"key": k, "label": v} for k, v in SUPPORTED_LEAGUES.items()]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host=os.getenv("HOST","0.0.0.0"),
                port=int(os.getenv("PORT",8000)), reload=True)
