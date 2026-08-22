# Grounded Portfolio Assistant Methodology

## Scope and safety boundary

The OptiVest assistant is an offline natural-language routing layer over existing portfolio evidence. It does not call an LLM or any external generative service. A TF-IDF classifier selects one of seven fixed intents, slot extraction identifies a stock or scenario parameter, and deterministic templates render only values returned by the optimization, explainability, analytics, or scenario modules. Questions below the `0.55` confidence threshold receive an `UNKNOWN` clarification response.

## Training data

The reproducible generator starts with 15 hand-authored question patterns for each intent and performs transparent substitutions of Nifty-50 symbols, sectors, shock magnitudes, shock verbs, and conversational wrappers. The committed dataset contains 2,100 rows: 300 synthetic examples for each of the seven intents. These are generated examples, not observed investor conversations.

## Model and measured evaluation

The classifier is a scikit-learn pipeline containing unigram/bigram TF-IDF features and multinomial logistic regression. A stratified 80/20 split with random seed 42 produced 1,680 training examples and 420 held-out examples. The measured training and held-out accuracies were both `1.0000`.

The held-out confusion matrix was:

| Actual / predicted | Allocation | Diversification | Inclusion | Exclusion | Shock | Risk | Unknown |
|---|---:|---:|---:|---:|---:|---:|---:|
| Allocation | 60 | 0 | 0 | 0 | 0 | 0 | 0 |
| Diversification | 0 | 60 | 0 | 0 | 0 | 0 | 0 |
| Inclusion | 0 | 0 | 60 | 0 | 0 | 0 | 0 |
| Exclusion | 0 | 0 | 0 | 60 | 0 | 0 | 0 |
| Shock | 0 | 0 | 0 | 0 | 60 | 0 | 0 |
| Risk | 0 | 0 | 0 | 0 | 0 | 60 | 0 |
| Unknown | 0 | 0 | 0 | 0 | 0 | 0 | 60 |

No notable intent pair was confused in this synthetic held-out split. This perfect score demonstrates that the generated intent patterns are separable; it must not be interpreted as 100% accuracy on unrestricted real investor language. The safe fallback threshold is retained for unfamiliar wording.

## Grounding and no-hallucination control

Every response returns a grounding bundle with the source name, fields, and exact values used by its template. Inclusion and exclusion answers reuse the stored `narrative_text`; risk answers use out-of-sample analytics; allocation answers reuse the Phase 5 portfolio summary; diversification answers use the computed concentration breakdown. Shock questions invoke the real Phase 6 transformation and optimizer re-solve before reporting metric deltas.

The structural no-hallucination test extracts every number from generated answers across all intents and requires an exactly equal value in the response grounding. An untraceable number fails the test.

## Limitations

- The language dataset is synthetic and English-only.
- Symbol extraction is exact/fuzzy matching against the known universe, not a learned entity model.
- The assistant explains system calculations; it does not provide open-ended financial advice.
- Quality on natural user questions should be reassessed with an anonymized, human-labeled corpus before production deployment.
