from typing import List, Union
from decimal import Decimal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    PROJECT_NAME: str = "Pluxee Enterprise HR Suite Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_V1_STR: str = "/api/v1"
    CATEGORY_GLOBAL_BUDGET_CAP: Decimal = Decimal("45000.00")

    # SQLite Database Configuration
    DATABASE_URL: str = "sqlite:///./db.sqlite3"

    # CORS Configuration (allows frontend development servers)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5500",
         "http://localhost:5500"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Cloudinary Storage Configuration (Receipt uploads)
    CLOUDINARY_CLOUD_NAME: str = "dxooutyum"
    CLOUDINARY_API_KEY: str = "113547718117145"
    CLOUDINARY_API_SECRET: str = "gYI_D_XOoyiSzLdQC1_9rMXF_sY"

    # GenAI / Google Genkit Configuration
    GEMINI_API_KEY: str = ""
    GENKIT_API_KEY: str = ""
    GENKIT_MODEL: str = "googleai/gemini-2.0-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
