from libs.service_common.versioning import read_version
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "timetable-service"
    service_title: str = "Simbir.Health Timetable Service"
    service_description: str = "Doctor timetable and appointments microservice."
    service_env: str = "local"
    docs_url: str = "/ui-swagger"
    openapi_url: str = "/openapi.json"
    api_prefix: str = "/api"
    service_version: str = read_version()
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/timetable_db",
        alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(default="local-account-service-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    internal_api_key: str = Field(default="local-internal-api-key", alias="INTERNAL_API_KEY")
    account_service_url: str = Field(default="http://localhost:8081", alias="ACCOUNT_SERVICE_URL")
    hospital_service_url: str = Field(default="http://localhost:8082", alias="HOSPITAL_SERVICE_URL")
    rabbitmq_url: str = Field(default="memory://timetable-events", alias="RABBITMQ_URL")
    logstash_host: str = Field(default="", alias="LOGSTASH_HOST")
    logstash_port: int = Field(default=5000, alias="LOGSTASH_PORT")
    timetable_events_exchange: str = "simbir.health.events"
    rabbitmq_dead_letter_exchange: str = Field(
        default="simbir.health.events.dlx",
        alias="RABBITMQ_DEAD_LETTER_EXCHANGE",
    )
    hospital_cleanup_queue_name: str = "timetable-service.hospital-cleanup.v1"
    hospital_cleanup_dead_letter_queue_name: str = Field(
        default="timetable-service.hospital-cleanup.dlq.v1",
        alias="HOSPITAL_CLEANUP_DEAD_LETTER_QUEUE_NAME",
    )
    outbox_poll_interval_seconds: float = 0.1
    outbox_batch_size: int = 50
