# JWT And Internal Token Strategy

## Current runtime policy

- All services currently validate access tokens with `HS256`.
- `account-service` signs access tokens.
- `hospital-service`, `timetable-service`, and `document-service` verify the same token.
- Internal service-to-service HTTP calls use `X-Internal-Token`.

## Security rules now enforced in code

- `staging` and `production` must not use the local default `JWT_SECRET_KEY`.
- `staging` and `production` must not use the local default `INTERNAL_API_KEY`.
- `staging` and `production` require both secrets to be at least `32` characters.
- Runtime code currently supports `HS256` only. Any asymmetric rollout must be implemented deliberately.

## Environment expectations

- `local` and local `docker` flows may use explicit development secrets.
- `staging` and `production` must provide:
  - `JWT_SECRET_KEY`
  - `JWT_ALGORITHM=HS256`
  - `INTERNAL_API_KEY`

## Internal token handling review

Current state:
- one shared internal token protects internal HTTP reference endpoints;
- the token is propagated only inside trusted service-to-service calls;
- the token is not intended for browser or public API use.

Current limitation:
- this is a shared secret, not per-service identity;
- rotation is manual;
- compromise of the token affects all internal HTTP contracts.

## Asymmetric JWT evaluation

Recommended next production step:
- `account-service` signs tokens with a private key;
- other services verify tokens with the public key;
- algorithm moves from `HS256` to `RS256`;
- key rotation is handled independently from application deploys.

Why this is better:
- verification keys can be distributed without sharing signing capability;
- compromise of a verifier does not allow token minting;
- rotation and trust boundaries become cleaner.

## Migration outline

1. Introduce `JWT_PRIVATE_KEY` in `account-service`.
2. Introduce `JWT_PUBLIC_KEY` in all verifying services.
3. Add runtime support for `RS256`.
4. Roll out dual-environment validation in staging.
5. Switch production traffic to asymmetric verification.
