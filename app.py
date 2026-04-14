"""
RockIA — Flask app
Lancer : python app.py → http://localhost:8080
"""

import os, sys, json
from datetime import datetime
from collections import defaultdict
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from xgboost import XGBClassifier
from sklearn.calibration import CalibratedClassifierCV

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from data_loader import download_data, clean_data
from features import compute_team_stats, compute_elo, compute_h2h, compute_fatigue, FEATURE_COLS, WINDOW, H2H_WINDOW, FATIGUE_DAYS
from odds_api import get_upcoming_matches, match_team_name
from backtest import run_backtest
from injuries_api import build_injury_reports, adjust_proba_for_injuries
from dixon_coles import DixonColesModel
from database import init_db, login_user, register_user, get_user_stats, add_user_bet, is_bet_tracked

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "rockia-secret-2025")

PARIS_TZ     = ZoneInfo("Europe/Paris")
SEASONS      = ["2425", "2526"]
TRAIN_LEAGUES= ["E0", "F1", "D1", "SP1", "I1"]
DC_WEIGHT    = 0.45
VALUE_THRESHOLD = 0.05

COMPETITIONS = {
    "E0":  {"name": "Premier League",   "short": "PL",  "color": "#7c3aed", "bg": "#ede9fe"},
    "F1":  {"name": "Ligue 1",          "short": "L1",  "color": "#2563eb", "bg": "#dbeafe"},
    "D1":  {"name": "Bundesliga",       "short": "BL",  "color": "#dc2626", "bg": "#fee2e2"},
    "SP1": {"name": "La Liga",          "short": "LL",  "color": "#ea580c", "bg": "#ffedd5"},
    "I1":  {"name": "Serie A",          "short": "SA",  "color": "#16a34a", "bg": "#dcfce7"},
    "UCL": {"name": "Champions League", "short": "UCL", "color": "#d97706", "bg": "#fef3c7"},
}
LEAGUE_ORDER = ["UCL", "E0", "F1", "SP1", "D1", "I1"]

init_db()

# ── Cache module-level ─────────────────────────────────────────────
_cache = {}

def _build_xgb():
    return XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric="mlogloss", tree_method="hist",
        random_state=42, verbosity=0,
    )

def get_model():
    if "model" in _cache:
        return _cache["model"]

    all_dfs, elo_ratings, raw_by_league = [], {}, {}
    for code in TRAIN_LEAGUES:
        try:
            raw   = download_data(league=code, seasons=SEASONS)
            df_lg = clean_data(raw)
            df_lg = compute_team_stats(df_lg)
            df_lg, league_elo = compute_elo(df_lg)
            df_lg = compute_h2h(df_lg)
            df_lg = compute_fatigue(df_lg)
            df_lg["league"] = code
            all_dfs.append(df_lg)
            elo_ratings.update(league_elo)
            raw_by_league[code] = df_lg
        except Exception as e:
            print(f"[WARN] {code}: {e}")

    df = pd.concat(all_dfs, ignore_index=True).sort_values("Date").reset_index(drop=True)
    X, y = df[FEATURE_COLS], df["target"]
    model = CalibratedClassifierCV(_build_xgb(), method="sigmoid", cv=3)
    model.fit(X, y)

    dc_models = {}
    for code, df_lg in raw_by_league.items():
        try:
            dc = DixonColesModel(xi=0.0065).fit(df_lg)
            if dc._fitted:
                dc_models[code] = dc
        except Exception:
            pass

    split   = int(len(df) * 0.8)
    bt_model = CalibratedClassifierCV(_build_xgb(), method="sigmoid", cv=3)
    bt_model.fit(X.iloc[:split], y.iloc[:split])
    df_test  = df.iloc[split:].copy().reset_index(drop=True)
    proba    = bt_model.predict_proba(X.iloc[split:])
    df_test["prob_H"] = proba[:, 0]
    df_test["prob_D"] = proba[:, 1]
    df_test["prob_A"] = proba[:, 2]

    training_teams = sorted(set(df["HomeTeam"]) | set(df["AwayTeam"]))

    _cache["model"] = (df, model, dc_models, elo_ratings, df_test, training_teams)
    return _cache["model"]

def get_upcoming():
    import time
    if "upcoming" in _cache and time.time() - _cache.get("upcoming_ts", 0) < 3600:
        return _cache["upcoming"]
    all_matches = []
    for code in COMPETITIONS:
        try:
            matches, _ = get_upcoming_matches(league=code, days=7)
            for m in matches:
                m["league_code"] = code
                m["comp"] = COMPETITIONS[code]
            all_matches.extend(matches)
        except Exception:
            pass
    all_matches.sort(key=lambda x: x["commence_time"])
    _cache["upcoming"] = all_matches
    _cache["upcoming_ts"] = time.time()
    return all_matches

# ── Helpers prédiction ─────────────────────────────────────────────
def get_team_stats_local(team, df, is_home=None):
    home_r = df[df["HomeTeam"] == team]
    away_r = df[df["AwayTeam"] == team]
    has_xg = "home_xg" in df.columns

    home = home_r[["Date","home_goals","away_goals","result"]].copy()
    home["points"]   = home["result"].map({"H":3,"D":1,"A":0})
    home["scored"]   = home["home_goals"]
    home["conceded"] = home["away_goals"]
    home["tr"]       = home["result"].map({"H":"W","D":"D","A":"L"})
    home["is_home"]  = True
    home["opponent"] = home_r["AwayTeam"].values

    away = away_r[["Date","home_goals","away_goals","result"]].copy()
    away["points"]   = away["result"].map({"A":3,"D":1,"H":0})
    away["scored"]   = away["away_goals"]
    away["conceded"] = away["home_goals"]
    away["tr"]       = away["result"].map({"A":"W","D":"D","H":"L"})
    away["is_home"]  = False
    away["opponent"] = away_r["HomeTeam"].values

    all_g = pd.concat([home[["Date","points","scored","conceded","tr","is_home","opponent"]],
                       away[["Date","points","scored","conceded","tr","is_home","opponent"]]]).sort_values("Date")
    if len(all_g) == 0:
        return None

    last = all_g.tail(WINDOW)
    venue = all_g[all_g["is_home"] == (is_home if is_home is not None else True)].tail(WINDOW)
    if len(venue) == 0:
        venue = last

    last_results = []
    for _, row in all_g.tail(8).iterrows():
        last_results.append({
            "result": row["tr"],
            "is_home": bool(row["is_home"]),
            "opponent": row.get("opponent",""),
            "gf": int(row["scored"]) if pd.notna(row["scored"]) else 0,
            "ga": int(row["conceded"]) if pd.notna(row["conceded"]) else 0,
            "date": row["Date"].strftime("%d/%m") if pd.notna(row["Date"]) else "",
        })

    return {
        "form": last["points"].mean(),
        "venue_form": venue["points"].mean(),
        "avg_scored": last["scored"].mean(),
        "avg_conceded": last["conceded"].mean(),
        "avg_xg": last["scored"].mean(),
        "last_results": last_results,
    }

def compute_pred(match, df, model, training_teams, elo_ratings, dc_models):
    home_m = match_team_name(match["home_team"], training_teams)
    away_m = match_team_name(match["away_team"], training_teams)
    hs = get_team_stats_local(home_m, df, is_home=True)
    as_ = get_team_stats_local(away_m, df, is_home=False)
    if not hs or not as_:
        return None

    home_elo = elo_ratings.get(home_m, 1500.0)
    away_elo = elo_ratings.get(away_m, 1500.0)
    h2h_row  = df[((df["HomeTeam"]==home_m)&(df["AwayTeam"]==away_m))|
                  ((df["HomeTeam"]==away_m)&(df["AwayTeam"]==home_m))].tail(H2H_WINDOW)
    h2h_win  = sum((r["HomeTeam"]==home_m and r["result"]=="H") or
                   (r["AwayTeam"]==home_m and r["result"]=="A")
                   for _, r in h2h_row.iterrows()) / max(len(h2h_row),1)
    h2h_draw = sum(r["result"]=="D" for _, r in h2h_row.iterrows()) / max(len(h2h_row),1)

    ref = pd.Timestamp(match["commence_time"]).tz_localize(None) if match["commence_time"].tzinfo else pd.Timestamp(match["commence_time"])
    cutoff = ref - pd.Timedelta(days=FATIGUE_DAYS)
    home_fat = len(df[((df["HomeTeam"]==home_m)|(df["AwayTeam"]==home_m))&(df["Date"]>cutoff)&(df["Date"]<ref)])
    away_fat = len(df[((df["HomeTeam"]==away_m)|(df["AwayTeam"]==away_m))&(df["Date"]>cutoff)&(df["Date"]<ref)])

    feat = np.array([[
        hs["form"], as_["form"], hs["form"]-as_["form"],
        hs["avg_scored"], hs["avg_conceded"],
        as_["avg_scored"], as_["avg_conceded"],
        hs["avg_scored"]-as_["avg_scored"], hs["avg_conceded"]-as_["avg_conceded"],
        home_elo, away_elo, home_elo-away_elo,
        hs["avg_xg"], as_["avg_xg"], hs["avg_xg"]-as_["avg_xg"],
        hs.get("venue_form", hs["form"]), as_.get("venue_form", as_["form"]),
        h2h_win, h2h_draw, home_fat, away_fat,
    ]])

    proba_xgb = model.predict_proba(feat)[0]
    lc = match.get("league_code","")
    dc = dc_models.get(lc)
    proba_dc = dc.predict_proba(home_m, away_m) if dc else None
    if proba_dc is not None and not np.allclose(proba_dc, 1/3):
        proba = (1-DC_WEIGHT)*proba_xgb + DC_WEIGHT*proba_dc
        proba = proba / proba.sum()
    else:
        proba = proba_xgb

    odds  = [match["odds_H"], match["odds_D"], match["odds_A"]]
    over  = sum(1/o for o in odds)
    fair  = [1/o/over for o in odds]
    implied = [1/o for o in odds]
    edges = [proba[i]-fair[i] for i in range(3)]
    labels = [match["home_team"], "Nul", match["away_team"]]

    best_bet = None
    best_kelly = -1.0
    xgb_best = int(np.argmax(proba_xgb))
    dc_best  = int(np.argmax(proba_dc)) if proba_dc is not None else xgb_best

    for i in range(3):
        p = float(proba[i])
        b = odds[i]-1
        fk = max(0.0, (p*b-(1-p))/b)
        qk = min(fk*0.25, 0.25)
        models_agree = (proba_dc is None) or (xgb_best==dc_best==i)
        if edges[i]>=0.05 and qk>=0.02 and p>=0.40 and models_agree and qk>best_kelly:
            best_kelly = qk
            best_bet = {"label":labels[i],"odds":odds[i],"edge":edges[i],"proba":p,"idx":i,"kelly":qk}

    return {
        "proba": proba.tolist(), "odds": odds, "implied": implied,
        "fair": fair, "edges": edges, "labels": labels,
        "best_bet": best_bet, "home_m": home_m, "away_m": away_m,
        "hs": hs, "as_": as_, "home_elo": home_elo, "away_elo": away_elo,
    }

# ── Routes ─────────────────────────────────────────────────────────
@app.route("/")
def index():
    tab = request.args.get("tab", "matches")
    only_value = request.args.get("value", "1") == "1"
    selected_day = request.args.get("day", None)

    try:
        df, model, dc_models, elo_ratings, df_test, training_teams = get_model()
    except Exception as e:
        return render_template("error.html", error=str(e))

    upcoming = get_upcoming()
    predictions = {}
    for m in upcoming:
        try:
            predictions[m["id"]] = compute_pred(m, df, model, training_teams, elo_ratings, dc_models)
        except Exception:
            predictions[m["id"]] = None

    by_day = defaultdict(list)
    day_labels = {}
    for m in upcoming:
        dt = m["commence_time"].astimezone(PARIS_TZ)
        key = dt.strftime("%Y-%m-%d")
        if key not in day_labels:
            day_labels[key] = dt.strftime("%a. %d %b").capitalize()
        by_day[key].append({**m, "_dt": dt})

    sorted_days = sorted(by_day.keys())
    if not selected_day or selected_day not in sorted_days:
        selected_day = sorted_days[0] if sorted_days else None

    n_value  = sum(1 for m in upcoming if predictions.get(m["id"]) and predictions[m["id"]]["best_bet"])
    n_leagues = len(set(m["league_code"] for m in upcoming))
    n_matches_train = len(df)

    user = None
    user_stats = None
    if "user_id" in session:
        try:
            user_stats = get_user_stats(session["user_id"])
            user = {"username": session.get("username",""), "email": session.get("email","")}
        except Exception:
            pass

    return render_template("index.html",
        tab=tab, only_value=only_value, selected_day=selected_day,
        by_day=by_day, day_labels=day_labels, sorted_days=sorted_days,
        predictions=predictions, competitions=COMPETITIONS, league_order=LEAGUE_ORDER,
        n_value=n_value, n_leagues=n_leagues, n_matches_train=n_matches_train, n_upcoming=len(upcoming),
        user=user, user_stats=user_stats,
        df_test=df_test, value_threshold=VALUE_THRESHOLD,
    )

@app.route("/match/<match_id>")
def match_detail(match_id):
    upcoming = get_upcoming()
    match = next((m for m in upcoming if str(m["id"]) == str(match_id)), None)
    if not match:
        return redirect(url_for("index"))

    df, model, dc_models, elo_ratings, df_test, training_teams = get_model()
    pred = compute_pred(match, df, model, training_teams, elo_ratings, dc_models)
    if not pred:
        return redirect(url_for("index"))

    user = None
    already_tracked = False
    if "user_id" in session:
        user = {"username": session.get("username",""), "id": session["user_id"]}
        already_tracked = is_bet_tracked(session["user_id"], str(match_id))

    dt = match["commence_time"].astimezone(PARIS_TZ)
    return render_template("match.html",
        match=match, pred=pred, dt=dt,
        competitions=COMPETITIONS,
        user=user, already_tracked=already_tracked,
    )

@app.route("/refresh")
def refresh():
    _cache.pop("upcoming", None)
    _cache.pop("upcoming_ts", None)
    return redirect(url_for("index"))

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username","").strip()
    password = request.form.get("password","")
    ok, user = login_user(username, password)
    if ok:
        session["user_id"]  = user["id"]
        session["username"] = user["username"]
        session["email"]    = user.get("email","")
    return redirect(request.referrer or url_for("index", tab="account"))

@app.route("/register", methods=["POST"])
def register():
    username  = request.form.get("username","").strip()
    email     = request.form.get("email","").strip()
    password  = request.form.get("password","")
    password2 = request.form.get("password2","")
    if password != password2:
        return redirect(url_for("index", tab="account"))
    register_user(username, email, password)
    return redirect(url_for("index", tab="account"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/track-bet", methods=["POST"])
def track_bet():
    if "user_id" not in session:
        return redirect(url_for("index"))
    data = request.form
    match_id = data.get("match_id")
    upcoming = get_upcoming()
    match = next((m for m in upcoming if str(m["id"]) == str(match_id)), None)
    if match:
        df, model, dc_models, elo_ratings, df_test, training_teams = get_model()
        pred = compute_pred(match, df, model, training_teams, elo_ratings, dc_models)
        if pred and pred["best_bet"]:
            stake = float(data.get("stake", 10))
            add_user_bet(session["user_id"], match, pred["best_bet"], stake=stake)
    return redirect(url_for("match_detail", match_id=match_id))

@app.route("/backtest-data")
def backtest_data():
    threshold = float(request.args.get("threshold", 0.05))
    mise = float(request.args.get("mise", 10))
    _, _, _, _, df_test, _ = get_model()
    bets = run_backtest(df_test, value_threshold=threshold, mise=mise)
    if bets.empty:
        return jsonify({"empty": True})
    bets["Date"] = pd.to_datetime(bets["Date"]).dt.strftime("%d/%m")
    return jsonify({
        "n": len(bets),
        "roi": round((bets["Profit"].sum() / (len(bets)*mise)) * 100, 1),
        "win_rate": round(bets["Gagné"].mean() * 100, 1),
        "profit": round(bets["Profit"].sum(), 2),
        "bankroll": (mise * len(bets) + bets["Profit"].cumsum()).round(2).tolist(),
        "bets": bets[["Date","Match","Pari","Cote","Proba_modele","Gagné","Profit"]].head(50).to_dict("records"),
    })

if __name__ == "__main__":
    app.run(debug=True, port=8080, host="127.0.0.1")
