# Migration Rollback Runbook

## Purpose

This runbook describes how to inspect and roll back a service database migration when a release introduced an incompatible schema change.

## Scope

Each microservice owns its own database and Alembic migration history:
- `account-service`
- `hospital-service`
- `timetable-service`
- `document-service`

Rollback must be handled per service.

## Preconditions

- identify the exact failing service;
- identify the deployed application version;
- identify the currently applied Alembic revision;
- confirm whether rollback is safe for existing data.

## Important warning

Rollback is safe only if the migration is actually reversible and the application/data changes allow moving backward.
Do not roll back blindly after destructive schema or data transformations.

## Investigation steps

1. Inspect the failing service logs for Alembic or SQL errors.
2. Find the current revision in the target database.
3. Compare it with the expected revision from the service's `migrations/versions`.
4. Identify the target rollback revision.

## Recommended rollback flow

1. Stop or scale down the affected service.
2. Back up the service database.
3. Run Alembic downgrade for that service only.
4. Deploy the matching application version.
5. Start the service and confirm health.

## Service paths

- `services/account_service/alembic.ini`
- `services/hospital_service/alembic.ini`
- `services/timetable_service/alembic.ini`
- `services/document_service/alembic.ini`

## Local command examples

Account service:
- `alembic -c services/account_service/alembic.ini current`
- `alembic -c services/account_service/alembic.ini downgrade -1`

Apply the same pattern to the other services.

## When not to roll back

- when a migration dropped or transformed data that cannot be restored safely;
- when newer application writes depend on the new schema;
- when the faster and safer path is to fix forward with a new migration.

## Exit criteria

The rollback is complete when:
- the database revision matches the intended target;
- the matching application version is deployed;
- service health is restored;
- no migration exception repeats on startup.
