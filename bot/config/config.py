from typing import ClassVar
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_ignore_empty=True,
        extra='allow'
    )

    API_ID: int
    API_HASH: str

    USE_REF: bool = False
    REF_ID: str = 'T7B3IMWS'

    USE_RANDOM_DELAY_IN_RUN: bool = True
    RANDOM_DELAY_IN_RUN: list[int] = [5, 60]

    PROXY_TYPE: str = 'http'

    USE_PROXY_FROM_FILE: bool = True
    MAX_RETRIES: int = 2


settings = Settings()


