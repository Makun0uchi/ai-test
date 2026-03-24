# Simbir.Health Backend: production readiness plan

## Planning context
- Planning date: `2026-03-24`
- Current repository version baseline: `v0.13.0`
- Current project state:
  - all `4` FastAPI microservices are implemented;
  - each service has PostgreSQL schema migrations via `Alembic`;
  - synchronous reference validation over internal HTTP is implemented;
  - all services publish domain events through `Transactional Outbox + RabbitMQ`;
  - shared RabbitMQ payload contracts live in `libs/contracts`;
  - `document-service` consumes history events and updates Elasticsearch asynchronously;
  - CI quality gates already run `ruff`, `black`, `mypy`, `pytest`, and Docker config validation.

## Main objective
Bring the repository from a working demo-quality microservice platform to a production-ready backend that is:
- observable;
- operable;
- resilient to partial failures;
- contract-stable;
- testable end-to-end;
- releasable through deterministic CI/CD.

## What is already done

### Functional scope already covered
- `account-service`: auth, JWT, seeded users, account CRUD, doctor directory.
- `hospital-service`: hospital CRUD and room management.
- `timetable-service`: schedule CRUD, appointments, interval validation, overlap protection.
- `document-service`: history CRUD, access control, Elasticsearch search, async indexing.

### Architectural scope already covered
- layer structure `router -> service -> repository -> model`;
- service-local database ownership;
- `Alembic` migrations per service;
- outbox + RabbitMQ publication for all services;
- shared event schemas;
- contract tests for published events;
- Docker-based local stack.

## Remaining production gaps

### Inter-service consumers and read models
Events are published, but only `document-service` currently consumes domain events in a meaningful flow.

Still missing:
- reusable inter-service consumers beyond document indexing;
- denormalized read models fed by events;
- replay-safe/idempotent consumer behavior across more than one service;
- clear event ownership and routing matrix.

### Reliability and failure handling
The current outbox dispatcher pattern is solid, but operational protections are still thin.

Still missing:
- retry/backoff policy for consumer-side failures;
- dead-letter strategy for poison messages;
- explicit idempotency rules for consumers;
- recovery procedures for stuck outbox rows or replay operations.

### Observability
ELK infrastructure exists, but production-grade observability is not complete.

Still missing:
- structured request logs with correlation IDs;
- event publication and consumption logs with aggregate identifiers;
- health/readiness details for dependencies;
- Kibana dashboards and saved searches;
- operational alerts or at least actionable log queries.

### Security hardening
Authentication works, but production hardening is incomplete.

Still missing:
- move from local shared-secret JWT verification toward asymmetric signing or externalized keys;
- secrets handling through environment or secret store conventions;
- stricter token lifecycle controls and documented rotation policy;
- security headers and deployment posture review.

### CI/CD and release discipline
CI exists, but release automation is not yet fully production-oriented.

Still missing:
- image publishing to registry on release tags;
- GitHub Release automation tied to changelog sections;
- deployment smoke verification for tagged builds;
- branch protection and release checklist formalization.

### Documentation and operations
The repository is understandable, but not yet production-operable by a third-party engineer.

Still missing:
- runbooks;
- failure recovery instructions;
- event catalog;
- deployment/environment matrix;
- SLO/SLI expectations;
- data retention and backup policy.

## Target production architecture state

### Runtime shape
- each microservice remains independently deployable;
- RabbitMQ topic exchange is the main async backbone;
- Elasticsearch is updated only through validated event consumers;
- internal HTTP remains for request-time reference checks where immediate consistency is required;
- all event payloads remain versioned and shared through `libs/contracts`.

### Operational shape
- every request and event has a correlation ID;
- every service emits structured JSON logs;
- every service exposes health and readiness signals;
- every deployment runs migrations deterministically;
- every release produces a versioned image, a git tag, and a changelog-backed release note.

## Detailed roadmap

### Phase A. Event-driven completion
Goal:
- turn event publication into full event-driven integration, not just producer completeness.

Tasks:
- add consumer-side infrastructure helpers shared across services;
- implement consumer idempotency guidelines and storage strategy where needed;
- define which services must react to which events;
- add at least one new cross-service consumer-driven flow beyond document indexing;
- document the event catalog and ownership rules.

Definition of done:
- event routing matrix exists in docs;
- at least two independent consumer flows are covered by tests;
- consumer handlers validate payloads through `libs/contracts`;
- replaying the same event does not corrupt state.

### Phase B. Search and read-model hardening
Goal:
- make document search production-usable and operationally resilient.

Tasks:
- add explicit Elasticsearch index alias strategy and rollover naming;
- separate write and read aliases;
- define reindex procedure from PostgreSQL + event replay;
- add search relevance tests for Russian text and filters;
- enrich search projection with optional denormalized labels if needed.

Definition of done:
- search remains correct after service restart and reindex;
- search contract is documented;
- Elasticsearch projection rebuild procedure is documented and tested.

### Phase C. Messaging reliability
Goal:
- make RabbitMQ flows safe under retries and partial outages.

Tasks:
- define message acknowledgment policy;
- add consumer error logging with aggregate and event metadata;
- introduce dead-letter queue strategy in compose/deployment docs;
- define retry and poison-message handling;
- add operational visibility into outbox lag and unprocessed messages.

Definition of done:
- failure modes are documented;
- replay/runbook exists for event processing issues;
- there is at least one automated test for retry-safe or idempotent behavior.

### Phase D. Observability and diagnostics
Goal:
- make runtime behavior diagnosable without code inspection.

Tasks:
- add request correlation IDs in all services;
- emit event publication/consumption logs with event type and aggregate ID;
- standardize log fields across services;
- wire Logstash parsing if needed;
- prepare Kibana views for:
  - request failures;
  - event publication;
  - event consumer failures;
  - search indexing activity.

Definition of done:
- logs are consistently structured;
- a request can be traced across services via correlation ID;
- Kibana contains at least baseline saved searches or dashboards.

### Phase E. Security hardening
Goal:
- remove demo assumptions that would block production.

Tasks:
- externalize JWT signing material from code defaults;
- plan migration to asymmetric token signing;
- document required env vars for each environment;
- review internal service authentication approach;
- document least-privilege role matrix and service trust model.

Definition of done:
- secrets are not dependent on local defaults in production profile;
- token verification strategy is documented;
- security-sensitive configuration has explicit environment requirements.

### Phase F. End-to-end and integration testing
Goal:
- verify the platform as a system, not only as isolated services.

Tasks:
- add full-stack tests using docker-compose or testcontainers;
- test the full business chain:
  - sign up/sign in;
  - hospital creation;
  - timetable creation;
  - appointment booking;
  - history creation;
  - search indexing and search retrieval;
- add event-contract regression checks into CI;
- add migration boot tests for the full stack.

Definition of done:
- one command can run high-value integration checks;
- at least one end-to-end scenario covers the main product workflow;
- CI fails on event contract drift.

### Phase G. CI/CD release pipeline hardening
Goal:
- make releases deterministic and traceable.

Tasks:
- build and publish Docker images on release tags;
- create GitHub Releases automatically;
- attach changelog section to release notes;
- optionally tag images by version and `latest` only on stable policy;
- document rollback procedure.

Definition of done:
- tag push produces release artifacts automatically;
- repository has a documented release workflow;
- rollback path is documented.

### Phase H. Production deployment posture
Goal:
- ensure the stack can be promoted from local to production-like environments.

Tasks:
- define environment profiles: `local`, `ci`, `staging`, `production`;
- document required env vars and service URLs;
- review Dockerfiles for size, startup, and health behavior;
- define persistent volume, backup, and retention assumptions;
- decide ingress/gateway approach if external exposure is needed.

Definition of done:
- deployment assumptions are explicit;
- environment-specific configuration is documented;
- production checklist exists.

## Production checklists

### Engineering readiness checklist
- all published events use shared contracts;
- consumers are typed and idempotent;
- no schema creation via ORM auto-bootstrap;
- release tags correspond to tested code;
- changelog is current.

### Operational readiness checklist
- services expose health endpoints;
- logs are structured and searchable;
- outbox processing can be diagnosed;
- replay/recovery procedure exists;
- dependencies and required env vars are documented.

### Release readiness checklist
- CI green on `ruff`, `black`, `mypy`, `pytest`;
- integration tests green;
- Docker images build successfully;
- changelog section prepared;
- tag and release notes ready.

## Risks to manage during the remaining work
- consumer logic can silently duplicate side effects without idempotency rules;
- event contract changes can break downstream consumers if not versioned carefully;
- Elasticsearch can drift from PostgreSQL if replay procedures are not explicit;
- demo security defaults can accidentally leak into production if environment rules stay implicit;
- operational complexity can grow faster than documentation if runbooks are postponed.

## Recommended immediate execution order
1. Finish inter-service consumer design and at least one additional real consumer flow.
2. Add shared consumer utilities, failure logging, and idempotency rules.
3. Add end-to-end integration tests for the core product workflow.
4. Harden observability with correlation IDs and event logs.
5. Complete release automation and deployment documentation.

## Final production target
The project should be considered production-ready only when:
- all core business flows are covered by end-to-end tests;
- event contracts are versioned, shared, and regression-tested;
- asynchronous processing has operational runbooks;
- search can be rebuilt deterministically;
- release automation produces traceable artifacts;
- deployment and rollback procedures are documented clearly enough for another engineer to operate the system safely.
