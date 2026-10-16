from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

# Valores de exemplo conhecidos publicamente — nunca podem ser usados para assinar JWTs.
SECRET_KEYS_PROIBIDAS = {
    "troque-esta-chave-em-producao",                              # antigo default do código
    "troque-esta-chave-por-um-valor-aleatorio-longo-em-producao",  # placeholder do .env.example
}
SECRET_KEY_TAMANHO_MINIMO = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres@localhost:5432/logistica"
    artifacts_dir: Path = BASE_DIR / "app" / "ml" / "artifacts"
    retreino_min_amostras: int = 100  # mínimo de novas entregas para disparar retreino
    secret_key: str  # obrigatória: sem default, a aplicação não sobe sem SECRET_KEY
    access_token_expire_minutes: int = 60

    @field_validator("secret_key")
    @classmethod
    def _validar_secret_key(cls, v: str) -> str:
        """Recusa a inicialização com chave curta ou igual a um placeholder conhecido."""
        if v in SECRET_KEYS_PROIBIDAS:
            raise ValueError(
                "SECRET_KEY ainda é o valor de exemplo; gere uma com: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        if len(v) < SECRET_KEY_TAMANHO_MINIMO:
            raise ValueError(
                f"SECRET_KEY deve ter pelo menos {SECRET_KEY_TAMANHO_MINIMO} caracteres"
            )
        return v


settings = Settings()
