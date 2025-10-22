# backend/app/db/base.py
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
Base declarativa de SQLAlchemy.
Solo exporta Base - los modelos se importan directamente donde se necesiten.
"""
from app.db.session import Base

__all__ = ["Base"]
