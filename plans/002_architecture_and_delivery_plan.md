# Simbir.Health Backend: architecture and delivery plan

## Planning objective
Deliver the project as a production-style monorepo with:
- `4 FastAPI microservices`;
- `PostgreSQL` with database-per-service ownership;
- `RabbitMQ` for domain events;
- `Elasticsearch + Kibana + Logstash` for search and observability;
- `Dockerfile` for each service and `docker-compose` for the full stack;
- `GitHub Actions` for lint, tests, image build, and release automation;
- mandatory test coverage at unit, integration, contract, and end-to-end levels;
- disciplined `CHANGELOG`, semantic tags, and GitHub releases.

## Chosen technical approach

### Why this communication model
To keep the architecture both realistic and implementable in Python:
- use `HTTP` for synchronous request-time validations;
- use `RabbitMQ` for domain events and eventual consistency;
- do not introduce `gRPC` in the first iteration unless a specific performance bottleneck appears.

This gives a clean balance:
- predictable request flows;
- decoupled updates between services;
- a clear place to hook Elasticsearch indexing and audit logging.

## Target repository structure

```text
.
├─ services/
│  ├─ account-service/
│  ├─ hospital-service/
│  ├─ timetable-service/
│  └─ document-service/
├─ libs/
│  ├─ contracts/
│  ├─ auth/
│  ├─ messaging/
│  ├─ observability/
│  └─ testing/
├─ deploy/
│  ├─ docker/
│  ├─ compose/
│  └─ elk/
├─ plans/
├─ .github/
│  └─ workflows/
├─ CHANGELOG.md
└─ README.md
```

## Internal structure of each FastAPI microservice
Each service should follow the required adapted MVC layering:

```text
app/
├─ main.py
├─ core/
│  ├─ config.py
│  ├─ security.py
│  ├─ logging.py
│  └─ dependencies.py
├─ routers/
├─ schemas/
├─ services/
├─ repositories/
├─ models/
├─ clients/
├─ events/
└─ migrations/
```

Layer responsibilities:
- `routers`: HTTP contract, auth guards, request/response models.
- `services`: business rules and orchestration.
- `repositories`: database access and query logic.
- `models`: ORM models and persistence definitions.
- `clients`: calls to other services.
- `events`: publish/consume domain events.

## Bounded context plan

### Account service
Owns:
- user accounts;
- roles;
- password hashing;
- refresh tokens;
- doctor listing;
- JWT issuing and validation.

Proposed tables:
- `accounts`
- `roles`
- `account_roles`
- `refresh_tokens`
- `auth_audit_log`

Key design decisions:
- use `RS256` JWT signing so other services can verify access tokens safely;
- provide `/Validate` because it is part of the required contract;
- keep refresh token rotation and token revocation in the account domain.

### Hospital service
Owns:
- hospitals;
- room list per hospital.

Proposed tables:
- `hospitals`
- `hospital_rooms`

Key design decisions:
- room names are unique inside a hospital;
- service publishes events on hospital creation/update/deletion so dependent services can refresh read models.

### Timetable service
Owns:
- timetable ranges;
- appointments;
- slot generation rules.

Proposed tables:
- `timetables`
- `appointments`

Core invariants:
- time range must be aligned to 30 minutes;
- `to > from`;
- maximum duration `12 hours`;
- no overlapping timetable ranges for the same doctor and hospital room combination;
- appointment booking must be concurrency-safe.

Concurrency plan:
- use transactional row locking or optimistic versioning on appointment creation;
- add unique constraints preventing double booking of the same slot.

### Document service
Owns:
- medical history records;
- search indexing pipeline for history content.

Proposed tables:
- `history_records`
- `history_index_outbox`

Key design decisions:
- store canonical medical history in PostgreSQL;
- index searchable projection in Elasticsearch;
- use an outbox pattern so PostgreSQL write and index event emission stay reliable.

## Database strategy

### PostgreSQL ownership
Use one PostgreSQL server in local `docker-compose`, but **separate databases or schemas per service**:
- `account_db`
- `hospital_db`
- `timetable_db`
- `document_db`

Reason:
- preserves microservice ownership;
- keeps local deployment simple;
- avoids accidental cross-service joins.

### Migrations
Use `Alembic` inside each service:
- one migration history per service;
- migrations run automatically on container startup or through a dedicated migration command.

## Inter-service communication plan

### Synchronous HTTP flows
Use direct HTTP clients for request-time validation:
- timetable service validates `doctorId` against account service;
- timetable service validates `hospitalId` and room against hospital service;
- document service validates `pacientId` and `doctorId` against account service;
- document service validates `hospitalId` against hospital service.

This is necessary where immediate consistency matters for the write path.

### Asynchronous RabbitMQ flows
Publish domain events for:
- account created/updated/deleted;
- doctor role assigned or removed;
- hospital created/updated/deleted;
- timetable created/updated/deleted;
- appointment created/deleted;
- history record created/updated.

Consumers use these events to:
- maintain denormalized read models where useful;
- update search indexes;
- emit audit/logging events;
- reduce future tight coupling.

### Event transport details
Initial pragmatic choice:
- RabbitMQ topic exchange;
- versioned routing keys, for example:
  - `account.user.created.v1`
  - `hospital.updated.v1`
  - `history.updated.v1`

## Authentication and authorization plan

### Authentication
- account service is the only token issuer;
- passwords hashed with `passlib` and `bcrypt` or `argon2`;
- access + refresh token pair;
- JWT contains:
  - `sub`
  - `username`
  - `roles`
  - `exp`
  - `jti`

### Authorization
Define a role access matrix before implementation of routers:

Initial safe matrix:
- `Admin`: full account administration, read access everywhere.
- `Manager`: hospitals CRUD, timetable management, operational access to records.
- `Doctor`: doctor schedule view, appointment context, create/update history records.
- `User`: own profile, own history, appointment booking, limited reads.

This matrix should be formalized in a dedicated plan artifact during service implementation.

## Elasticsearch search plan

### Search scope
Index medical history records from the document service.

Searchable fields:
- `data` full text;
- `doctorId`
- `hospitalId`
- `pacientId`
- `room`
- `date`
- optional denormalized doctor/hospital names for better usability.

### Index design
Create a dedicated index alias, for example:
- write alias: `history-write`
- read alias: `history-read`
- concrete index: `history-v1`

Recommended mapping:
- `data`: `text` with Russian analyzer;
- keyword subfields for exact match;
- `date`: `date`;
- IDs: `integer` or `keyword`;
- denormalized names: `text` + `keyword`.

### Query capabilities
Planned search API addition in document service:
- `GET /api/History/Search`

Parameters:
- `query`
- `pacientId`
- `doctorId`
- `hospitalId`
- `dateFrom`
- `dateTo`
- `page`
- `size`
- `sort`

Why add it:
- the PDF explicitly demands Elasticsearch-based document search;
- the listed `History` endpoints alone do not expose a search interface.

### Relevance strategy
To make the search actually useful:
- use Russian analyzer for stemming;
- boost exact filters over generic text match;
- combine full-text query with structured filters;
- sort by relevance first, then by date desc;
- store only search projection fields, not full relational state.

### Index consistency strategy
Recommended path:
- write document to PostgreSQL;
- insert outbox record in the same transaction;
- background consumer publishes index update event;
- indexing worker updates Elasticsearch.

This avoids silent divergence between PostgreSQL and Elasticsearch.

## ELK observability plan

### Stack
- `Elasticsearch`
- `Logstash`
- `Kibana`

### Logging strategy
All services emit JSON logs with:
- timestamp;
- service name;
- environment;
- request id / correlation id;
- user id when available;
- log level;
- event name;
- error details.

Pipeline:
- service stdout -> Docker logging -> Logstash -> Elasticsearch -> Kibana.

Use separate index patterns:
- `logs-*` for observability;
- `history-*` for business search data.

## API and documentation plan
- each service exposes Swagger at `/ui-swagger`;
- service OpenAPI JSON stays enabled for test/contract verification;
- README will document:
  - startup steps;
  - services and ports;
  - test commands;
  - seeded users;
  - Elasticsearch and Kibana URLs;
  - release/versioning policy.

## Docker and local deployment plan

### Containers in docker-compose
- `account-service`
- `hospital-service`
- `timetable-service`
- `document-service`
- `postgres`
- `rabbitmq`
- `elasticsearch`
- `logstash`
- `kibana`

Optional later:
- `nginx` or `traefik` as a convenience gateway, but not required for acceptance.

### Local startup expectations
One command:

```bash
docker-compose up -d
```

Startup flow:
- infrastructure comes up first;
- migrations run;
- seed users are created idempotently;
- services become healthy;
- Swagger is available on `8081-8084`.

## Testing strategy

### Test types required before the first complete release
For every service:
- unit tests for services, validators, policies, and helpers;
- repository integration tests against PostgreSQL;
- API tests against FastAPI endpoints;
- auth/permission tests;
- migration smoke tests.

Cross-service:
- contract tests for HTTP clients and event payloads;
- end-to-end tests for main business scenarios in docker-compose.

Search:
- integration tests for PostgreSQL -> outbox -> RabbitMQ -> Elasticsearch indexing;
- search relevance tests for filtering and full-text results.

### Recommended tooling
- `pytest`
- `pytest-asyncio`
- `httpx`
- `testcontainers-python`
- `factory-boy` or lightweight fixtures
- `freezegun` where time-sensitive logic matters

### Minimum acceptance scenarios
1. Sign up and sign in return valid JWT tokens.
2. Admin can create manager/doctor/user accounts.
3. Manager can create a hospital and its rooms.
4. Manager can create a timetable for a doctor in a hospital room.
5. User can book an appointment in a free slot but not in an occupied slot.
6. Doctor can create a history record for a patient visit.
7. History record becomes searchable in Elasticsearch.
8. User can access only own history.
9. Invalid timetable intervals are rejected.
10. Full stack starts successfully with `docker-compose up -d`.

## CI/CD plan with GitHub Actions

### Workflow set
1. `ci.yml`
- install dependencies;
- run `ruff`, `black --check`, `mypy`;
- run unit and API tests;
- run selected integration tests.

2. `docker.yml`
- build all service images on push/PR;
- optionally push tagged images to `Docker Hub` or `GHCR`.

3. `release.yml`
- trigger on git tag `v*`;
- build and publish images;
- create GitHub Release;
- attach generated release notes from changelog sections.

### Branch and merge quality gates
Before merge:
- lint passes;
- tests pass;
- Docker images build;
- no breaking OpenAPI or event contract drift.

## Versioning, tags, releases, changelog

### Versioning policy
Use `Semantic Versioning`:
- `MAJOR` for breaking API changes;
- `MINOR` for backward-compatible features;
- `PATCH` for fixes.

### Tag format
- `v0.1.0`
- `v0.2.0`
- `v1.0.0`

### Release policy
- create a git tag only after CI is green;
- create GitHub Release from the tag;
- publish matching Docker image tags;
- update `CHANGELOG.md` on every meaningful change set.

### Changelog discipline
Follow `Keep a Changelog` sections:
- `Added`
- `Changed`
- `Fixed`
- `Removed`

## Recommended implementation order

### Phase 0. Repository bootstrap
- create monorepo skeleton;
- add shared config strategy;
- add code style and testing tooling;
- configure Docker base images;
- configure GitHub Actions skeleton;
- define versioning and changelog rules.

### Phase 1. Account service
- implement auth and role model;
- implement seeded users;
- implement JWT/refresh token flow;
- implement account CRUD;
- implement doctor listing;
- cover with tests.

### Phase 2. Hospital service
- implement hospital and room CRUD;
- add events and tests;
- verify authorization matrix.

### Phase 3. Timetable service
- implement schedule invariants;
- implement appointment booking with race protection;
- add HTTP validations to account/hospital services;
- add tests for edge cases and conflicts.

### Phase 4. Document service
- implement history CRUD;
- add role and ownership checks;
- add validation against account/hospital services;
- add outbox and indexing pipeline;
- add search endpoint and tests.

### Phase 5. ELK and observability
- add structured logs;
- configure Logstash pipelines;
- configure Kibana dashboards or saved searches.

### Phase 6. Full-stack hardening
- add docker-compose health checks;
- seed data and smoke tests;
- finalize README;
- prepare first tagged release.

## Definition of done
The project is done only when:
- all 4 services are isolated and runnable together;
- service interactions are implemented and tested;
- document search in Elasticsearch works with useful relevance and filters;
- `docker-compose up -d` launches the full platform;
- Swagger is reachable on all required ports;
- test suite is green in GitHub Actions;
- `CHANGELOG.md` is current;
- the repository has a release-ready semantic version tag strategy.

## Immediate next step after this plan
Start implementation with `Phase 0` and `Phase 1` together:
- bootstrap the monorepo and shared libraries;
- deliver the account service first because every other service depends on identity and roles.
