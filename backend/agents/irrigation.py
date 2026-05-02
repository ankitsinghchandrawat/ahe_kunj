"""
agents/irrigation.py — KrishiMind v3
Irrigation Planning Agent using ETc = Kc × ET₀ (Hargreaves method)

Input  : crop, location, soil_type, land_acres
Output : 7-day irrigation schedule with water_needed flag and litres per day
"""

from __future__ import annotations
import os, math, random
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

KC_TABLE = {
    "rice": 1.20, "wheat": 1.15, "maize": 1.10, "cotton": 1.15,
    "sugarcane": 1.25, "soybean": 1.10, "chickpea": 1.00, "lentil": 1.00,
    "mustard": 1.05, "groundnut": 1.05, "tomato": 1.15, "onion": 1.00,
    "default": 1.00,
}

SOIL_WHC = {
    "sandy": 0.6, "loamy": 0.8, "clay": 0.9, "black": 0.85,
    "red": 0.70, "alluvial": 0.80, "default": 0.75,
}

CITY_LAT = {
    "delhi": 28.6, "mumbai": 19.1, "pune": 18.5, "nagpur": 21.1,
    "kolkata": 22.6, "chennai": 13.1, "hyderabad": 17.4, "bengaluru": 12.9,
    "jaipur": 26.9, "lucknow": 26.8, "patna": 25.6, "bhopal": 23.3,
    "ahmedabad": 23.0, "chandigarh": 30.7, "default": 23.0,
}


def _fetch_real_weather(location: str) -> list[dict] | None:
    if not WEATHER_API_KEY or WEATHER_API_KEY == "your_key_here":
        return None
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"q": location, "appid": WEATHER_API_KEY, "units": "metric", "cnt": 40},
            timeout=8,
        )
        r.raise_for_status()
        days: dict[str, list] = {}
        for item in r.json()["list"]:
            day = item["dt_txt"][:10]
            days.setdefault(day, []).append(item)
        result = []
        for day, items in sorted(days.items())[:7]:
            temps = [i["main"]["temp"] for i in items]
            result.append({
                "date": day,
                "temp_max": max(temps), "temp_min": min(temps),
                "temp_mean": sum(temps) / len(temps),
                "rainfall": sum(i.get("rain", {}).get("3h", 0) for i in items),
                "humidity": sum(i["main"]["humidity"] for i in items) / len(items),
            })
        return result
    except Exception:
        return None


def _synthetic_weather(n_days: int = 7) -> list[dict]:
    month = datetime.now().month
    if month in (12, 1, 2):
        base, rain_p, rain_mm = 18, 0.05, 2
    elif month in (3, 4, 5):
        base, rain_p, rain_mm = 32, 0.10, 5
    elif month in (6, 7, 8, 9):
        base, rain_p, rain_mm = 28, 0.65, 18
    else:
        base, rain_p, rain_mm = 24, 0.20, 8

    today = datetime.now().date()
    result = []
    for i in range(n_days):
        t = base + random.uniform(-3, 3)
        rain = random.uniform(0, rain_mm * 2) if random.random() < rain_p else 0.0
        result.append({
            "date": str(today + timedelta(days=i)),
            "temp_max": round(t + 5, 1), "temp_min": round(t - 4, 1),
            "temp_mean": round(t, 1), "rainfall": round(rain, 1),
            "humidity": round(min(95, 55 + rain * 2 + random.uniform(-5, 5)), 1),
        })
    return result


def _et0(t_max, t_min, t_mean, lat, doy) -> float:
    dr    = 1 + 0.033 * math.cos(2 * math.pi / 365 * doy)
    delta = 0.409 * math.sin(2 * math.pi / 365 * doy - 1.39)
    phi   = math.radians(lat)
    ws    = math.acos(max(-1, min(1, -math.tan(phi) * math.tan(delta))))
    Ra    = (24 * 60 / math.pi) * 0.082 * dr * (
        ws * math.sin(phi) * math.sin(delta) +
        math.cos(phi) * math.cos(delta) * math.sin(ws))
    return max(0.0023 * (t_mean + 17.8) * math.sqrt(max(t_max - t_min, 0.1)) * Ra * 0.408, 0)


def plan_irrigation(crop: str, location: str = "Delhi",
                    soil_type: str = "loamy", land_acres: float = 1.0) -> dict:
    kc   = KC_TABLE.get(crop.lower(), KC_TABLE["default"])
    lat  = CITY_LAT.get(location.lower().split(",")[0].strip(), CITY_LAT["default"])
    whc  = SOIL_WHC.get(soil_type.lower().split()[0], SOIL_WHC["default"])

    weather = _fetch_real_weather(location)
    weather_source = "live" if weather else "synthetic"
    if not weather:
        weather = _synthetic_weather()

    doy = datetime.now().timetuple().tm_yday
    schedule, total = [], 0.0

    for i, day in enumerate(weather):
        et0  = round(_et0(day["temp_max"], day["temp_min"], day["temp_mean"], lat, doy + i), 2)
        etc  = round(kc * et0, 2)
        eff_rain = round(day["rainfall"] * 0.75, 2)
        net  = max(etc - eff_rain, 0.0) * (1 - whc * 0.3)
        litres = round(net * 4047 * land_acres / 1000, 0)
        needed = net > 0.5

        if not needed:
            action, reason = "✅ No irrigation", f"Rain {day['rainfall']} mm covers demand"
        elif litres < 500:
            action, reason = "💧 Light irrigation", f"Apply {int(litres)} L"
        elif litres < 2000:
            action, reason = "💧💧 Moderate irrigation", f"Apply {int(litres)} L — ETc {etc} mm"
        else:
            action, reason = "💧💧💧 Heavy irrigation", f"Apply {int(litres)} L — high demand"

        total += litres
        schedule.append({
            "date": day["date"], "temp_max": day["temp_max"], "temp_min": day["temp_min"],
            "rainfall_mm": day["rainfall"], "humidity_pct": day["humidity"],
            "et0_mm": et0, "kc": kc, "etc_mm": etc,
            "water_needed": needed, "litres": int(litres),
            "action": action, "reason": reason,
        })

    irr_days = sum(1 for d in schedule if d["water_needed"])
    return {
        "schedule": schedule,
        "total_water_litres": int(total),
        "irrigation_days": irr_days,
        "kc_used": kc,
        "weather_source": weather_source,
        "summary": (f"7-day plan for {crop} ({location}): {irr_days} irrigation days, "
                    f"~{int(total):,} L total for {land_acres} acres."),
        "agent": "irrigation",
    }
