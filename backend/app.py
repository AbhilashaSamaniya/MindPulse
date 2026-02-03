from __future__ import annotations

import json
import random
from typing import Dict, List
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
SYSTEM_PROMPT = (
    "MindPulse local assistant: concise, supportive, actionable. "
    "Ask at most one clarifying question. Offer short recovery suggestions."
)

USERS_PATH = Path(__file__).parent / "users.json"


def load_users() -> Dict[str, dict]:
    if not USERS_PATH.exists():
        return {}
    try:
        return json.loads(USERS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_users(users: Dict[str, dict]) -> None:
    USERS_PATH.write_text(json.dumps(users, indent=2), encoding="utf-8")


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def compute_mri(payload: Dict[str, float]) -> int:
    sleep = float(payload.get("sleep", 5))
    switching = float(payload.get("switching", 5))
    stress = float(payload.get("stress", 5))
    workload = float(payload.get("workload", 5))
    hrv = float(payload.get("hrv", 5))
    deep_work = float(payload.get("deep_work", 50))
    deep_work_hours = float(payload.get("deep_work_hours", 4))
    context_switching = float(payload.get("context_switching", 50))
    context_hours = float(payload.get("context_hours", 3))
    recovery_breaks = float(payload.get("recovery_breaks", 40))
    recovery_hours = float(payload.get("recovery_hours", 2))
    overload_hours = float(payload.get("overload_hours", 50))
    overload_hours_count = float(payload.get("overload_hours_count", 4))

    score = 100 - (switching * 4 + stress * 5 + workload * 4) + (sleep * 5 + hrv * 3)
    score += deep_work * 0.1 + deep_work_hours * 1.5
    score -= context_switching * 0.15 + context_hours * 2.0
    score += recovery_breaks * 0.12 + recovery_hours * 2.0
    score -= overload_hours * 0.2 + overload_hours_count * 2.5
    return int(clamp(round(score)))


def build_forecast(
    base: float,
    seed: int,
    context_switching: float,
    recovery_breaks: float,
    overload_hours: float,
) -> List[int]:
    random.seed(seed)
    forecast = []
    for day in range(7):
        jitter = random.uniform(-4, 4)
        adjust = context_switching * 0.08 + overload_hours * 0.1 - recovery_breaks * 0.06
        forecast.append(int(clamp(base + day * 3 + jitter + adjust)))
    return forecast


def weekly_series(
    mri: int,
    seed: int,
    deep_work: float,
    context_switching: float,
    recovery_breaks: float,
    overload_hours: float,
) -> Dict[str, List[int]]:
    random.seed(seed)
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    mri_series = []
    load_series = []
    for _ in labels:
        drift = random.uniform(-6, 6)
        day_mri = clamp(
            mri
            + drift
            + deep_work * 0.04
            - context_switching * 0.05
            + recovery_breaks * 0.03
            - overload_hours * 0.06
        )
        mri_series.append(int(day_mri))
        load_series.append(
            int(
                clamp(
                    100
                    - day_mri
                    + overload_hours * 0.2
                    + context_switching * 0.15
                    - recovery_breaks * 0.1
                    + random.uniform(-5, 5)
                )
            )
        )
    return {"labels": labels, "mri": mri_series, "load": load_series}


def risk_package(mri: int) -> Dict[str, str]:
    if mri >= 75:
        return {
            "label": "Healthy",
            "level": "healthy",
            "pill": "🟢 Healthy",
            "forecast_label": "Low Risk",
            "coach_tip": "You can push, but keep a 12-minute reset break every 2 hours.",
            "recovery_now": "Hydration + light stretching recommended now.",
        }
    if mri >= 55:
        return {
            "label": "At Risk",
            "level": "at-risk",
            "pill": "🟡 At Risk",
            "forecast_label": "Elevated Risk",
            "coach_tip": "You need a 17-minute low-stimulus break. Avoid decision-heavy tasks after 6 PM today.",
            "recovery_now": "Step away from screens for 8 minutes and take 10 slow breaths.",
        }
    return {
        "label": "Burnout Incoming",
        "level": "danger",
        "pill": "🔴 Burnout Incoming",
        "forecast_label": "High Risk",
        "coach_tip": "Block 45 minutes for recovery, reduce workload intensity, and delay complex tasks.",
        "recovery_now": "Power nap suggestion: 18 minutes with a quiet timer.",
    }


@app.route("/predict", methods=["POST"])
def predict() -> "tuple[dict, int]":
    payload = request.get_json(force=True, silent=True) or {}
    mri = compute_mri(payload)
    risk = risk_package(mri)
    context_switching = float(payload.get("context_switching", 50))
    recovery_breaks = float(payload.get("recovery_breaks", 40))
    overload_hours = float(payload.get("overload_hours", 50))
    deep_work = float(payload.get("deep_work", 50))

    risk_score = clamp(
        100 - mri + context_switching * 0.12 + overload_hours * 0.18 - recovery_breaks * 0.1
    )
    seed = int(mri + risk_score + payload.get("stress", 5))
    forecast = build_forecast(risk_score, seed, context_switching, recovery_breaks, overload_hours)
    weekly = weekly_series(mri, seed + 7, deep_work, context_switching, recovery_breaks, overload_hours)
    confidence = clamp(0.7 + (mri / 100) * 0.25, 0.7, 0.95)

    response = {
        "mri": mri,
        "risk": {"label": risk["label"], "level": risk["level"], "pill": risk["pill"]},
        "forecast_label": risk["forecast_label"],
        "confidence": round(confidence, 2),
        "forecast": forecast,
        "weekly": weekly,
        "coach_tip": risk["coach_tip"],
        "recovery_now": risk["recovery_now"],
    }
    return jsonify(response), 200


@app.route("/")
def index() -> str:
    return "MindPulse API running. POST /predict with JSON payload.", 200


def local_assistant_reply(message: str) -> str:
    msg = message.lower()
    if any(word in msg for word in ["tired", "exhausted", "burnt", "burnout", "drained"]):
        return (
            "You sound depleted. Try a 12–18 minute low-stimulus break, then pick one tiny task "
            "to restart momentum. Do you want a breathing or a walk suggestion?"
        )
    if any(word in msg for word in ["stress", "anxious", "overwhelmed", "panic"]):
        return (
            "Let’s downshift: 60 seconds of box breathing (4‑4‑4‑4), then a 5‑minute screen break. "
            "What’s the single most urgent task right now?"
        )
    if any(word in msg for word in ["focus", "distracted", "procrastinate", "procrastination"]):
        return (
            "Try a 25‑minute focus sprint: pick one task, close extra tabs, and set a timer. "
            "Want a 2‑minute reset exercise first?"
        )
    if any(word in msg for word in ["sleep", "insomnia", "late"]):
        return (
            "For tonight: dim screens 60 minutes before bed, avoid heavy decisions, and do a 3‑minute "
            "slow-breath routine. What time do you plan to sleep?"
        )
    return (
        "I can help with recovery moves, stress resets, or focus plans. "
        "Tell me how you’re feeling or what you need right now."
    )


@app.route("/chat", methods=["POST"])
def chat() -> "tuple[dict, int]":
    payload = request.get_json(force=True, silent=True) or {}
    message = str(payload.get("message", "")).strip()

    if not message:
        return jsonify({"error": "Message is required."}), 400

    reply = local_assistant_reply(message)
    return jsonify({"reply": reply}), 200


@app.route("/auth/signup", methods=["POST"])
def signup() -> "tuple[dict, int]":
    payload = request.get_json(force=True, silent=True) or {}
    username = str(payload.get("username", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", "")).strip()

    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required."}), 400
    if "@gmail.com" not in email:
        return jsonify({"error": "Gmail address required."}), 400

    users = load_users()
    if email in users:
        return jsonify({"error": "User already exists."}), 409

    users[email] = {"username": username, "password": password}
    save_users(users)
    return jsonify({"ok": True, "username": username, "email": email}), 200


@app.route("/auth/login", methods=["POST"])
def login() -> "tuple[dict, int]":
    payload = request.get_json(force=True, silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", "")).strip()

    users = load_users()
    user = users.get(email)
    if not user or user.get("password") != password:
        return jsonify({"error": "Invalid credentials."}), 401

    return jsonify({"ok": True, "username": user.get("username", ""), "email": email}), 200


@app.route("/auth/ping", methods=["GET"])
def auth_ping() -> "tuple[dict, int]":
    return jsonify({"ok": True, "service": "auth"}), 200


@app.route("/routes", methods=["GET"])
def routes() -> "tuple[dict, int]":
    items = []
    for rule in app.url_map.iter_rules():
        items.append({"endpoint": rule.endpoint, "methods": sorted(rule.methods), "rule": rule.rule})
    return jsonify({"routes": items}), 200


if __name__ == "__main__":
    app.run(debug=False, port=5050)
