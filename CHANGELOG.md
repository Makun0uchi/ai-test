# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.19.0] - 2026-03-24

### Added
- Added `POST /api/History/Search/Reindex` in `document-service` for admin-triggered full search rebuilds from PostgreSQL.
- Added alias-backed Elasticsearch rebuild support in `services/document_service/app/search/elasticsearch_gateway.py` with versioned physical index names.
- Added `docs/runbooks/search_reindex.md` and regression coverage for search rebuild behavior, including an Elasticsearch gateway unit test.

### Changed
- `document-service` search bootstrap now creates or rebuilds the projection through the shared search gateway contract instead of reindexing every startup blindly.
- Search configuration now distinguishes a logical alias from a physical index prefix.
- The execution backlog now marks search reindex and maintenance tooling as completed.

## [0.18.0] - 2026-03-24

### Added
- Added dead-letter queue support to the shared RabbitMQ and in-memory consumer infrastructure.
- Added RabbitMQ reliability runbook in `docs/runbooks/rabbitmq_reliability.md`.
- Added regression coverage for dead-letter routing in `tests/test_event_consumers.py`.

### Changed
- RabbitMQ consumer failures no longer use endless `requeue=true`; failed events are now routed to dedicated DLQs for controlled replay.
- `document-service` and `timetable-service` now declare per-consumer dead-letter queue names through settings.
- The production execution backlog now marks the RabbitMQ reliability policy task as completed.

## [0.17.0] - 2026-03-24

### Added
- Added production-oriented release automation in `.github/workflows/release.yml` with explicit `contents: write` and `packages: write` permissions.
- Added tagged image publishing to `ghcr.io` for all four microservices during release runs.
- Added `scripts/extract_release_notes.py` and `tests/test_release_notes.py` so GitHub Releases are generated from the matching `CHANGELOG` section instead of the failing `generate_release_notes` API path.

### Changed
- Reworked the `release` workflow to stop relying on `generate_release_notes`, which was failing with `403 Resource not accessible by integration`.
- The execution backlog now marks release automation as completed.

## [0.16.0] - 2026-03-24

### Added
- Added request correlation ID middleware for all four services with `X-Correlation-ID` echoing and structured request completion logs.
- Added correlation ID persistence in every outbox table and propagated correlation metadata through RabbitMQ publishers, subscribers, and background consumers.
- Added optional Logstash TCP shipping configuration so structured service logs can be forwarded into ELK in the docker environment.
- Added regression tests for correlation header forwarding, response header echoing, correlation-aware outbox publication, and migration coverage for the new outbox column.

### Changed
- Internal HTTP reference validation now forwards the active correlation ID to downstream internal service calls.
- Event publication and consumption logs now include correlation ID, event type, routing key, aggregate type, aggregate ID, and queue metadata.

## [0.15.0] - 2026-03-24

### Added
- Added a full end-to-end workflow test in `tests/test_end_to_end_flow.py` that boots all four FastAPI microservices together, uses real internal HTTP validation, books an appointment, writes history, and verifies searchable output.

### Changed
- The production execution backlog now marks the P0 end-to-end workflow scenario as completed.

## [0.14.0] - 2026-03-24

### Added
- Added shared RabbitMQ consumer infrastructure in `libs/service_common.messaging`, including in-memory topic subscriptions, generic RabbitMQ topic subscribers, typed payload parsing, and background consumer helpers.
- Added a real cross-service consumer flow where `timetable-service` consumes `hospital.deleted.v1` and asynchronously removes related timetables.
- Added consumer tests covering message filtering, failure tracking, and the end-to-end `hospital-service -> RabbitMQ -> timetable-service` cleanup flow.

### Changed
- Refactored account, hospital, timetable, and document event publishers to use the shared messaging layer instead of service-local RabbitMQ adapter implementations.
- Refactored `document-service` history indexer to run through the shared consumer infrastructure and typed event parsing helpers.

## [0.13.1] - 2026-03-24

### Added
- Added a production-readiness roadmap in `plans/003_production_readiness_plan.md`.
- Added an execution backlog in `plans/004_execution_backlog.md` with P0/P1/P2 prioritization and release criteria.

## [0.13.0] - 2026-03-24

### Added
- Added shared event contracts in `libs/contracts` for account, hospital, timetable, appointment, and history payloads.
- Added cross-service contract tests validating real published events against shared schemas.

### Changed
- Event payload serialization in all four services now uses shared typed contracts instead of ad-hoc dictionaries.
- `document-service` history indexer now parses history events through a typed contract before indexing Elasticsearch documents.

## [0.12.0] - 2026-03-24

### Added
- Added outbox-based domain event publication to `account-service`.
- Added RabbitMQ publisher and background dispatcher for account lifecycle events.
- Added API tests covering event publication for sign-up, self-update, and admin account CRUD flows.

### Changed
- `account-service` now writes account mutations and outbox events in the same transaction while keeping seed users event-free.

## [0.11.0] - 2026-03-24

### Added
- Added outbox-based domain event publication to `timetable-service`.
- Added RabbitMQ publisher and background dispatcher for timetable and appointment events.
- Added API tests covering event publication for timetable CRUD, appointment booking, and bulk timetable cleanup flows.

### Changed
- `timetable-service` now writes schedule and appointment mutations together with outbox events in the same transaction.

## [0.10.0] - 2026-03-24

### Added
- Added outbox-based domain event publication to `hospital-service`.
- Added RabbitMQ publisher and background dispatcher for `hospital.created.v1`, `hospital.updated.v1`, and `hospital.deleted.v1`.
- Added API tests covering hospital event publication and migration coverage for the new outbox table.

### Changed
- `hospital-service` now writes hospital CRUD changes and outbox events in the same transaction.

## [0.9.0] - 2026-03-24

### Added
- Added a background RabbitMQ subscriber in `document-service` to consume `history.created.v1` and `history.updated.v1` events.
- Added a search indexer worker that rebuilds Elasticsearch documents from published history events.

### Changed
- `document-service` now uses versioned routing keys per history event instead of a shared `history.changed.v1` key.
- Search indexing is no longer performed inside the history write path and now runs through the outbox and message consumer pipeline.

## [0.8.0] - 2026-03-24

### Added
- Added `history_index_outbox` support in `document-service` for reliable history event publication.
- Added background outbox dispatcher and RabbitMQ publisher for `history.created.v1` and `history.updated.v1` events.
- Added in-memory event publisher for tests and API tests covering outbox publication.

### Changed
- `document-service` now writes history records and outbox events in the same transaction.
- Synchronous Elasticsearch indexing remains as a fallback while event-driven infrastructure is introduced incrementally.

## [0.7.0] - 2026-03-24

### Added
- Added Alembic-based migration support for all four microservices.
- Added versioned initial revisions for `account-service`, `hospital-service`, `timetable-service`, and `document-service`.
- Added a shared migration runner and migration smoke tests to verify schema bootstrap from revisions.

### Changed
- Replaced startup-time `create_all()` schema bootstrap with `alembic upgrade head` on service startup.
- Clarified repository documentation so PostgreSQL database creation and table migrations are separated cleanly.

## [0.6.0] - 2026-03-24

### Added
- Added protected internal HTTP contracts in `account-service` and `hospital-service` for service-to-service reference validation.
- Added shared internal reference validator client for synchronous cross-service checks.
- Added write-path validation in `timetable-service` for doctor, hospital, and room references.
- Added write-path validation in `document-service` for patient, doctor, hospital, and room references.
- Added tests for internal contracts and cross-service validation flows, plus shared client tests with mocked upstream services.

## [0.5.0] - 2026-03-24

### Added
- Implemented the functional `document-service` with medical history create, update, read, and patient listing flows.
- Added PostgreSQL-backed SQLAlchemy models and layered router-service-repository-model structure for history records.
- Added Elasticsearch indexing and filtered full-text search for medical history documents with an in-memory search fallback for tests.
- Added JWT-based authorization rules for patient self-access and elevated staff editing scenarios.
- Added API tests for document creation, updates, per-patient access control, and search restrictions.

## [0.4.0] - 2026-03-24

### Added
- Implemented the functional `timetable-service` with timetable CRUD, slot listing, and appointment booking flows.
- Added timetable interval validation for 30-minute alignment, ordering, 12-hour limit, and overlap protection.
- Added persistent SQLAlchemy models for timetables and appointments.
- Added JWT-based authorization for timetable management and patient booking scenarios.
- Added API tests for timetable creation, updates, overlaps, slot booking, duplicate booking rejection, and cleanup by doctor and hospital.

## [0.3.0] - 2026-03-24

### Added
- Implemented the functional `hospital-service` with hospital CRUD and room management endpoints.
- Added PostgreSQL-backed SQLAlchemy models for hospitals and hospital rooms.
- Added JWT-based role checks for hospital management actions.
- Added API tests for hospital creation, reading, updating, deletion, and room validation scenarios.

## [0.2.0] - 2026-03-24

### Added
- Implemented the first functional microservice: `account-service`.
- Added JWT authentication, refresh token rotation, authorization dependencies, and seeded demo users.
- Added account administration endpoints and doctor directory endpoints.
- Added persistent SQLAlchemy models for accounts, roles, and refresh tokens.
- Added integration-style API tests for sign-up, sign-in, me, account CRUD, doctor filtering, validation, refresh, and sign-out flows.

## [0.1.0] - 2026-03-24

### Added
- Added the initial requirements analysis and architecture plan for the Simbir.Health microservice platform.
- Added the monorepo bootstrap for the account, hospital, timetable, and document FastAPI services.
- Added shared Python tooling, Docker bootstrap, docker-compose stack definition, and ELK scaffolding.
- Added GitHub Actions workflows for CI, Docker image builds, and tagged releases.
- Added initial smoke tests and repository versioning metadata.
