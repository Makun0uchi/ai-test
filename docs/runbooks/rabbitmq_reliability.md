# RabbitMQ Reliability Runbook

## Purpose

This runbook defines how consumer failures are handled in the Simbir.Health platform and how operators should recover from them.

## Current policy

- Producers publish persistent messages through the transactional outbox pattern.
- Consumers do not use automatic hot requeue on handler failure.
- Failed messages are routed to a dedicated dead-letter queue (DLQ) per consumer.
- DLQ messages do not expire automatically.
- Retry is a controlled operational action after the root cause is fixed.

## Why this policy exists

Automatic `requeue=true` can create a hot loop:
- one bad message is consumed over and over;
- logs flood quickly;
- CPU usage rises while useful work stalls;
- the queue appears alive but no recovery happens.

Routing failed messages to DLQ makes the failure visible and preserves the payload for later replay.

## Consumer queues with DLQ

- `document-service.history-indexer.v1`
  - DLQ: `document-service.history-indexer.dlq.v1`
- `timetable-service.hospital-cleanup.v1`
  - DLQ: `timetable-service.hospital-cleanup.dlq.v1`

Shared dead-letter exchange:
- `simbir.health.events.dlx`

## Failure signals to watch

- structured logs with `message="event handler failed"`
- log fields:
  - `service`
  - `correlation_id`
  - `event_type`
  - `routing_key`
  - `aggregate_type`
  - `aggregate_id`
  - `queue_name`
  - `dead_letter_queue_name`
- RabbitMQ queue depth growth in a DLQ

## Recovery workflow

1. Identify the failing consumer and the affected DLQ.
2. Inspect the structured logs by `correlation_id` and `event_type`.
3. Fix the application or infrastructure cause.
4. Pause or scale down the affected consumer if needed.
5. Replay messages from the DLQ back into the primary exchange or republish them manually.
6. Confirm that the primary queue drains and the DLQ stops growing.

## Replay guidance

- Prefer replaying only after a known fix is deployed.
- Replay in small batches first.
- Preserve the original payload and correlation metadata when possible.
- If replay tools are not available, use the RabbitMQ management UI or CLI-based republish scripts.

## TTL and retry stance

- Main consumer queues: no retry TTL queue is configured yet.
- Dead-letter queues: no TTL is configured intentionally.

Rationale:
- operational safety is better than hidden automatic retries at the current project stage;
- messages stay available for investigation and controlled replay;
- delayed retry queues can be added later when idempotency and replay tooling are expanded.
