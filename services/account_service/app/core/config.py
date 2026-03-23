from libs.service_common.versioning import read_version
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "account-service"
    service_title: str = "Simbir.Health Account Service"
    service_description: str = "Authentication and account management microservice."
    service_env: str = "local"
    docs_url: str = "/ui-swagger"
    openapi_url: str = "/openapi.json"
    api_prefix: str = "/api"
    service_version: str = read_version()
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/account_db",
        alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(default="local-account-service-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
