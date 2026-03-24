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
    internal_api_key: str = Field(default="local-internal-api-key", alias="INTERNAL_API_KEY")
    account_service_url: str = Field(default="http://localhost:8081", alias="ACCOUNT_SERVICE_URL")
    hospital_service_url: str = Field(default="http://localhost:8082", alias="HOSPITAL_SERVICE_URL")
    rabbitmq_url: str = Field(default="memory://history-events", alias="RABBITMQ_URL")
    logstash_host: str = Field(default="", alias="LOGSTASH_HOST")
    logstash_port: int = Field(default=5000, alias="LOGSTASH_PORT")
    history_events_exchange: str = "simbir.health.events"
    rabbitmq_dead_letter_exchange: str = Field(
        default="simbir.health.events.dlx",
        alias="RABBITMQ_DEAD_LETTER_EXCHANGE",
    )
    history_indexer_queue_name: str = "document-service.history-indexer.v1"
    history_indexer_dead_letter_queue_name: str = Field(
        default="document-service.history-indexer.dlq.v1",
        alias="HISTORY_INDEXER_DEAD_LETTER_QUEUE_NAME",
    )
    outbox_poll_interval_seconds: float = 0.1
    outbox_batch_size: int = 50
    elasticsearch_url: str = Field(default="memory://history", alias="ELASTICSEARCH_URL")
    search_index_name: str = "history-records-v1"
