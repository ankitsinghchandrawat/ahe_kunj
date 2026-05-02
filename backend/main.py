"""
main.py — KrishiMind v3 FastAPI Orchestrator
============================================================

Endpoints:
  GET  /health         → Status check
  POST /crop           → Crop recommendation
  POST /irrigation     → 7-day irrigation plan
  POST /pest           → Pest detection (image upload)
  POST /market         → Market price + SELL/HOLD signal
  POST /advisory       → Full agentic loop (all agents combined)
  POST /ask            → NLP text router → auto-routes to right agent

Usage:
  uvicorn main:app --reload --port 8001
  OR: python main.py
"""

import os
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# ── Internal imports ──────────────────────────────────────────────────────────
from database import get_db, log_activity, init_db
from agents.crop_agent  import recommend_crops
from agents.irrigation  import plan_irrigation
from agents.pest_cv     import detect_pest
from agents.market      import get_market_trend

# ══════════════════════════════════════════════════════════════════════════════
# FastAPI App
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="KrishiMind v3 — Smart Agriculture Advisory API",
    description=(
        "AI-driven agricultural advisory agent providing crop recommendations, "
        "irrigation planning (ETc = Kc × ET₀), pest detection, and market trend analysis."
    ),
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic Schemas
# ══════════════════════════════════════════════════════════════════════════════

class CropRequest(BaseModel):
    N:           float = Field(80,   ge=0,   le=500,  description="Nitrogen (kg/ha)")
    P:           float = Field(40,   ge=0,   le=300,  description="Phosphorus (kg/ha)")
    K:           float = Field(40,   ge=0,   le=300,  description="Potassium (kg/ha)")
    temperature: float = Field(25,   ge=-10, le=55,   description="Temperature (°C)")
    pH:          float = Field(6.5,  ge=0,   le=14,   description="Soil pH")
    humidity:    float = Field(60,   ge=0,   le=100,  description="Humidity (%)")
    rainfall:    float = Field(80,   ge=0,   le=500,  description="Monthly rainfall (mm)")
    season:      Optional[str] = Field(None, description="Kharif | Rabi | Zaid")


class IrrigationRequest(BaseModel):
    crop:        str   = Field("wheat",  description="Crop name")
    location:    str   = Field("Delhi",  description="City or city, State")
    soil_type:   str   = Field("loamy",  description="sandy | loamy | clay | black | red | alluvial")
    land_acres:  float = Field(1.0, ge=0.1, le=1000, description="Land area in acres")


class MarketRequest(BaseModel):
    crop:   str = Field("wheat",  description="Crop name")
    region: str = Field("Punjab", description="Indian state or city")


class AdvisoryRequest(BaseModel):
    farmer_name: str   = Field("Farmer",  description="Farmer's name")
    location:    str   = Field("Delhi",   description="Location")
    soil_type:   str   = Field("loamy",   description="Soil type")
    season:      str   = Field("Kharif",  description="Current season")
    land_acres:  float = Field(1.0,       description="Land in acres")
    N:           float = Field(80.0,      description="Nitrogen kg/ha")
    P:           float = Field(40.0,      description="Phosphorus kg/ha")
    K:           float = Field(40.0,      description="Potassium kg/ha")
    pH:          float = Field(6.5,       description="Soil pH")
    temperature: float = Field(25.0,      description="Temperature °C")
    humidity:    float = Field(60.0,      description="Humidity %")
    rainfall:    float = Field(80.0,      description="Rainfall mm/month")


class AskRequest(BaseModel):
    query:       str   = Field(..., description="Natural language farmer question")
    location:    str   = Field("Delhi", description="Farmer location")
    crop:        Optional[str] = None
    soil_type:   str   = Field("loamy")
    land_acres:  float = Field(1.0)


# ══════════════════════════════════════════════════════════════════════════════
# NLP Router
# ══════════════════════════════════════════════════════════════════════════════

def _route_query(query: str) -> str:
    """Simple keyword-based intent classifier."""
    q = query.lower()
    if any(w in q for w in ["water", "irrigat", "rain", "dry", "moisture", "et0", "etc", "schedule"]):
        return "irrigation"
    if any(w in q for w in ["pest", "insect", "disease", "leaf", "spot", "blight", "aphid", "bug", "spray"]):
        return "pest_text"
    if any(w in q for w in ["price", "sell", "market", "rate", "mandi", "profit", "hold", "msp"]):
        return "market"
    if any(w in q for w in ["crop", "plant", "sow", "grow", "recommend", "npk", "nitrogen", "soil", "pH"]):
        return "crop"
    return "advisory"


# ══════════════════════════════════════════════════════════════════════════════
# Startup
# ══════════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
def on_startup():
    init_db()
    print("[KrishiMind] v3 API started — all agents ready.")


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status":    "✅ KrishiMind v3 is running",
        "version":   "3.0.0",
        "agents":    ["crop", "irrigation", "pest", "market"],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "docs":      "/docs",
    }


# ── Crop ──────────────────────────────────────────────────────────────────────

@app.post("/crop", tags=["Agents"])
def crop_endpoint(req: CropRequest):
    """Recommend top 3 crops based on soil NPK, pH, climate parameters."""
    try:
        result = recommend_crops(
            N=req.N, P=req.P, K=req.K,
            temperature=req.temperature, pH=req.pH,
            humidity=req.humidity, rainfall=req.rainfall,
            season=req.season,
        )
        log_activity("crop", req.model_dump(), result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Irrigation ────────────────────────────────────────────────────────────────

@app.post("/irrigation", tags=["Agents"])
def irrigation_endpoint(req: IrrigationRequest):
    """Generate 7-day irrigation schedule using ETc = Kc × ET₀."""
    try:
        result = plan_irrigation(
            crop=req.crop, location=req.location,
            soil_type=req.soil_type, land_acres=req.land_acres,
        )
        log_activity("irrigation", req.model_dump(), result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Pest Detection ────────────────────────────────────────────────────────────

@app.post("/pest", tags=["Agents"])
async def pest_endpoint(
    image: UploadFile = File(..., description="Leaf or crop photo"),
    crop_name: str    = Form("unknown", description="Optional crop name"),
):
    """Analyze uploaded image for pest/disease detection."""
    try:
        img_bytes = await image.read()
        if len(img_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty image file")
        result = detect_pest(img_bytes, crop_name)
        log_activity("pest", {"crop_name": crop_name, "filename": image.filename}, result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Market ────────────────────────────────────────────────────────────────────

@app.post("/market", tags=["Agents"])
def market_endpoint(req: MarketRequest):
    """Get current price, 4-week forecast, and SELL/HOLD recommendation."""
    try:
        result = get_market_trend(crop=req.crop, region=req.region)
        log_activity("market", req.model_dump(), result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Full Advisory Loop ────────────────────────────────────────────────────────

@app.post("/advisory", tags=["Agents"])
def advisory_endpoint(req: AdvisoryRequest):
    """
    Full Agentic Loop — combines all 3 agents:
      Crop Recommendation + Irrigation Plan + Market Trend
    """
    try:
        crop_result = recommend_crops(
            N=req.N, P=req.P, K=req.K,
            temperature=req.temperature, pH=req.pH,
            humidity=req.humidity, rainfall=req.rainfall,
            season=req.season,
        )
        top_crop = crop_result["top_crops"][0]["crop"]

        irr_result = plan_irrigation(
            crop=top_crop, location=req.location,
            soil_type=req.soil_type, land_acres=req.land_acres,
        )

        mkt_result = get_market_trend(crop=top_crop, region=req.location)

        advisory = {
            "farmer":            req.farmer_name,
            "location":          req.location,
            "season":            req.season,
            "recommended_crop":  top_crop,
            "crop_confidence":   crop_result["top_crops"][0]["confidence"],
            "soil_health":       crop_result["soil_health"],
            "top_crops":         crop_result["top_crops"],
            "irrigation":        irr_result,
            "market":            mkt_result,
            "action_items": [
                f"🌾 Sow {top_crop} — best match for your soil ({crop_result['top_crops'][0]['confidence']}% confidence)",
                f"💧 Irrigate on {irr_result['irrigation_days']} of next 7 days (~{irr_result['total_water_litres']:,} L total)",
                f"💰 Market: {mkt_result['badge']} — ₹{mkt_result['current_price']}/q",
            ],
            "ai_explanation": (
                f"For {req.farmer_name}'s {req.land_acres}-acre {req.soil_type} farm in {req.location} ({req.season} season): "
                f"{crop_result['summary']} "
                f"{irr_result['summary']} "
                f"{mkt_result['market_summary']}"
            ),
            "agent": "advisory",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        log_activity("advisory", req.model_dump(), {"recommended_crop": top_crop})
        return advisory

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── NLP Text Router ───────────────────────────────────────────────────────────

@app.post("/ask", tags=["Agents"])
def ask_endpoint(req: AskRequest):
    """
    Natural language query router.
    Detects intent and routes to the appropriate agent.
    """
    intent = _route_query(req.query)
    crop   = req.crop or "wheat"

    if intent == "crop":
        result = recommend_crops(N=80, P=40, K=40, temperature=25, pH=6.5)
        result["routed_to"] = "crop"
        result["query"] = req.query
    elif intent == "irrigation":
        result = plan_irrigation(crop=crop, location=req.location,
                                 soil_type=req.soil_type, land_acres=req.land_acres)
        result["routed_to"] = "irrigation"
        result["query"] = req.query
    elif intent == "market":
        result = get_market_trend(crop=crop, region=req.location)
        result["routed_to"] = "market"
        result["query"] = req.query
    elif intent == "pest_text":
        result = {
            "routed_to": "pest",
            "query": req.query,
            "message": "Pest detection requires an image upload. Use POST /pest with a leaf photo.",
            "tip": "Alternatively, describe symptoms and I can suggest probable pests.",
            "agent": "pest",
        }
    else:
        # Full advisory as fallback
        advisory_req = AdvisoryRequest(
            farmer_name="Farmer", location=req.location,
            soil_type=req.soil_type, season="Kharif",
            land_acres=req.land_acres,
        )
        result = advisory_endpoint(advisory_req)
        result["routed_to"] = "advisory"
        result["query"] = req.query

    log_activity("ask", {"query": req.query, "intent": intent}, result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Dev runner
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
