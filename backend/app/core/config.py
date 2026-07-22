from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Resume Studio AI"
    app_version: str = "0.1.0"
    debug: bool = False

    omniroute_api_url: str = "http://localhost:20128/v1/chat/completions"
    omniroute_api_key: str = ""
    omniroute_model: str = "kiro/claude-haiku-4.5"
    omniroute_timeout: int = 60
    omniroute_max_retries: int = 1

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7


settings = Settings()
