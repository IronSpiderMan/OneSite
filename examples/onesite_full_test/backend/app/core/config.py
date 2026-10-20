from pydantic_settings import BaseSettings
from typing import Optional, List, Any
from pydantic import field_validator, AnyHttpUrl

class Settings(BaseSettings):
    PROJECT_NAME: str = "onesite_full_test"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "changeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 11520
    DATABASE_URI: str = "sqlite:///./app.db"
    FIRST_SUPERUSER: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin"
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Upload config
    UPLOAD_DIR: str = "uploads"

    # Global Resources
    
    
    

    

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            if not v.startswith("["):
                return [i.strip() for i in v.split(",")]
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Fallback or let Pydantic handle it?
                # If valid JSON fails (unlikely if starts with [), return as is?
                return []
        elif isinstance(v, list):
            return v
        raise ValueError(v)

    class Config:
        env_file = ".env"
        extra = "ignore" # Ignore extra env vars

settings = Settings()