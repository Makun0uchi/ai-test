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
- `timetable-service`: implemented with schedule CRUD, slot generation, appointment booking, cross-service reference validation, RabbitMQ outbox publication, and hospital deletion cleanup consumption.
- `document-service`: implemented with medical history CRUD, patient access rules, Elasticsearch-backed search, alias-based reindex maintenance endpoint, cross-service reference validation, RabbitMQ outbox publication, and asynchronous search indexing consumer.
- Shared event contracts, consumer infrastructure, and contract tests are implemented for all published RabbitMQ payloads.
- A full end-to-end patient visit workflow test now covers all 4 services plus asynchronous search indexing.

## Services

1. Account URL: http://localhost:8081/ui-swagger
2. Hospital URL: http://localhost:8082/ui-swagger
3. Timetable URL: http://localhost:8083/ui-swagger
4. Document URL: http://localhost:8084/ui-swagger

## Search and observability

1. ElasticSearch URL: http://localhost:9200/
2. Kibana URL: http://localhost:5601/
3. Logstash TCP input: localhost:5000

Structured log fields:
- `service`
- `correlation_id`
- `http_method`
- `http_path`
- `status_code`
- `duration_ms`
- `event_type`
- `routing_key`
- `aggregate_type`
- `aggregate_id`
- `queue_name`

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
+- docs/
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

## Environment profiles

- supported `SERVICE_ENV` values are `local`, `ci`, `staging`, `production`;
- root [docker-compose.yml](D:/Study/codex/ai-test/docker-compose.yml) is the local baseline profile;
- CI and staging overrides live in:
  [docker-compose.ci.yml](D:/Study/codex/ai-test/deploy/compose/docker-compose.ci.yml)
  [docker-compose.staging.yml](D:/Study/codex/ai-test/deploy/compose/docker-compose.staging.yml)
- full environment matrix and deployment strategy are documented in [environment_profiles.md](D:/Study/codex/ai-test/docs/environment_profiles.md).

## Migrations

- Table schema is managed by `Alembic` in each service directory.
- On startup, every service runs `alembic upgrade head` before serving requests.
- [01-create-databases.sql](D:/Study/codex/ai-test/deploy/postgres/init/01-create-databases.sql) only creates PostgreSQL databases; it does not create application tables.
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
- `document-service` exposes `POST /api/History/Search/Reindex` for a full PostgreSQL to Elasticsearch rebuild.
- `timetable-service` consumes `hospital.deleted.v1` from RabbitMQ and cleans up related timetables asynchronously.
- Shared RabbitMQ payload schemas live in `libs/contracts` and are verified by contract tests.
- Shared publisher and subscriber primitives live in `libs/service_common.messaging`.
- Consumer failure handling uses dedicated dead-letter queues instead of endless hot requeue loops.
- Every service accepts and returns `X-Correlation-ID`, forwards it through internal HTTP validation, and preserves it in outbox-driven event publication.
- Internal service-to-service contracts are protected with `X-Internal-Token`.

## RabbitMQ reliability policy

- consumer failures are routed to per-consumer dead-letter queues;
- automatic `requeue=true` is intentionally disabled for handler exceptions;
- DLQ messages are retained for manual inspection and controlled replay;
- the current operational runbook lives in [rabbitmq_reliability.md](D:/Study/codex/ai-test/docs/runbooks/rabbitmq_reliability.md).

## Search maintenance policy

- `document-service` uses a logical Elasticsearch alias and versioned physical indices;
- manual rebuild creates a new physical index and atomically switches the alias;
- the current reindex runbook lives in [search_reindex.md](D:/Study/codex/ai-test/docs/runbooks/search_reindex.md);
- reindex should currently be treated as a maintenance operation during a low-write window.

## Operational runbooks

- the runbook index lives in [docs/runbooks/README.md](D:/Study/codex/ai-test/docs/runbooks/README.md);
- covered scenarios now include service startup failure, migration rollback, outbox lag, RabbitMQ reliability, search reindex, and token/key rotation.

## Security posture

- local `docker-compose` now sets JWT and internal tokens explicitly instead of relying on silent defaults;
- `staging` and `production` reject local default `JWT_SECRET_KEY` and `INTERNAL_API_KEY`;
- `staging` and `production` require both secrets to be at least `32` characters;
- the current JWT and internal token strategy is documented in [jwt_strategy.md](D:/Study/codex/ai-test/docs/security/jwt_strategy.md).

## Versioning and releases

- Version source: `VERSION`
- Changelog format: `Keep a Changelog`
- Versioning strategy: `Semantic Versioning`
- Git tags format: `vMAJOR.MINOR.PATCH`
- Release workflow:
  - tag push `v*` publishes all 4 images to `ghcr.io/<owner>/<service>:<tag>`
  - the same workflow creates a GitHub Release from the matching `CHANGELOG` section
  - workflow requires `contents: write` and `packages: write`

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
