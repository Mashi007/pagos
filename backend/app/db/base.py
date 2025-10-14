# backend/app/db/base.py
"""
Base declarativa de SQLAlchemy.
Solo exporta Base - los modelos se importan directamente donde se necesiten.
"""
from app.db.session import Base

__all__ = ["Base"]
