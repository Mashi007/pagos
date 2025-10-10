# app/db/session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ✅ Lectura lazy de DATABASE_URL
def get_database_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("❌ DATABASE_URL no está configurada")
    return url

# ✅ No crear engine en tiempo de importación
engine = None
SessionLocal = None
Base = declarative_base()

def init_db():
    """Inicializa la conexión a la base de datos"""
    global engine, SessionLocal
    
    if engine is None:
        database_url = get_database_url()
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine

def get_db():
    """Dependency para obtener sesión de BD"""
    if SessionLocal is None:
        init_db()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
