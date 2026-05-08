# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Crée l'engine PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # Mettre à True pour voir les requêtes SQL
    pool_pre_ping=True
)

# SessionLocal = factory pour créer des sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    """
    Dépendance FastAPI — yield une session et ferme proprement.
    Utilisée dans tous les endpoints : Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()