# Conclusion and Future Work

## What was built

OptiVest now spans the full research-to-product path: formal requirements; a UUID/Numeric PostgreSQL schema; profiled, idempotently loaded real Nifty data; three solver families; independent feasibility checks; deterministic explanations; seven re-solved scenario types; real-price analytics; PDF generation; JWT/ownership-aware APIs; a fully connected React UI; and explicit temporal methodology validation.

The live system optimizes the 49-stock universe, persists holdings and “Why?” narratives, re-solves a 20% crash, displays a 30-point frontier and a zero-overlap OOS audit, and downloads a real two-page PDF. The corrected OOS result—₹10,00,000 to ₹11,01,423.96 with 0.6777 Sharpe—is less visually impressive than the biased replay and scientifically more useful.

## Honest simplifications and fallbacks

- Expected returns are annualized arithmetic historical means; no shrinkage, factor or Bayesian estimator is fitted.
- PuLP uses mean absolute deviation for a linear cardinality model; its relaxation shadow prices are not integer-program dual prices.
- OR-Tools selects support and delegates continuous weights to SciPy; it is a hybrid heuristic.
- Rate and inflation sensitivity tables are transparent estimated calibration assumptions, not coefficients fitted to this dataset.
- Share quantities are computed as decimal shares; whole-share transaction execution is not implemented.
- Backtests omit fees, bid–ask spread, slippage, taxes and market impact.
- The current out-of-sample methodology is a single fixed split rather than rolling walk-forward estimation.
- PDF generation is synchronous service work moved to a thread, not a distributed job queue.
- Backend achieved coverage is 88.56%, below its configured 90% global gate; service orchestration/error branches need additional tests.
- The Kaggle snapshot contains 49 symbols and does not reconstruct historical Nifty membership, so survivorship effects remain possible.

## Future work

### Methodology

1. Add walk-forward re-estimation with rolling 252-day fits and monthly/quarterly refits.
2. Evaluate several disjoint bull, bear and sideways periods; publish fold distributions rather than one Sharpe.
3. Add covariance shrinkage, robust mean estimation, Black–Litterman/factor alternatives and estimator comparison.
4. Model transaction costs, taxes, liquidity, turnover and whole-share lot constraints.
5. Reconstruct point-in-time index membership and corporate-action validation to reduce survivorship/data artifacts.

### Scenario calibration

Fit rate/inflation sector sensitivities from external macro series with uncertainty intervals, version each calibration, and test scenario stability. Add historical crisis replay while preserving the current transparent deterministic transforms.

### Scale and operations

Move optimization, walk-forward analytics and PDF jobs to Celery/Redis (or an equivalent durable queue), expose progress/cancellation, cache frontiers by problem hash, add structured logs/metrics, and deploy PostgreSQL backups and secret management.

### Product and validation

Add accessible responsive chart interactions, snapshot comparison/history selection, downloadable methodology manifests, stronger frontend branch coverage, and independent benchmark comparisons. A regulated deployment would also require suitability, disclosures, governance, data licensing and security review beyond this academic system.

## Final assessment

The project does not claim to predict markets or invent portfolio theory. Its value is a traceable, testable and self-correcting decision-support implementation. The Phase 9C correction demonstrates the central lesson: a mathematically feasible portfolio and polished dashboard are insufficient unless the temporal methodology behind the evidence is also valid.
