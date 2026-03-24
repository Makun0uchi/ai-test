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
- `account-service`: implemented with JWT auth, seeded users, account CRUD, and doctor directory.
- `hospital-service`: implemented with hospital CRUD and room management.
- `timetable-service`: implemented with schedule CRUD, slot generation, appointment booking, and cross-service reference validation.
- `document-service`: implemented with medical history CRUD, patient access rules, Elasticsearch-backed search, and cross-service reference validation.

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
- `document-service` validates patients and doctors through `account-service` and validates hospitals and rooms through `hospital-service`.
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
