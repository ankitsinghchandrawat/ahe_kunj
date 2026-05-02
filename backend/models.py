"""
models.py
─────────
SQLAlchemy ORM Models for KrishiMind v3

Tables:
  - Farmers       : farmer profile (name, location, soil, season, land)
  - ActivityLogs  : audit trail of every agent call
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class Farmer(Base):
    __tablename__ = "farmers"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name        = Column(String(100), nullable=False)
    location    = Column(String(200), nullable=False, default="India")
    soil_type   = Column(String(50),  nullable=False, default="loamy")
    season      = Column(String(30),  nullable=False, default="Kharif")
    land_acres  = Column(Float,       nullable=False, default=1.0)
    created_at  = Column(DateTime,    default=datetime.utcnow)

    logs = relationship("ActivityLog", back_populates="farmer", cascade="all, delete")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    farmer_id   = Column(Integer, ForeignKey("farmers.id"), nullable=True)
    agent_name  = Column(String(50),  nullable=False)   # crop | irrigation | pest | market | advisory
    query_json  = Column(Text,        nullable=True)
    result_json = Column(Text,        nullable=True)
    timestamp   = Column(DateTime,    default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="logs")


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name            = Column(String(100), nullable=False)
    email           = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    created_at      = Column(DateTime,    default=datetime.utcnow)
