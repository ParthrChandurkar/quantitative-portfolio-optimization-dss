# Phase 9 Integration Notes

## Frontend contract audit

The Phase 3 React prototype is located at repository-root `src/`, not `frontend/src/`. It contains static fixture imports and timer-driven interactions; there was no mock API client and no frontend test script or test files to replace while keeping page components unchanged.

Phase 9 therefore added the real dependency-injectable client at `src/lib/api/client.ts`, matching every `/api/v1` route and the shared response envelope. Phase 9B subsequently closed this gap: `src/data.ts` was deleted and the application was split into live React Query pages. See [phase9b-frontend-integration.md](phase9b-frontend-integration.md).

## Backend behavior

- JSON endpoints return `{ "data": ..., "error": null }` or `{ "data": null, "error": { "code": "...", "message": "..." } }`.
- The PDF download endpoint returns `application/pdf` bytes because wrapping a downloadable binary in JSON would break browser download semantics.
- Optimization runs are persisted as `pending` before solving and then transition to `solved`, `infeasible`, or `failed`. Solving runs in a worker thread so the event loop remains available; the polling route exposes the persisted status.
- Phase 2 did not provide nullable cardinality/default-sector-cap fields on `optimization_runs`. Phase 9 stores the complete configuration inside the existing `sector_constraints` JSONB document while retaining compatibility with legacy direct cap dictionaries.
