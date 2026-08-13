# Requirements Traceability Matrix

## Purpose

This matrix assigns every Phase 1 requirement to the phase and module responsible for its implementation and verification. Requirement identifiers are immutable. Later implementation comments and test names shall use the exact forms `FR-1` through `FR-9` and `NFR-1` through `NFR-8` so automated checks can locate them with a repository-wide search.

## Functional requirement traceability

| Requirement | Requirement title | Primary implementation phase | Primary module or artifact | Planned verification |
|---|---|---|---|---|
| FR-1 | User authentication and profile management | Phase 9 — Architecture and integration | FastAPI `auth`, `users`, JWT service, PostgreSQL user/session tables, React auth routes | API authentication, token rotation, ownership, and cross-user authorization integration tests |
| FR-2 | Market data and investment-universe management | Phase 2 — Database design and data ingestion | PostgreSQL market/universe schema, ETL mapping and validation service, data-readiness API | ETL unit tests, duplicate and invalid-row tests, as-of-date and look-ahead-bias integration tests |
| FR-3 | Portfolio problem configuration and validation | Phase 3 — UI/UX design and Phase 4 — Optimization engine | React model builder, FastAPI request schema, domain constraint validator | Frontend form tests, API schema tests, cross-constraint feasibility test suite |
| FR-4 | Constrained portfolio optimization | Phase 4 — Optimization engine | Model factory, SciPy adapter, PuLP adapter, OR-Tools adapter, solver-status mapper | Mathematical invariant, known-solution, infeasibility, timeout, and solver parity tests |
| FR-5 | Decision explanation and recommendation rationale | Phase 5 — Decision support | Explanation service, constraint diagnostics, contribution analysis, explanation UI | Explanation consistency, binding-tolerance, contribution reconciliation, and invalid-status tests |
| FR-6 | Scenario simulation and re-optimization | Phase 6 — Scenario simulator | Scenario definitions, shock transforms, linked re-optimization service, comparison UI | Scenario formula, baseline immutability, authorization, and delta-reconciliation tests |
| FR-7 | Portfolio analytics dashboard | Phase 7 — Analytics dashboard | Analytics service, metric library, allocation/performance/risk visualizations | Metric reference, date-alignment, unavailable-state, chart, and accessibility tests |
| FR-8 | Portfolio persistence, history, and comparison | Phase 2 — Database design and Phase 9 — Architecture and integration | Portfolio/run schema, repository services, history and comparison API/UI | Transaction, immutability, ownership, archive filtering, and comparison tests |
| FR-9 | Report generation and export | Phase 8 — Reports | Report composition service, PDF renderer, CSV exporter, report UI | Content contract, total reconciliation, scenario linkage, UTF-8 CSV, and authorization tests |

## Non-functional requirement traceability

| Requirement | Quality attribute | Primary implementation phase | Primary module or control | Planned verification |
|---|---|---|---|---|
| NFR-1 | Performance and response time | Phase 4 — Optimization engine and Phase 9 — Architecture and integration | Solver benchmarks, API query optimization, frontend performance budget | 100-run solver benchmark, API load test, and browser performance audit |
| NFR-2 | Capacity and scalability | Phase 2 — Database design and Phase 9 — Architecture and integration | Indexed time-series schema, pagination, worker/job concurrency controls | Dataset-volume test and 15-minute concurrent load test |
| NFR-3 | Security and privacy | Phase 9 — Architecture and integration | TLS configuration, Argon2id, JWT rotation/revocation, authorization policy, secret handling | Security unit/integration tests, dependency scan, static scan, and release checklist |
| NFR-4 | Reliability, integrity, and recoverability | Phase 2 — Database design and Phase 9 — Architecture and integration | Database transactions, health checks, backup/restore procedure, terminal-status state machine | Fault injection, forced solver failure, availability monitoring, and restore drill |
| NFR-5 | Usability and accessibility | Phase 3 — UI/UX design | Responsive React components, keyboard interaction, accessible charts and status messages | Axe scan, contrast check, keyboard script, viewport suite, and moderated usability test |
| NFR-6 | Maintainability and testability | Phase 9 — Architecture and integration and Phase 10 — Development roadmap | Layered architecture, linters, type checks, migrations, coverage and traceability CI gates | CI build/lint/type/coverage reports and clean-database migration test |
| NFR-7 | Data quality and freshness | Phase 2 — Database design and data ingestion | Canonical validation rules, batch manifest, checksums, derived-metric pipeline, freshness monitor | Invalid-row property tests, lineage assertions, reference-calculation tests, and stale-data test |
| NFR-8 | Auditability and reproducibility | Phase 5 — Decision support and Phase 9 — Architecture and integration | Immutable run provenance, replay service, append-only audit log, UTC timestamp policy | Continuous/integer replay tests, provenance completeness test, and audit-log mutation test |

## Phase coverage summary

| Phase | Requirements delivered or materially supported |
|---|---|
| Phase 1 — Requirement analysis | FR-1–FR-9 and NFR-1–NFR-8 definitions and traceability baseline |
| Phase 2 — Database design and data ingestion | FR-2, FR-8, NFR-2, NFR-4, NFR-7 |
| Phase 3 — UI/UX design | FR-3, NFR-5 |
| Phase 4 — Optimization engine | FR-3, FR-4, NFR-1 |
| Phase 5 — Decision support | FR-5, NFR-8 |
| Phase 6 — Scenario simulator | FR-6 |
| Phase 7 — Analytics dashboard | FR-7 |
| Phase 8 — Reports | FR-9 |
| Phase 9 — Architecture and integration | FR-1, FR-8, NFR-1, NFR-2, NFR-3, NFR-4, NFR-6, NFR-8 |
| Phase 10 — Development roadmap | NFR-6 delivery gates and sequencing |

## CI traceability convention

Later phases shall add the relevant identifier to both implementation and test artifacts. Examples:

```python
 # implements FR-4
def solve_portfolio(...):
    ...
```

```typescript
// implements FR-7
export function PortfolioAnalytics() {
  // ...
}
```

```python
def test_fr_6_scenario_preserves_baseline():
    """Verifies FR-6 and contributes to NFR-8."""
```

During staged development, CI shall evaluate only requirements assigned to completed phases. At final integration, the expected identifier set is exactly FR-1 through FR-9 and NFR-1 through NFR-8, and every identifier shall occur in this matrix, at least one implementation artifact, and at least one automated test artifact.
