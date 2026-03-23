# Simbir.Health Backend: requirements analysis

## Source
- Source document: `C:/Users/redmi/Downloads/semifinal-task-backend.pdf`
- Analysis date: `2026-03-24`
- Extraction note: most API contracts and infrastructure requirements were extracted cleanly; a small part of the narrative text in the PDF was partially garbled during text extraction, so several role details below are marked as implementation assumptions.

## High-level goal
Build a backend platform for `Simbir.Health` as **4 independent microservices** on `Python + FastAPI`, with:
- `PostgreSQL` as the transactional data store.
- `Elasticsearch + Kibana` for document search and observability.
- `Dockerfile` + `docker-compose` for local deployment.
- `GitHub Actions` for CI/CD.
- mandatory automated tests.
- versioning, tags, releases, and changelog discipline.

## Mandatory architectural constraints
- All 4 applications must be implemented as **microservices**.
- Services must communicate with each other according to the business workflow.
- Preferred application layering for each service:
  - `router -> service -> repository -> model`
- No external identity provider:
  - solutions such as `Identity Server`, `Keycloak`, etc. are explicitly forbidden.
- API documentation must be available through Swagger and protected appropriately for JWT-based flows.
- System must be runnable via `docker-compose up -d`.

## Required services

### 1. Account microservice
Responsibility:
- registration and authentication;
- JWT issuing and validation;
- current user profile management;
- user administration;
- doctor directory.

Explicit API contract from the PDF:
- `POST /api/Authentication/SignUp`
- `POST /api/Authentication/SignIn`
- `PUT /api/Authentication/SignOut`
- `GET /api/Authentication/Validate`
- `POST /api/Authentication/Refresh`
- `GET /api/Accounts/Me`
- `PUT /api/Accounts/Update`
- `GET /api/Accounts`
- `POST /api/Accounts`
- `PUT /api/Accounts/{id}`
- `DELETE /api/Accounts/{id}`
- `GET /api/Doctors`
- `GET /api/Doctors/{id}`

Entities inferred from the contract:
- account/user;
- role;
- refresh token/session.

### 2. Hospital microservice
Responsibility:
- hospitals CRUD;
- room management per hospital.

Explicit API contract:
- `GET /api/Hospitals`
- `GET /api/Hospitals/{id}`
- `GET /api/Hospitals/{id}/Rooms`
- `POST /api/Hospitals`
- `PUT /api/Hospitals/{id}`
- `DELETE /api/Hospitals/{id}`

Entities:
- hospital;
- hospital room.

### 3. Timetable microservice
Responsibility:
- doctor schedules;
- hospital room schedules;
- appointment slot booking;
- deletion of schedules by doctor and hospital.

Explicit API contract:
- `POST /api/Timetable`
- `PUT /api/Timetable/{id}`
- `DELETE /api/Timetable/{id}`
- `DELETE /api/Timetable/Doctor/{id}`
- `DELETE /api/Timetable/Hospital/{id}`
- `GET /api/Timetable/Hospital/{id}`
- `GET /api/Timetable/Doctor/{id}`
- `GET /api/Timetable/Hospital/{id}/Room/{room}`
- `GET /api/Timetable/{id}/Appointments`
- `POST /api/Timetable/{id}/Appointments`
- `DELETE /api/Appointment/{id}`

Business rules explicitly visible in the PDF:
- schedule start and end must align to `30-minute` boundaries;
- example boundaries use minute `0` or `30`;
- `to > from`;
- one timetable interval cannot exceed `12 hours`;
- available appointment times are generated every `30 minutes` inside the timetable interval.

Entities:
- timetable slot/range;
- appointment.

### 4. Document microservice
Responsibility:
- medical history records;
- document storage and retrieval;
- searchable medical record content.

Explicit API contract:
- `GET /api/History/Account/{id}`
- `GET /api/History/{id}`
- `POST /api/History`
- `PUT /api/History/{id}`

Business rules visible in the PDF:
- `pacientId` in a medical history record must reference a user with role `User`;
- records contain:
  - `date`
  - `pacientId`
  - `hospitalId`
  - `doctorId`
  - `room`
  - `data`

Entities:
- medical history document.

## Data and infrastructure requirements from the PDF
- transactional database: `PostgreSQL`;
- authentication: `JWT`;
- search engine: `Elasticsearch`;
- visualization/observability: `Kibana`;
- containerized deployment: `Docker`;
- local startup command: `docker-compose up -d`;
- source control platform can be GitHub/GitLab/Bitbucket/GitVerse, but the user explicitly requires `GitHub Actions`.

## Integration requirements
The PDF states that service interaction is required and suggests protocols such as:
- `HTTP`
- `gRPC`
- `RabbitMQ`
- `Apache Kafka`

Conclusion for implementation planning:
- inter-service communication is mandatory;
- protocol choice is flexible, but it must be justified and aligned with the workflows.

## Search requirements
The PDF explicitly requires:
- document search through `Elasticsearch`;
- exposure of `Elasticsearch` and `Kibana` URLs in `README.md`.

From the user's additional constraint:
- search must be "gramotny", meaning not just a raw text dump but a usable full-text and filtered search over medical records.

## Deployment and documentation requirements
Expected exposed URLs in `README.md`:
- Account: `http://localhost:8081/ui-swagger`
- Hospital: `http://localhost:8082/ui-swagger`
- Timetable: `http://localhost:8083/ui-swagger`
- Document: `http://localhost:8084/ui-swagger`
- Elasticsearch: `http://elasticsearch-service/`
- Kibana: `http://kibana-service/`

Conclusion:
- each FastAPI app should expose Swagger on `/ui-swagger`;
- ports `8081-8084` are effectively part of the acceptance contract.

## Seed users visible in the PDF
The PDF contains a starter matrix with these credentials/roles:
- `admin / admin` -> `Admin`
- `manager / manager` -> `Manager`
- `doctor / doctor` -> `Doctor`
- `user / user` -> `User`

Implementation assumption:
- these users should be pre-seeded on first startup for local/demo acceptance.

## Role and access implications
The PDF text is partially degraded, but the role model is clearly present:
- `Admin`
- `Manager`
- `Doctor`
- `User`

Safe access assumptions for the plan:
- `Admin` manages accounts and platform-level actions.
- `Manager` manages hospitals, timetables, and operational records.
- `Doctor` works with schedules and medical histories.
- `User` can view own profile, available timetables, book appointments, and access own history only.

These assumptions must be formalized in an authorization matrix during implementation.

## Hidden but necessary requirements
Even though they are not written line by line in the PDF, the following are necessary to deliver a robust solution:
- service-specific database ownership;
- schema migrations;
- idempotent seed data;
- centralized configuration;
- structured logs;
- health checks;
- API contract consistency;
- reproducible local environment;
- automated tests across units, repositories, APIs, and cross-service flows.

## Risks and ambiguities captured early
- The PDF extraction degraded some Russian descriptive text; endpoint contracts are reliable, but some narrative access rules must be inferred.
- The PDF names `Document microservice`, but its API actually models `History` records, so the implementation should treat medical histories as searchable documents.
- The PDF allows several integration transports; choosing too many at once would create unnecessary complexity. A mixed strategy should be selected deliberately.
- Search relevance for Russian medical text requires explicit analyzer configuration in Elasticsearch; a naive default index will not be enough.

## Planning conclusion
The project should be treated as a **monorepo of 4 FastAPI microservices**, each with its own bounded context, its own repository/model layer, its own migrations, and explicit service communication. The hardest parts are:
- authorization and role separation;
- slot booking correctness in the timetable service;
- document indexing and search relevance in Elasticsearch;
- reproducible local deployment with ELK and CI pipelines.
