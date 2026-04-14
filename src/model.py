"""
model.py
Entraînement XGBoost + calibration, évaluation et sauvegarde.
"""

import os
import argparse
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, classification_report

from features import FEATURE_COLS, compute_team_stats, compute_elo, compute_h2h, compute_fatigue, WINDOW
from data_loader import download_data, clean_data

LABELS    = ["Victoire domicile", "Match nul", "Victoire extérieur"]
MODEL_DIR = "models"


def _build_xgb() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mlogloss",
        tree_method="hist",
        random_state=42,
        verbosity=0,
    )


def train(df: pd.DataFrame, test_ratio: float = 0.2):
    """
    Entraîne le modèle sur un split temporel.

    Returns:
        model (CalibratedClassifierCV), None (scaler — plus nécessaire), df_test
    """
    X = df[FEATURE_COLS]
    y = df["target"]

    split = int(len(df) * (1 - test_ratio))
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]
    df_test = df.iloc[split:].copy().reset_index(drop=True)

    print(f"Train : {len(X_train)} matchs | Test : {len(X_test)} matchs")

    model = CalibratedClassifierCV(_build_xgb(), method="sigmoid", cv=3)
    model.fit(X_train, y_train)

    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    acc = accuracy_score(y_test, y_pred)
    print(f"\n🎯 Accuracy : {acc:.1%}")
    print(classification_report(y_test, y_pred, target_names=LABELS))

    df_test["prob_H"] = y_proba[:, 0]
    df_test["prob_D"] = y_proba[:, 1]
    df_test["prob_A"] = y_proba[:, 2]

    return model, None, df_test


def save_model(model, scaler=None, name: str = "xgb"):
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(MODEL_DIR, f"{name}_model.pkl"))
    print(f"💾 Modèle sauvegardé dans {MODEL_DIR}/")


def load_model(name: str = "xgb"):
    model = joblib.load(os.path.join(MODEL_DIR, f"{name}_model.pkl"))
    return model, None


def predict_match(home_team: str, away_team: str, df: pd.DataFrame, model, scaler=None):
    def get_stats(team, is_home):
        if is_home:
            recent = df[df["HomeTeam"] == team].tail(WINDOW)
            if len(recent) == 0:
                return None
            form  = recent.apply(
                lambda r: 3 if r["result"] == "H" else (1 if r["result"] == "D" else 0), axis=1
            ).mean()
            avg_scored   = recent["home_goals"].mean()
            avg_conceded = recent["away_goals"].mean()
        else:
            recent = df[df["AwayTeam"] == team].tail(WINDOW)
            if len(recent) == 0:
                return None
            form  = recent.apply(
                lambda r: 3 if r["result"] == "A" else (1 if r["result"] == "D" else 0), axis=1
            ).mean()
            avg_scored   = recent["away_goals"].mean()
            avg_conceded = recent["home_goals"].mean()
        return form, avg_scored, avg_conceded

    home_s = get_stats(home_team, True)
    away_s = get_stats(away_team, False)

    if not home_s:
        raise ValueError(f"Équipe introuvable : {home_team}")
    if not away_s:
        raise ValueError(f"Équipe introuvable : {away_team}")

    # Minimal feature vector (new features get neutral defaults)
    features = np.array([[
        home_s[0], away_s[0], home_s[0] - away_s[0],
        home_s[1], home_s[2],
        away_s[1], away_s[2],
        home_s[1] - away_s[1],
        home_s[2] - away_s[2],
        1500.0, 1500.0, 0.0,        # ELO — neutre
        home_s[1], away_s[1], 0.0,  # xG proxy
        home_s[0], away_s[0],       # home_home_form / away_away_form
        1/3, 1/4,                   # h2h priors
        0, 0,                       # fatigue
    ]])

    proba = model.predict_proba(features)[0]

    result = {
        "home":       home_team,
        "away":       away_team,
        "prob_H":     proba[0],
        "prob_D":     proba[1],
        "prob_A":     proba[2],
        "prediction": LABELS[np.argmax(proba)],
    }

    print(f"\n🔮 {home_team} vs {away_team}")
    print(f"   Victoire {home_team:<25} : {proba[0]:.1%}")
    print(f"   Match nul                          : {proba[1]:.1%}")
    print(f"   Victoire {away_team:<25} : {proba[2]:.1%}")
    print(f"   → {result['prediction']}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RockIA — Prédiction football")
    parser.add_argument("--home",   type=str, help="Équipe domicile")
    parser.add_argument("--away",   type=str, help="Équipe extérieur")
    parser.add_argument("--league", type=str, default="E0")
    args = parser.parse_args()

    raw = download_data(league=args.league)
    df  = clean_data(raw)
    df  = compute_team_stats(df)
    df, _ = compute_elo(df)
    df  = compute_h2h(df)
    df  = compute_fatigue(df)

    model, _, df_test = train(df)
    save_model(model)

    if args.home and args.away:
        predict_match(args.home, args.away, df, model)
