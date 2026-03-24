# Environment Profiles

## Supported service profiles

All services now support exactly these `SERVICE_ENV` values:
- `local`
- `ci`
- `staging`
- `production`

Any other value is rejected during application startup.

## Profile intent

### `local`
- used for developer machines;
- usually launched through root [docker-compose.yml](D:/Study/codex/ai-test/docker-compose.yml);
- may use explicit local development secrets;
- exposes service ports and full supporting stack locally.

### `ci`
- used for GitHub Actions and disposable verification environments;
- should avoid external log shipping;
- uses deterministic test-oriented secrets;
- recommended compose overlay:
  [docker-compose.ci.yml](D:/Study/codex/ai-test/deploy/compose/docker-compose.ci.yml)

### `staging`
- production-like verification environment;
- must not use local default secrets;
- requires explicit `JWT_SECRET_KEY` and `INTERNAL_API_KEY`;
- recommended compose overlay:
  [docker-compose.staging.yml](D:/Study/codex/ai-test/deploy/compose/docker-compose.staging.yml)

### `production`
- real deployment profile;
- must not use local default secrets;
- must use externally supplied secrets;
- should follow deployment manifests strategy instead of relying on local compose files.

## Compose strategy

Baseline:
- [docker-compose.yml](D:/Study/codex/ai-test/docker-compose.yml) is the local baseline stack.

Overrides:
- CI: `docker compose -f docker-compose.yml -f deploy/compose/docker-compose.ci.yml config`
- Staging: `docker compose -f docker-compose.yml -f deploy/compose/docker-compose.staging.yml config`

Production posture:
- use the same environment contract and image set;
- render environment-specific deployment manifests in the target platform;
- do not depend on committed local compose overrides for secret management.

## Required environment variables by profile

Common to all profiles:
- `SERVICE_ENV`
- `DATABASE_URL`
- `RABBITMQ_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `INTERNAL_API_KEY`

Additional for `timetable-service` and `document-service`:
- `ACCOUNT_SERVICE_URL`
- `HOSPITAL_SERVICE_URL`

Additional for `document-service`:
- `ELASTICSEARCH_URL`
- `SEARCH_INDEX_ALIAS`
- `SEARCH_INDEX_PREFIX`

Optional observability variables:
- `LOGSTASH_HOST`
- `LOGSTASH_PORT`

## Ports in local profile

- `8081` account-service
- `8082` hospital-service
- `8083` timetable-service
- `8084` document-service
- `5432` PostgreSQL
- `5672` RabbitMQ
- `15672` RabbitMQ management
- `9200` Elasticsearch
- `5000` Logstash TCP input
- `5601` Kibana

## Stateful dependencies

Persistent data in local compose:
- PostgreSQL volume: `postgres_data`
- Elasticsearch volume: `elasticsearch_data`

Operational dependencies:
- PostgreSQL for all four services
- RabbitMQ for async messaging
- Elasticsearch for document search
- Logstash and Kibana for observability in local/staging-style runs
