# Non-Functional Requirements

## NFR-1 — Performance and response time

**Measurable targets:**

- A continuous LP over 50 assets shall reach and serialize a terminal solver result in less than 2.0 seconds at the 95th percentile across 100 benchmark runs on the reference deployment: 4 vCPU, 8 GB RAM, warm application process, and locally hosted PostgreSQL.
- A MILP over 50 assets with sector and cardinality constraints shall return an optimal solution or a feasible incumbent with explicit `TIME_LIMIT` status within 10.0 seconds at the 95th percentile under the same reference deployment.
- Read-only API requests excluding report generation shall respond in less than 500 ms at the 95th percentile under 50 concurrent authenticated users and a sustained load of 25 requests per second for 10 minutes.
- The largest analytics route shall reach Largest Contentful Paint within 2.5 seconds at the 75th percentile on a 10 Mbps connection and a mid-tier device profile.

## NFR-2 — Capacity and scalability

**Measurable targets:**

- The system shall store and query at least 30 years of daily observations for 100 securities, equal to at least 750,000 market-data rows, without changing the canonical schema.
- The API shall support 100 concurrent authenticated sessions and 20 concurrent optimization jobs while keeping error rate below 1.0% in a 15-minute load test; intentionally returned 4xx validation responses are excluded from the error rate.
- Market-data list endpoints shall paginate responses to no more than 500 records per page, and portfolio-history endpoints to no more than 100 records per page.

## NFR-3 — Security and privacy

**Measurable targets:**

- All non-localhost network traffic shall use TLS 1.2 or later; HTTP requests shall be redirected to HTTPS.
- Passwords shall be hashed with Argon2id using at least 19 MiB memory, 2 iterations, and parallelism 1, or a stronger OWASP-recommended setting available at deployment time; plaintext passwords shall never be logged or persisted.
- JWT access tokens shall expire within 15 minutes and refresh tokens within 7 days. Refresh tokens shall be revocable and rotated on every successful refresh; reuse of a rotated token shall revoke its token family.
- Every protected object-level request shall be covered by an automated authorization test, with 100% of cross-user read, update, archive, report, and scenario attempts returning HTTP 403 or 404.
- Automated dependency and static security scans on the default branch shall report zero unresolved critical or high-severity vulnerabilities before a release build is approved.

## NFR-4 — Reliability, integrity, and recoverability

**Measurable targets:**

- Excluding planned maintenance, the API shall achieve at least 99.5% monthly availability in the deployed evaluation environment.
- Optimization-run creation, allocation persistence, and portfolio saving shall be transactional: fault-injection tests at each database write boundary shall produce either a complete valid record or no visible record in 100% of cases.
- PostgreSQL shall be backed up at least once every 24 hours with a recovery point objective of 24 hours and a recovery time objective of 4 hours; a restore drill shall be completed at least once per release cycle.
- An interrupted or timed-out optimization shall never be labeled `OPTIMAL`; 100% of forced timeout and solver-failure tests shall retain the correct terminal status and diagnostic message.

## NFR-5 — Usability and accessibility

**Measurable targets:**

- The primary workflows for configuring, solving, explaining, simulating, saving, and exporting a portfolio shall conform to WCAG 2.2 Level AA with zero critical or serious automated accessibility violations in Axe scans.
- Text and essential icon contrast shall be at least 4.5:1, and large text at least 3:1; focus indicators shall have at least 3:1 contrast against adjacent colors.
- All interactive controls in the primary workflows shall be operable by keyboard alone, with zero keyboard traps across a complete scripted workflow.
- Layouts shall have no horizontal page overflow at viewport widths of 360, 768, 1024, and 1440 CSS pixels at 100% zoom, excluding intentionally scrollable data tables that include an accessible label.
- In a moderated test of at least five representative users, at least 80% shall complete a baseline optimization and locate its binding constraints within 5 minutes without facilitator intervention.

## NFR-6 — Maintainability and testability

**Measurable targets:**

- The frontend TypeScript compiler, frontend linter, Python formatter/linter, and type checker shall complete with zero errors in continuous integration for every merge to the default branch.
- Automated tests shall maintain at least 80% statement coverage for backend domain and service modules, 90% branch coverage for constraint validation and optimization-status mapping, and 70% statement coverage for frontend application code.
- Every implemented FR-1 through FR-9 and NFR-1 through NFR-8 shall appear verbatim in at least one implementation comment or test name, and CI traceability checks shall fail if any identifier has no implementation and no automated test reference after its scheduled phase is complete.
- Database schema changes shall use versioned migrations; a clean database shall migrate from version zero to the current version in less than 60 seconds on the reference deployment.

## NFR-7 — Data quality and freshness

**Measurable targets:**

- Ingestion shall enforce uniqueness of `(symbol, trading_date)` and reject 100% of rows with invalid dates, non-positive adjusted close values, negative volume, or symbols absent from the referenced universe snapshot.
- For any completed ingestion batch, accepted-row counts, rejected-row counts, source checksum, ingestion timestamp, date range, and per-column null counts shall be retained for 100% of batches.
- Derived return, annualized-volatility, and covariance calculations shall match an independent reference implementation within absolute tolerance `1e-10` on a fixed validation dataset.
- During normal provider availability, daily market data shall be refreshed by 08:00 Asia/Kolkata on the next calendar day; the UI shall display the latest trading date and mark data stale when the latest expected trading observation is more than one trading day overdue.

## NFR-8 — Auditability and reproducibility

**Measurable targets:**

- For 100% of persisted optimization and scenario runs, the system shall retain user identifier, UTC timestamps, data snapshot checksum, as-of date, estimation window and method, objective, normalized constraints, solver name and version, solver parameters, random seed where applicable, terminal status, objective value, allocations, and computed metrics.
- Replaying a deterministic continuous run from its stored provenance shall reproduce each allocation weight and objective value within absolute tolerance `1e-8`; replaying a deterministic integer run with the same solver version shall reproduce selected assets and integer quantities exactly.
- Audit events for authentication, data ingestion, run creation, portfolio save/archive, scenario execution, and report generation shall be retained for at least 365 days and shall be append-only to application roles.
- Application logs and reports shall use UTC timestamps in ISO 8601 format; user-facing screens may additionally show the configured local timezone.

