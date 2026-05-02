"""
agents/market.py — KrishiMind v3
Market Price Forecasting Agent

Input  : crop (str), region (str — Indian state/city)
Output : current price (₹/quintal), 4-week forecast, SELL/HOLD recommendation

Strategy:
  - India MSP 2024-25 base prices + seasonal multipliers + regional variation
  - Statistical trend simulation (sine wave + noise) as price model
  - XGBoost/LSTM not required — rule-based forecasting achieves demo quality
"""

from __future__ import annotations
import math
import random
from datetime import datetime, timedelta

# ──────────────────────────────────────────────────────────────────────────────
# MSP 2024-25 Data (₹ per quintal) — Government of India
# ──────────────────────────────────────────────────────────────────────────────
MSP_2024: dict[str, float] = {
    "wheat":      2275,
    "rice":       2300,
    "maize":      2090,
    "soybean":    4892,
    "groundnut":  6783,
    "cotton":     7121,   # medium staple
    "mustard":    5650,
    "sugarcane":  340,    # per quintal FRP
    "chickpea":   5440,
    "lentil":     6425,
    "onion":      800,    # approx mandi rate
    "tomato":     1200,   # volatile; mandi estimate
    "potato":     650,
}

# Regional price multipliers (demand-supply regional factor)
REGIONAL_FACTOR: dict[str, float] = {
    "punjab": 1.05, "haryana": 1.04, "uttar pradesh": 1.00,
    "madhya pradesh": 0.97, "rajasthan": 0.98, "gujarat": 1.02,
    "maharashtra": 1.01, "karnataka": 1.03, "andhra pradesh": 1.00,
    "telangana": 1.01, "west bengal": 0.99, "bihar": 0.96,
    "odisha": 0.95, "tamil nadu": 1.02, "kerala": 1.06,
    "default": 1.00,
}

# Seasonal price patterns (month → multiplier)
# Prices generally rise post-harvest, fall during harvest season
SEASONAL_PATTERN: dict[str, list[float]] = {
    "wheat":   [1.12, 1.10, 1.05, 0.90, 0.88, 0.92, 0.98, 1.02, 1.05, 1.08, 1.10, 1.12],
    "rice":    [1.00, 1.02, 1.05, 1.08, 1.10, 1.08, 0.92, 0.88, 0.90, 0.95, 0.98, 1.00],
    "onion":   [0.85, 0.90, 1.00, 1.10, 1.20, 1.30, 1.25, 1.15, 1.05, 0.90, 0.80, 0.82],
    "tomato":  [1.20, 1.10, 0.90, 0.85, 1.00, 1.15, 1.30, 1.20, 1.00, 0.90, 0.95, 1.10],
    "default": [1.00] * 12,
}


def _base_price(crop: str) -> float:
    key = crop.lower()
    return MSP_2024.get(key, 2000.0)


def _regional_factor(region: str) -> float:
    key = region.lower()
    for k, v in REGIONAL_FACTOR.items():
        if k in key:
            return v
    return REGIONAL_FACTOR["default"]


def _seasonal_multiplier(crop: str, month_offset: int = 0) -> float:
    month = (datetime.now().month - 1 + month_offset) % 12
    pattern = SEASONAL_PATTERN.get(crop.lower(), SEASONAL_PATTERN["default"])
    return pattern[month]


def _generate_forecast(crop: str, region: str, weeks: int = 4) -> list[dict]:
    """Generate week-by-week price forecast."""
    base   = _base_price(crop)
    reg_f  = _regional_factor(region)
    today  = datetime.now().date()

    forecast = []
    prev_price = base * reg_f * _seasonal_multiplier(crop)

    for w in range(weeks):
        week_date = today + timedelta(weeks=w)
        month_off = w // 4
        seasonal  = _seasonal_multiplier(crop, month_off)
        # Trend: slight price drift + seasonal + random noise
        trend_delta = random.uniform(-0.015, 0.025)   # -1.5% to +2.5% weekly
        price = base * reg_f * seasonal * (1 + trend_delta * w * 0.3)
        price += random.uniform(-price * 0.02, price * 0.02)  # ±2% noise
        price = round(price, 0)

        pct_change = round((price - prev_price) / prev_price * 100, 1)
        direction  = "↑ Rising" if pct_change > 0.5 else ("↓ Falling" if pct_change < -0.5 else "→ Stable")

        forecast.append({
            "week":         w + 1,
            "date":         str(week_date),
            "price":        int(price),
            "pct_change":   pct_change,
            "direction":    direction,
        })
        prev_price = price

    return forecast


def _recommendation(crop: str, current_price: float, forecast: list[dict]) -> tuple[str, str, str]:
    """
    Returns (action, badge, reason).
    action: SELL | HOLD | WAIT
    """
    msp = _base_price(crop)
    last_price = forecast[-1]["price"]
    trend = last_price - current_price

    if current_price < msp * 0.95:
        return "WAIT", "⏳ WAIT — Below MSP", (
            f"Current price ₹{int(current_price)} is below MSP ₹{int(msp)}. "
            "Consider government procurement channels (e-NAM / APMC)."
        )
    elif trend > current_price * 0.05:
        return "HOLD", "📊 HOLD — Prices Rising", (
            f"Price forecast shows ₹{int(last_price)} in 4 weeks "
            f"(+{round(trend/current_price*100,1)}%). Hold for better returns."
        )
    elif trend < -current_price * 0.03:
        return "SELL", "✅ SELL NOW — Peak Window", (
            f"Prices expected to fall to ₹{int(last_price)} in 4 weeks. "
            "Sell now to maximize returns."
        )
    else:
        return "SELL", "✅ SELL — Stable Market", (
            f"Price stable around ₹{int(current_price)}/q. "
            "Good time to sell — avoid storage costs."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def get_market_trend(crop: str, region: str = "India") -> dict:
    """
    Returns:
        {
          "crop", "region", "current_price", "msp", "above_msp",
          "forecast": [...], "action", "badge", "reason",
          "price_chart_data": [...], "agent": "market"
        }
    """
    base = _base_price(crop)
    reg_f = _regional_factor(region)
    current_seasonal = _seasonal_multiplier(crop)
    current_price = round(base * reg_f * current_seasonal * random.uniform(0.97, 1.03), 0)
    msp = base
    above_msp = current_price >= msp

    forecast = _generate_forecast(crop, region)
    action, badge, reason = _recommendation(crop, current_price, forecast)

    # Chart data: current + 4 weeks
    chart = [{"label": "Now", "price": int(current_price)}]
    for f in forecast:
        chart.append({"label": f"Wk{f['week']}", "price": f["price"]})

    return {
        "crop":              crop.title(),
        "region":            region.title(),
        "current_price":     int(current_price),
        "currency":          "₹/quintal",
        "msp":               int(msp),
        "above_msp":         above_msp,
        "forecast":          forecast,
        "action":            action,
        "badge":             badge,
        "reason":            reason,
        "price_chart_data":  chart,
        "market_summary":    (
            f"{crop.title()} in {region}: Current ₹{int(current_price)}/q "
            f"({'above' if above_msp else 'below'} MSP ₹{int(msp)}). "
            f"Recommendation: {action}."
        ),
        "agent":             "market",
    }
