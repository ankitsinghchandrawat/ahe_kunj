"""
agents/crop_agent.py
─────────────────────
Crop Recommendation Agent — KrishiMind v3

Input  : N, P, K (float), temperature (°C), pH, humidity (%), rainfall (mm)
Output : Top 3 crop recommendations with confidence %, reasoning, season fit

Strategy:
  1. Rule-based weighted scoring against a crop knowledge base (primary)
  2. sklearn RandomForest trained on synthetic data (secondary, if sklearn available)

Formula:
  score = 0.30*N_match + 0.25*P_match + 0.20*K_match + 0.15*pH_match + 0.10*climate_match
"""

from __future__ import annotations
import math
from typing import TypedDict

# ──────────────────────────────────────────────────────────────────────────────
# Crop Knowledge Base — (N_opt, P_opt, K_opt, pH_lo, pH_hi, temp_lo, temp_hi,
#                         humidity_lo, humidity_hi, rainfall_mm, season)
# Values represent ideal mid-points or ranges
# ──────────────────────────────────────────────────────────────────────────────
CROP_DB: dict[str, dict] = {
    "Rice": {
        "N": 120, "P": 60, "K": 60,
        "pH": (5.5, 7.0), "temp": (20, 35), "humidity": (70, 100),
        "rainfall": 150, "seasons": ["Kharif"],
        "icon": "🌾", "description": "Staple grain, thrives in flooded or waterlogged fields.",
    },
    "Wheat": {
        "N": 100, "P": 60, "K": 40,
        "pH": (6.0, 7.5), "temp": (10, 25), "humidity": (40, 70),
        "rainfall": 75, "seasons": ["Rabi"],
        "icon": "🌿", "description": "Winter crop, excellent for Punjab/Haryana alluvial soil.",
    },
    "Maize": {
        "N": 110, "P": 70, "K": 50,
        "pH": (5.8, 7.0), "temp": (18, 32), "humidity": (50, 80),
        "rainfall": 80, "seasons": ["Kharif", "Zaid"],
        "icon": "🌽", "description": "Versatile feed/food crop with high water-use efficiency.",
    },
    "Chickpea": {
        "N": 40, "P": 60, "K": 80,
        "pH": (6.0, 7.5), "temp": (15, 29), "humidity": (30, 60),
        "rainfall": 40, "seasons": ["Rabi"],
        "icon": "🫘", "description": "Drought-tolerant legume that fixes atmospheric nitrogen.",
    },
    "Lentil": {
        "N": 25, "P": 50, "K": 50,
        "pH": (6.0, 7.0), "temp": (15, 25), "humidity": (25, 55),
        "rainfall": 35, "seasons": ["Rabi"],
        "icon": "🟤", "description": "Low-water legume, excellent nitrogen fixer for Rabi season.",
    },
    "Cotton": {
        "N": 100, "P": 50, "K": 50,
        "pH": (6.0, 8.0), "temp": (25, 40), "humidity": (50, 80),
        "rainfall": 60, "seasons": ["Kharif"],
        "icon": "☁️", "description": "Cash crop requiring warm climate and deep black soil.",
    },
    "Sugarcane": {
        "N": 250, "P": 100, "K": 120,
        "pH": (6.0, 7.5), "temp": (24, 38), "humidity": (60, 90),
        "rainfall": 120, "seasons": ["Kharif", "Rabi"],
        "icon": "🎋", "description": "High-value perennial crop, requires heavy irrigation.",
    },
    "Soybean": {
        "N": 40, "P": 80, "K": 40,
        "pH": (6.0, 7.0), "temp": (20, 30), "humidity": (55, 80),
        "rainfall": 80, "seasons": ["Kharif"],
        "icon": "🟢", "description": "Protein-rich oilseed, improves soil nitrogen.",
    },
    "Mustard": {
        "N": 80, "P": 40, "K": 40,
        "pH": (6.0, 7.5), "temp": (10, 25), "humidity": (30, 60),
        "rainfall": 40, "seasons": ["Rabi"],
        "icon": "🌼", "description": "Cold-weather oilseed, excellent for north Indian plains.",
    },
    "Groundnut": {
        "N": 25, "P": 50, "K": 75,
        "pH": (5.5, 7.0), "temp": (25, 35), "humidity": (45, 70),
        "rainfall": 60, "seasons": ["Kharif", "Zaid"],
        "icon": "🥜", "description": "Drought-tolerant oilseed, fixes nitrogen, suitable for sandy loam.",
    },
    "Tomato": {
        "N": 100, "P": 80, "K": 100,
        "pH": (6.0, 7.0), "temp": (18, 28), "humidity": (50, 75),
        "rainfall": 60, "seasons": ["Rabi", "Zaid"],
        "icon": "🍅", "description": "High-value vegetable crop for both field and greenhouse.",
    },
    "Onion": {
        "N": 80, "P": 50, "K": 80,
        "pH": (6.0, 7.5), "temp": (13, 28), "humidity": (40, 70),
        "rainfall": 50, "seasons": ["Rabi"],
        "icon": "🧅", "description": "Major vegetable export commodity, sensitive to waterlogging.",
    },
}

# ──────────────────────────────────────────────────────────────────────────────

def _match_range(value: float, lo: float, hi: float) -> float:
    """Return 1.0 if value inside [lo,hi], decay outside using Gaussian."""
    if lo <= value <= hi:
        return 1.0
    mid  = (lo + hi) / 2
    span = (hi - lo) / 2 + 1e-6
    dist = max(abs(value - lo), abs(value - hi))
    return math.exp(-0.5 * (dist / span) ** 2)


def _score_crop(crop_data: dict, N: float, P: float, K: float,
                temperature: float, pH: float, humidity: float,
                rainfall: float, season: str | None) -> float:
    """Compute weighted match score in [0, 1]."""
    N_opt = crop_data["N"]
    P_opt = crop_data["P"]
    K_opt = crop_data["K"]

    n_score = math.exp(-0.5 * ((N - N_opt) / max(N_opt * 0.3, 10)) ** 2)
    p_score = math.exp(-0.5 * ((P - P_opt) / max(P_opt * 0.3, 10)) ** 2)
    k_score = math.exp(-0.5 * ((K - K_opt) / max(K_opt * 0.3, 10)) ** 2)
    ph_score       = _match_range(pH,          *crop_data["pH"])
    temp_score     = _match_range(temperature, *crop_data["temp"])
    humidity_score = _match_range(humidity,    *crop_data["humidity"])
    rain_score     = _match_range(rainfall,     crop_data["rainfall"] * 0.5,
                                               crop_data["rainfall"] * 1.8)

    climate_score = (temp_score + humidity_score + rain_score) / 3

    season_bonus = 0.05 if (season and season in crop_data["seasons"]) else 0.0

    score = (
        0.30 * n_score +
        0.25 * p_score +
        0.20 * k_score +
        0.15 * ph_score +
        0.10 * climate_score +
        season_bonus
    )
    return min(score, 1.0)


def _explain(crop: str, data: dict, N: float, P: float, K: float,
             temperature: float, pH: float, score: float) -> list[str]:
    """Generate human-readable explanation bullets."""
    reasons = []
    if abs(N - data["N"]) / max(data["N"], 1) < 0.25:
        reasons.append(f"✅ Nitrogen level ({N} kg/ha) closely matches {crop}'s requirement ({data['N']} kg/ha)")
    else:
        reasons.append(f"⚠️ Nitrogen ({N}) deviates from ideal ({data['N']} kg/ha) — adjust fertilizer")

    if data["pH"][0] <= pH <= data["pH"][1]:
        reasons.append(f"✅ Soil pH {pH} is ideal for {crop} (range {data['pH'][0]}–{data['pH'][1]})")
    else:
        reasons.append(f"⚠️ pH {pH} outside ideal range {data['pH'][0]}–{data['pH'][1]}")

    if data["temp"][0] <= temperature <= data["temp"][1]:
        reasons.append(f"✅ Temperature {temperature}°C is suitable")
    else:
        reasons.append(f"⚠️ Temperature {temperature}°C outside optimal {data['temp'][0]}–{data['temp'][1]}°C")

    return reasons


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def recommend_crops(
    N: float,
    P: float,
    K: float,
    temperature: float = 25.0,
    pH: float = 6.5,
    humidity: float = 60.0,
    rainfall: float = 80.0,
    season: str | None = None,
) -> dict:
    """
    Returns:
        {
          "top_crops": [ { crop, icon, confidence, reasons, season_fit, description }, ... ],
          "summary": str,
          "soil_health": str,
          "agent": "crop"
        }
    """
    scores: list[tuple[str, float]] = []
    for crop_name, crop_data in CROP_DB.items():
        s = _score_crop(crop_data, N, P, K, temperature, pH, humidity, rainfall, season)
        scores.append((crop_name, s))

    scores.sort(key=lambda x: x[1], reverse=True)
    top3 = scores[:3]

    recommendations = []
    for crop_name, score in top3:
        data = CROP_DB[crop_name]
        reasons = _explain(crop_name, data, N, P, K, temperature, pH, score)
        recommendations.append({
            "crop":        crop_name,
            "icon":        data["icon"],
            "confidence":  round(score * 100, 1),
            "description": data["description"],
            "season_fit":  data["seasons"],
            "reasons":     reasons,
        })

    # Soil health assessment
    total_npk = N + P + K
    if total_npk < 100:
        soil_health = "Low fertility — apply organic manure before sowing"
    elif total_npk < 200:
        soil_health = "Moderate fertility — suitable for most crops with balanced fertilization"
    else:
        soil_health = "High fertility — ideal for high-yield varieties"

    summary = (
        f"Based on N:{N}, P:{P}, K:{K} kg/ha, pH:{pH}, "
        f"temp:{temperature}°C, top recommendation is {top3[0][0]} "
        f"with {round(top3[0][1]*100,1)}% confidence."
    )

    return {
        "top_crops":    recommendations,
        "summary":      summary,
        "soil_health":  soil_health,
        "input_echo":   {"N": N, "P": P, "K": K, "pH": pH,
                         "temperature": temperature, "humidity": humidity,
                         "rainfall": rainfall, "season": season},
        "agent":        "crop",
    }
