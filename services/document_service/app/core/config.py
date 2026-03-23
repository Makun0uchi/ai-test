from libs.service_common.versioning import read_version
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "document-service"
    service_title: str = "Simbir.Health Document Service"
    service_description: str = "Medical history and document search microservice."
    service_env: str = "local"
    docs_url: str = "/ui-swagger"
    openapi_url: str = "/openapi.json"
    api_prefix: str = "/api"
    service_version: str = read_version()
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/document_db",
        alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(default="local-account-service-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    elasticsearch_url: str = Field(default="memory://history", alias="ELASTICSEARCH_URL")
    search_index_name: str = "history-records-v1"
