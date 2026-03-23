from functools import lru_cache

from libs.service_common.versioning import read_version
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "hospital-service"
    service_title: str = "Simbir.Health Hospital Service"
    service_description: str = "Hospitals and rooms microservice."
    service_env: str = "local"
    docs_url: str = "/ui-swagger"
    openapi_url: str = "/openapi.json"
    api_prefix: str = "/api"
    service_version: str = read_version()


@lru_cache
def get_settings() -> Settings:
    return Settings()
