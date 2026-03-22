# Target Structure (DDD)

## Goals

- Separate protocol, use-case orchestration, domain rules, and infrastructure details.
- Keep business code testable and independent from Flask/ORM/file-system details.
- Converge legacy scripts and mixed logic into stable module boundaries.

## Directory Responsibilities

- `app/routes/`
  - HTTP layer only (request parsing, response mapping, status codes).
  - No direct DB access and no heavy business rules.
  - Depend on `app/application/*`.

- `app/application/`
  - Use-case orchestration (Application Services).
  - Transaction/use-case flow coordination.
  - Depend on `app/domain/*` + `app/application/ports/*`.

- `app/application/ports/`
  - Repository and gateway contracts.
  - No implementation details.

- `app/domain/`
  - Core business model: entities, aggregates, value objects, domain invariants.
  - Must not depend on Flask/SQLAlchemy/OpenPyXL.

- `app/infrastructure/`
  - Adapters and implementations for ports.
  - DB repositories, file/template/document generators, third-party clients.
  - Depend on framework and external libraries.

- `tools/`
  - Operational scripts, migrations, one-off maintenance tasks.
  - Must be explicit CLI style (arguments, dry-run support when possible).

- `archive/`
  - Historical scripts and snapshots kept for traceability, not for normal runtime.

- `tests/`
  - Layered tests:
    - domain unit tests
    - application use-case tests
    - route/API integration tests

## Dependency Direction

Allowed dependency flow:

`routes -> application -> domain`

`application -> ports`

`infrastructure -> ports + domain`

Composition root (`app/bootstrap.py`) wires `application` with `infrastructure` implementations.

## Forbidden Dependencies

- `domain` importing from `routes`, `infrastructure`, Flask, SQLAlchemy, or file IO SDKs.
- `routes` calling ORM/repository directly.
- `routes` importing `infrastructure/*` directly.
- Business rules implemented in `routes` or ad-hoc scripts.

## Migration Plan (Incremental)

1. New features follow target structure strictly.
2. Existing route handlers move use-case logic into `app/application/*`.
3. Legacy `app/services/*` logic is either:
   - migrated to application/domain, or
   - converted into infrastructure adapter/helper.
4. One-off scripts move to `tools/`; stale scripts move to `archive/`.
