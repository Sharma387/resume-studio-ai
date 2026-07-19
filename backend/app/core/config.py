from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "Resume Studio AI"
    app_version: str = "0.1.0"
    debug: bool = False

    omniroute_api_url: str = "https://api.omniroute.ai/v1/chat/completions"
    omniroute_api_key: str = ""
    omniroute_model: str = "omniroute-v1"
    omniroute_timeout: int = 60
    omniroute_max_retries: int = 1


settings = Settings()
