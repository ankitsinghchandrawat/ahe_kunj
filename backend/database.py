"""
database.py
───────────
SQLite Database Connection & Session Management for KrishiMind v3

Usage:
    from database import get_db, engine, log_activity
    from models import Base
    Base.metadata.create_all(bind=engine)
"""

import os
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH     = os.path.join(BASE_DIR, "agriculture.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def log_activity(agent_name: str, query: dict, result: dict, farmer_id: int = None):
    """
    Write an audit entry to activity_logs.
    Safe to call without an active request context.
    """
    from models import ActivityLog
    db = SessionLocal()
    try:
        entry = ActivityLog(
            farmer_id   = farmer_id,
            agent_name  = agent_name,
            query_json  = json.dumps(query,  ensure_ascii=False, default=str),
            result_json = json.dumps(result, ensure_ascii=False, default=str),
            timestamp   = datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB] log_activity error: {e}")
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist."""
    from models import Base
    Base.metadata.create_all(bind=engine)
    print(f"[DB] agriculture.db ready at {DB_PATH}")
