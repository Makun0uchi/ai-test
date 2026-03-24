from libs.service_common.versioning import read_version
from pydantic import Field
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
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/hospital_db",
        alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(default="local-account-service-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    internal_api_key: str = Field(default="local-internal-api-key", alias="INTERNAL_API_KEY")
    rabbitmq_url: str = Field(default="memory://hospital-events", alias="RABBITMQ_URL")
    logstash_host: str = Field(default="", alias="LOGSTASH_HOST")
    logstash_port: int = Field(default=5000, alias="LOGSTASH_PORT")
    hospital_events_exchange: str = "simbir.health.events"
    outbox_poll_interval_seconds: float = 0.1
    outbox_batch_size: int = 50
