from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres@localhost:5432/logistica"
    artifacts_dir: Path = BASE_DIR / "app" / "ml" / "artifacts"
    retreino_min_amostras: int = 100  # mínimo de novas entregas para disparar retreino
    secret_key: str = "troque-esta-chave-em-producao"
    access_token_expire_minutes: int = 60


settings = Settings()