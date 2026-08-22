# Personalized Risk and Anomaly Alert Methodology

## Scope

OptiVest generates two evidence-based alert families after successful optimization or scenario re-solves and through an authenticated on-demand endpoint. Portfolio drift is deterministic and personalized from the latest stored AI Phase 2 risk profile. Held-stock anomaly detection is unsupervised and uses the existing AI Phase 1 feature pipeline. Alerts support review; they are not trade instructions.

No alert is generated while a portfolio has only its first snapshot. That snapshot establishes the baseline, so warning immediately would misrepresent initial configuration as drift.

## Risk-drift policy

A `RISK_DRIFT` alert is generated only when snapshot expected volatility is more than `0.03` above the profile's stored recommended risk tolerance. An excess of at least `0.10` is critical; a smaller qualifying excess is a warning. The three-percentage-point buffer prevents warnings for numerical jitter or ordinary movement around the target.

Diversification reference minimums are `75.0` for conservative, `65.0` for moderate, and `55.0` for aggressive profiles. A lower score produces `DIVERSIFICATION_DRIFT`; a deficit of at least `20.0` is critical. These are explicit product-policy references, not fitted market parameters, and can be recalibrated as user-outcome evidence becomes available.

## Isolation Forest stock anomalies

The detector imports `build_training_features` and `build_inference_features` from `app.ml.features`; it does not reproduce feature construction. Each held stock is modeled separately with the same 12 return, moving-average, RSI, MACD, realized-volatility, valuation, yield, and beta features used by AI Phase 1.

Historical vectors end strictly before the latest scored feature date and are sampled every five trading observations to reduce redundant adjacent-day fitting latency. Missing values are median-imputed from that stock's historical matrix. An Isolation Forest with 200 trees, random seed 42, and contamination `0.02` is fitted when at least 50 historical rows are available. OptiVest defines anomaly score as the negative scikit-learn decision function, so a score above `0.0` is flagged. Insufficient-history stocks are skipped rather than assigned fabricated values.

## Grounding and deduplication

Every alert stores the exact snapshot/profile values or anomaly score used by its pure message template. A structural test extracts every number in every alert message and requires an exactly equal number in that alert's grounding payload.

An unacknowledged portfolio condition is persisted once. Rechecking the same condition returns the existing row instead of creating a duplicate. After acknowledgment, a later check may create a new alert if the condition still exists, preserving the user's audit trail.

## Limitations

- Isolation Forest identifies statistical unusualness, not fraud, news events, or guaranteed downside.
- The contamination rate and profile thresholds are documented policy assumptions rather than labels fitted from investor outcomes.
- Optimize and scenario responses enqueue alert evaluation as FastAPI background work in a separate database session. This removes alert latency from the response, but a multi-instance production deployment should replace in-process background tasks with a durable worker and retry queue.
- Per-stock Isolation Forests are trained for each check rather than shared through a potentially stale in-memory cache. Feature construction was optimized during finalization, reducing a live six-holding check from a profiled 19.201 seconds to 7.416 seconds; this remaining work is acceptable only because it is off the response path.
