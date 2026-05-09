from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # URL pour la connexion depuis l'hôte (votre machine → Docker)
    DATABASE_URL: str = "postgresql://marcos:dev_password_change_in_prod@localhost:5433/scoring_db"
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    DEBUG: bool = True
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()