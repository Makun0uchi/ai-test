# Outbox Lag Runbook

## Purpose

This runbook describes how to diagnose and recover from outbox backlog when database writes are succeeding but events are not being published fast enough.

## Relevant services

All four services publish domain events through transactional outbox tables:
- `account-service`
- `hospital-service`
- `timetable-service`
- `document-service`

## Typical symptoms

- business writes succeed but downstream effects appear late;
- RabbitMQ queues stay quiet while source tables continue changing;
- search indexing lags after history writes;
- logs show repeated dispatcher exceptions.

## What outbox lag means

The application transaction committed successfully, but the background dispatcher has not yet published one or more outbox rows.

## Initial checks

1. Identify the affected service.
2. Inspect the service logs for dispatcher failures.
3. Confirm RabbitMQ is healthy and reachable.
4. Check whether the service process is actually running its background dispatcher.

## Likely causes

- RabbitMQ outage or network failure;
- authentication or connection issue for the broker;
- dispatcher crash loop;
- DB contention or unexpectedly large backlog;
- consumer-side issues causing confusion with publication lag.

## Recovery workflow

1. Restore RabbitMQ availability if it is unhealthy.
2. Restart the affected application service if the dispatcher is stuck.
3. Confirm outbox rows begin draining.
4. Confirm the expected downstream side effect appears:
   - message in RabbitMQ;
   - search index update;
   - follow-up consumer activity.

## What to inspect

- service logs for outbox dispatcher failures;
- structured logs around event publication;
- RabbitMQ management UI for exchange and queue activity;
- service-specific outbox rows in the database.

## Escalation guidance

Escalate to code or schema investigation when:
- RabbitMQ is healthy but publication still does not resume;
- the same outbox rows remain stuck after restart;
- publication fails only for one event type or one service.

## Exit criteria

The incident is resolved when:
- backlog stops growing;
- dispatcher logs show normal publication again;
- downstream effects resume within expected delay.
