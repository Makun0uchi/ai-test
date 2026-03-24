# Service Startup Failure Runbook

## Purpose

This runbook describes how to diagnose a service that fails to start or restarts continuously.

## Typical symptoms

- container exits immediately after launch;
- health check keeps failing;
- service starts locally but not in CI or staging;
- logs show migration, database, RabbitMQ, or configuration errors.

## First checks

1. Identify the failing service.
2. Read the most recent service logs.
3. Confirm `SERVICE_ENV` is one of:
   - `local`
   - `ci`
   - `staging`
   - `production`
4. Confirm required environment variables are present for the profile.
5. Confirm dependent services are reachable:
   - PostgreSQL
   - RabbitMQ
   - Elasticsearch for `document-service`

## Common failure classes

### Configuration failure

Look for:
- unsupported `SERVICE_ENV`;
- rejected default `JWT_SECRET_KEY` or `INTERNAL_API_KEY` in `staging` or `production`;
- invalid service URLs;
- missing `DATABASE_URL` or `RABBITMQ_URL`.

Recovery:
- fix the environment variables;
- rerun `docker compose config` or the target deployment render step;
- restart the failing service.

### Migration failure

Look for:
- Alembic upgrade errors;
- missing database;
- schema conflict between code and DB state.

Recovery:
- confirm the target database exists;
- inspect the active Alembic version;
- use [migration_rollback.md](D:/Study/codex/ai-test/docs/runbooks/migration_rollback.md) if rollback is required.

### Dependency failure

Look for:
- PostgreSQL not healthy;
- RabbitMQ unavailable;
- Elasticsearch unavailable for `document-service`.

Recovery:
- restore the dependency first;
- then restart the application service.

## Recommended command flow

Local docker:
1. `docker compose ps`
2. `docker compose logs <service-name>`
3. `docker compose logs postgres rabbitmq elasticsearch`
4. `docker compose restart <service-name>`

## Exit criteria

The runbook is complete when:
- the service process stays up;
- health check returns `200`;
- no repeating startup exception appears in logs.
