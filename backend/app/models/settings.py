from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.db.base import Base


class AppSetting(Base):
    """
    Stockage clé-valeur des paramètres applicatifs configurables depuis l'admin.
    Remplace les constantes figées dans config.py pour les seuils monétaires.
    """
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Float, nullable=False)
    label = Column(String(200), nullable=True)
    description = Column(String(500), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<AppSetting(key={self.key}, value={self.value})>"
