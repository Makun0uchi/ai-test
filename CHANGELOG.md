# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
