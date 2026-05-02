# 🌾 KrishiMind v3 — Smart Agriculture Advisory Agent

AI-driven platform that synthesizes soil data, weather, and market trends into actionable farm advice.

## Folder Structure
```
ahe_kunj/
├── backend/
│   ├── main.py              ← FastAPI orchestrator (port 8001)
│   ├── database.py          ← SQLite + audit log
│   ├── models.py            ← ORM tables
│   ├── requirements.txt
│   ├── .env.example         ← Copy to .env
│   └── agents/
│       ├── crop_agent.py    ← NPK scoring → Top 3 crops
│       ├── irrigation.py    ← ETc = Kc × ET₀ + OpenWeather
│       ├── pest_cv.py       ← PIL image analysis → pest ID
│       └── market.py        ← MSP 2024-25 + SELL/HOLD signal
├── frontend/
│   ├── index.html           ← Open directly in browser
│   ├── app.js
│   └── style.css
└── agriculture.db           ← Auto-created on first run
```

## Quick Start

### 1. Install backend
```powershell
cd backend
pip install -r requirements.txt --prefer-binary
```

### 2. (Optional) Add OpenWeatherMap key
```powershell
copy .env.example .env
# Edit .env and add your key from openweathermap.org
```

### 3. Start backend
```powershell
# If venv available:
python -m uvicorn main:app --reload --port 8001

# OR direct path:
C:\Users\achan\Downloads\krishimind\venv\Scripts\python.exe -m uvicorn main:app --reload --port 8001
```

### 4. Open frontend
```
Open frontend/index.html in your browser
```

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Status check |
| POST | /crop | Crop recommendation (NPK input) |
| POST | /irrigation | 7-day water schedule (ETc formula) |
| POST | /pest | Pest detection (image upload) |
| POST | /market | Price forecast + SELL/HOLD |
| POST | /advisory | Full agentic loop (all agents) |
| POST | /ask | NLP text → auto-routed agent |

Swagger UI: http://localhost:8001/docs

## Key Formulas
- **ETc = Kc × ET₀** — Crop evapotranspiration
- **ET₀** via Hargreaves method from weather data
- **Crop Score** = 0.30×N + 0.25×P + 0.20×K + 0.15×pH + 0.10×climate
