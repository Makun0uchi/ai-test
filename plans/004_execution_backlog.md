# Simbir.Health Backend: execution backlog

## Current milestone baseline
- Baseline version: `v0.16.0`
- Scope already done:
  - microservice CRUD and auth flows;
  - migrations;
  - internal HTTP validation;
  - outbox publication in all services;
  - shared event contracts;
  - contract tests;
  - async search indexing in `document-service`;
  - shared consumer infrastructure;
  - first real cross-service consumer flow: `hospital.deleted.v1 -> timetable-service` cleanup;
  - full end-to-end patient visit workflow test across all four services;
  - correlation IDs and structured event/request logging across HTTP, outbox, and RabbitMQ flows.

## Backlog structure
- `P0`: required before calling the project production-ready.
- `P1`: strongly recommended before first serious deployment.
- `P2`: useful hardening after the first production-grade release candidate.

## P0 backlog

### P0.1 Event catalog and routing matrix
Deliverables:
- document every event type, producer, consumer, aggregate, and expected side effect;
- identify which events are currently published but not consumed;
- define versioning rules for event evolution.

Outputs:
- `plans/005_event_catalog.md`
- `docs/events/` if a docs folder is introduced later.

### P0.2 Shared consumer infrastructure
Status:
- completed in `v0.14.0`

Deliverables:
- generic consumer bootstrap helper;
- typed parsing helper for RabbitMQ payloads;
- standard logging and failure handling for consumers;
- idempotency strategy guidelines.

Outputs:
- reusable code in `libs/service_common` or `libs/contracts`;
- tests for parsing and failure behavior.

### P0.3 Second real consumer flow
Status:
- completed in `v0.14.0`

Deliverables:
- implement at least one consumer-driven integration besides history indexing;
- keep the flow bounded and testable.

Recommended candidate:
- consume `hospital.deleted.v1` or `account.deleted.v1` into a denormalized projection or operational cleanup flow.

Implemented flow:
- `hospital.deleted.v1 -> timetable-service` cleanup with `timetable.deleted.v1` follow-up publication.

Acceptance:
- producer and consumer both use shared contracts;
- replaying the same event does not corrupt state;
- integration test covers the side effect.

### P0.4 Full end-to-end flow tests
Status:
- completed in `v0.15.0`

Deliverables:
- automated system scenario:
  - create hospital;
  - create timetable;
  - book appointment;
  - write history;
  - observe searchable result.

Acceptance:
- executable in CI;
- stable under clean environment bootstrap.

### P0.5 Correlation IDs and structured event logging
Status:
- completed in `v0.16.0`

Deliverables:
- request correlation ID middleware;
- event publication and consumption logs with correlation and aggregate metadata;
- documented log field set.

Acceptance:
- logs can be correlated across services;
- event failures are discoverable in Kibana.

### P0.6 Release automation
Deliverables:
- release workflow that builds images on `v*` tags;
- GitHub Release creation from changelog;
- image tagging convention.

Acceptance:
- tag push creates release artifacts automatically.

## P1 backlog

### P1.1 RabbitMQ reliability policy
Tasks:
- define retry policy;
- define dead-letter exchange/queue strategy;
- define message TTL and requeue stance if needed;
- document operational recovery steps.

### P1.2 Search reindex and maintenance tooling
Tasks:
- explicit reindex command or admin workflow;
- alias management;
- rebuild docs.

### P1.3 Security posture uplift
Tasks:
- remove production reliance on default JWT secrets;
- document env requirements;
- evaluate asymmetric JWT signing;
- review internal token handling.

### P1.4 Environment profiles
Tasks:
- standardize `local`, `ci`, `staging`, `production`;
- document required variables, ports, storage, and dependencies;
- define compose override or deployment manifests strategy.

### P1.5 Operational runbooks
Tasks:
- service startup failure;
- migration rollback;
- outbox lag;
- RabbitMQ failure;
- Elasticsearch reindex;
- token/key rotation.

## P2 backlog

### P2.1 Performance and capacity review
Tasks:
- basic load checks on auth, timetable booking, and history search;
- identify obvious bottlenecks;
- document capacity assumptions.

### P2.2 Deployment ergonomics
Tasks:
- production ingress/gateway decision;
- optional reverse proxy;
- resource tuning for Elasticsearch and RabbitMQ.

### P2.3 Advanced data lifecycle
Tasks:
- retention policy for refresh tokens and logs;
- backup/restore documentation for PostgreSQL;
- index lifecycle for Elasticsearch.

## Suggested task order for the next 8 engineering steps
1. Create event catalog and routing matrix.
2. Introduce shared consumer utility layer.
3. Implement one additional real cross-service consumer flow.
4. Add end-to-end workflow tests.
5. Add correlation IDs and structured event logs.
6. Harden RabbitMQ failure handling and document replay strategy.
7. Add release automation for image publishing and GitHub Releases.
8. Finalize production deployment and runbooks.

## Release target ladder

### Release candidate target
- all P0 items complete;
- CI green including end-to-end tests;
- release workflow proven on tag;
- docs sufficient for another engineer to run and diagnose the system.

### First production-grade target
- all P0 complete;
- most P1 complete;
- known risks documented;
- rollback and recovery procedures written and reviewed.

## Notes for future execution
- Do not introduce new event types casually; prefer versioning existing contracts.
- Keep consumer logic idempotent before increasing the number of consumers.
- Preserve the current rule: every completed task updates changelog, version, tag, and remote repository state.
