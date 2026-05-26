import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


# ── Seuils monétaires LBC/FT — configurables via .env ──────────────────
# Justification : simplification intentionnelle de seuils absolus pour
# la soutenance. En production réelle, le seuil serait relatif aux
# revenus déclarés du client (profil personnalisé).
SEUIL_MONETAIRE: float = float(os.getenv("SEUIL_MONETAIRE", "10000000"))
SEUIL_ESPECES: float = float(os.getenv("SEUIL_ESPECES", "3000000"))
FENETRE_CUMUL_JOURS: int = int(os.getenv("FENETRE_CUMUL_JOURS", "30"))
BENEFICIAIRE_MIN_CLIENTS: int = int(os.getenv("BENEFICIAIRE_MIN_CLIENTS", "2"))
BENEFICIAIRE_MIN_TRANSACTIONS: int = int(os.getenv("BENEFICIAIRE_MIN_TRANSACTIONS", "5"))
BENEFICIAIRE_MIN_MONTANT: float = float(os.getenv("BENEFICIAIRE_MIN_MONTANT", "5000000"))


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG: bool = False
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore",
    )

    @model_validator(mode="after")
    def _fail_fast_on_missing_secrets(self):
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required — check .env file")
        if self.SECRET_KEY in ("", "dev_secret_key_change_in_production", "change_me_generate_a_random_key"):
            raise ValueError(
                "SECRET_KEY is weak or missing — generate a strong key with: openssl rand -hex 32"
            )
        if self.DEBUG and "localhost" not in self.DATABASE_URL and "127.0.0.1" not in self.DATABASE_URL:
            raise ValueError("DEBUG=true is not allowed with a remote database")
        return self


settings = Settings()
