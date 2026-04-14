"""
database.py — Gestion BDD SQLite pour RockIA
Tables : users, user_bets
"""

import sqlite3
import hashlib
import secrets
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "rockai.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Crée les tables si elles n'existent pas."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_bets (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            match_id      TEXT NOT NULL,
            home_team     TEXT NOT NULL,
            away_team     TEXT NOT NULL,
            league        TEXT NOT NULL DEFAULT '',
            bet_label     TEXT NOT NULL,
            odds          REAL NOT NULL,
            stake         REAL NOT NULL DEFAULT 10.0,
            model_proba   REAL,
            edge          REAL,
            result        TEXT,
            profit        REAL,
            match_date    TIMESTAMP,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


# ─── Auth ──────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, h = password_hash.split(":", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False


def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    """Retourne (success, message)."""
    if len(username) < 3:
        return False, "Le nom d'utilisateur doit faire au moins 3 caractères."
    if len(password) < 6:
        return False, "Le mot de passe doit faire au moins 6 caractères."
    conn = get_conn()
    try:
        ph = _hash_password(password)
        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username.strip(), email.strip().lower(), ph),
        )
        conn.commit()
        return True, "Compte créé avec succès."
    except sqlite3.IntegrityError as e:
        msg = str(e)
        if "username" in msg:
            return False, "Ce nom d'utilisateur est déjà pris."
        return False, "Cet email est déjà utilisé."
    finally:
        conn.close()


def login_user(username: str, password: str) -> tuple[bool, dict | None]:
    """Retourne (success, user_dict | None)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username.strip(),)
    ).fetchone()
    conn.close()
    if row and _verify_password(password, row["password_hash"]):
        return True, dict(row)
    return False, None


# ─── Bets ──────────────────────────────────────────────────────────

def add_user_bet(user_id: int, match: dict, best_bet: dict, stake: float = 10.0) -> bool:
    """Enregistre un pari. Retourne False si ce match est déjà suivi."""
    conn = get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM user_bets WHERE user_id = ? AND match_id = ?",
            (user_id, match["id"]),
        ).fetchone()
        if existing:
            return False
        match_date = match["commence_time"]
        if hasattr(match_date, "isoformat"):
            match_date = match_date.isoformat()
        conn.execute(
            """
            INSERT INTO user_bets
                (user_id, match_id, home_team, away_team, league,
                 bet_label, odds, stake, model_proba, edge, match_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                str(match["id"]),
                match["home_team"],
                match["away_team"],
                match.get("league_code", ""),
                best_bet["label"],
                best_bet["odds"],
                stake,
                best_bet["proba"],
                best_bet["edge"],
                match_date,
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_user_bets(user_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM user_bets WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_stats(user_id: int) -> dict:
    bets = get_user_bets(user_id)
    if not bets:
        return {
            "total": 0, "resolved": 0, "won": 0,
            "win_rate": 0.0, "total_profit": 0.0,
            "total_stake": 0.0, "roi": 0.0, "bets": [],
        }
    resolved = [b for b in bets if b["result"] is not None]
    won      = [b for b in resolved if b["result"] == "win"]
    total_profit = sum(b["profit"] or 0 for b in resolved)
    total_stake  = sum(b["stake"] for b in resolved) or 1
    return {
        "total":        len(bets),
        "resolved":     len(resolved),
        "won":          len(won),
        "win_rate":     len(won) / max(len(resolved), 1) * 100,
        "total_profit": total_profit,
        "total_stake":  total_stake,
        "roi":          total_profit / total_stake * 100,
        "bets":         bets,
    }


def is_bet_tracked(user_id: int, match_id: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM user_bets WHERE user_id = ? AND match_id = ?",
        (user_id, str(match_id)),
    ).fetchone()
    conn.close()
    return row is not None
