# Simbir.Health Backend

Monorepo for the Simbir.Health backend platform on Python + FastAPI.

## Current status

The repository currently contains the bootstrap for the target microservice platform:
- 4 FastAPI microservices;
- shared Python tooling and repository conventions;
- Docker and docker-compose scaffolding;
- PostgreSQL, RabbitMQ, Elasticsearch, Logstash, and Kibana stack definitions;
- GitHub Actions for quality checks, Docker builds, and tagged releases;
- smoke tests for each service;
- planning documents for the next implementation phases.

Current implementation progress:
- `account-service`: implemented with JWT auth, seeded users, account CRUD, doctor directory, and RabbitMQ outbox publication.
- `hospital-service`: implemented with hospital CRUD, room management, and RabbitMQ outbox publication.
- `timetable-service`: implemented with schedule CRUD, slot generation, appointment booking, cross-service reference validation, and RabbitMQ outbox publication.
- `document-service`: implemented with medical history CRUD, patient access rules, Elasticsearch-backed search, cross-service reference validation, RabbitMQ outbox publication, and asynchronous search indexing consumer.
- Shared event contracts and contract tests are implemented for all published RabbitMQ payloads.

## Services

1. Account URL: http://localhost:8081/ui-swagger
2. Hospital URL: http://localhost:8082/ui-swagger
3. Timetable URL: http://localhost:8083/ui-swagger
4. Document URL: http://localhost:8084/ui-swagger

## Search and observability

1. ElasticSearch URL: http://localhost:9200/
2. Kibana URL: http://localhost:5601/
3. Logstash TCP input: localhost:5000

## Stack

- Python 3.11
- FastAPI
- PostgreSQL
- RabbitMQ
- Elasticsearch
- Logstash
- Kibana
- Alembic migrations
- Docker / docker-compose
- GitHub Actions
- pytest / ruff / black / mypy

## Repository structure

```text
.
+- services/
|  +- account_service/
|  +- hospital_service/
|  +- timetable_service/
|  L- document_service/
+- libs/contracts/
+- libs/service_common/
+- deploy/
+- plans/
+- requirements/
L- .github/workflows/
```

## Local development

1. Create a Python 3.11 virtual environment.
2. Install dependencies:
   `pip install -r requirements/dev.txt`
3. Run tests:
   `pytest`
4. Start the full local stack:
   `docker-compose up -d`

## Migrations

- Table schema is managed by `Alembic` in each service directory.
- On startup, every service runs `alembic upgrade head` before serving requests.
- [deploy/postgres/init/01-create-databases.sql](D:/Study/codex/ai-test/deploy/postgres/init/01-create-databases.sql) only creates PostgreSQL databases; it does not create application tables.
- Initial revisions live under:
  `services/account_service/migrations/versions/0001_initial.py`
  `services/hospital_service/migrations/versions/0001_initial.py`
  `services/timetable_service/migrations/versions/0001_initial.py`
  `services/document_service/migrations/versions/0001_initial.py`

## Service interaction

- `timetable-service` validates doctors through `account-service` and validates hospitals and rooms through `hospital-service`.
- `account-service` publishes `account.created.v1`, `account.updated.v1`, and `account.deleted.v1` through RabbitMQ using an outbox table.
- `timetable-service` publishes `timetable.created.v1`, `timetable.updated.v1`, `timetable.deleted.v1`, `appointment.created.v1`, and `appointment.deleted.v1` through RabbitMQ using an outbox table.
- `document-service` validates patients and doctors through `account-service` and validates hospitals and rooms through `hospital-service`.
- `hospital-service` publishes `hospital.created.v1`, `hospital.updated.v1`, and `hospital.deleted.v1` through RabbitMQ using an outbox table.
- `document-service` publishes `history.created.v1` and `history.updated.v1` through RabbitMQ using an outbox table.
- `document-service` consumes its history events from RabbitMQ and updates the Elasticsearch search index asynchronously.
- Shared RabbitMQ payload schemas live in `libs/contracts` and are verified by contract tests.
- Internal service-to-service contracts are protected with `X-Internal-Token`.

## Versioning and releases

- Version source: `VERSION`
- Changelog format: `Keep a Changelog`
- Versioning strategy: `Semantic Versioning`
- Git tags format: `vMAJOR.MINOR.PATCH`

## Seeded users

- `admin / admin` -> `Admin`
- `manager / manager` -> `Manager`
- `doctor / doctor` -> `Doctor`
- `user / user` -> `User`

## Planning documents

- `plans/001_requirements_analysis.md`
- `plans/002_architecture_and_delivery_plan.md`
- `plans/003_production_readiness_plan.md`
- `plans/004_execution_backlog.md`
