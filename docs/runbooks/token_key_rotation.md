# Token And Key Rotation Runbook

## Purpose

This runbook describes how to rotate `JWT_SECRET_KEY` and `INTERNAL_API_KEY` safely in the current platform.

## Current model

- access tokens are signed with `HS256`;
- all services verify the same `JWT_SECRET_KEY`;
- internal HTTP contracts use a shared `INTERNAL_API_KEY`.

Because these are shared secrets, rotation must be coordinated carefully.

## When to rotate

- suspected secret exposure;
- scheduled credential hygiene;
- environment promotion with new secret material;
- transition toward asymmetric JWT signing.

## JWT secret rotation

Current limitation:
- services do not yet support dual-key validation;
- rotating the signing secret invalidates outstanding access tokens immediately.

Recommended procedure:
1. choose a maintenance window;
2. generate a new strong `JWT_SECRET_KEY`;
3. update all services to the new value at once;
4. restart or redeploy all four services;
5. require clients to sign in again if necessary.

## Internal API token rotation

Current limitation:
- internal HTTP validation uses one shared token;
- there is no dual-token overlap mode yet.

Recommended procedure:
1. generate a new strong `INTERNAL_API_KEY`;
2. update all services together;
3. restart or redeploy all four services;
4. verify internal endpoints continue to work through `timetable-service` and `document-service` flows.

## Verification checklist

- `account-service` can sign in and issue access tokens;
- `hospital-service`, `timetable-service`, and `document-service` accept those tokens;
- internal reference validation works;
- no `Invalid internal token` or JWT decode errors repeat in logs.

## Future improvement path

For safer rotation:
- move access tokens to asymmetric signing;
- add overlap support for current and next verification keys;
- replace the shared internal token with stronger service identity or per-service credentials.

Related design note:
- [jwt_strategy.md](D:/Study/codex/ai-test/docs/security/jwt_strategy.md)
