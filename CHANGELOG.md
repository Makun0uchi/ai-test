# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
