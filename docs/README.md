# OptiVest Documentation

This directory contains the technical documentation, reproducible diagrams, report material, and presentation-ready visuals for OptiVest.

## Documentation map

| Area | Contents |
| --- | --- |
| [System diagrams](diagrams/README.md) | Architecture, optimization request flow, AI/ML pipeline, and entity relationships |
| [Final report](final-report/README.md) | Report chapters and verified application screenshots |
| [Presentation visuals](presentation/README.md) | Reproducible PNG/SVG diagrams and charts for slides |
| [AI personalization](ai-personalization/) | Risk classification, alerts, and grounded assistant methodology |
| [Requirements and novelty](phase1-requirements/) | Problem statement, requirements, research gap, novelty, and traceability |
| [Methodology notes](methodology-notes.md) | Dataset, optimization, backtesting, and interpretation constraints |

## Visual asset organization

### Engineering diagrams

- [`system-architecture.svg`](diagrams/system-architecture.svg) — end-to-end application architecture
- [`optimize-request-flow.svg`](diagrams/optimize-request-flow.svg) — portfolio optimization sequence
- [`ai-ml-pipeline.svg`](diagrams/ai-ml-pipeline.svg) — model-assisted decision workflow
- [`entity-relationship.svg`](diagrams/entity-relationship.svg) — persisted data relationships

The Mermaid source for each diagram is stored in [`diagrams/src`](diagrams/src/) so the SVG files can be regenerated instead of edited manually.

### Application screenshots

Verified interface captures are stored in [`final-report/screenshots`](final-report/screenshots/), numbered in the order in which the product workflow is normally demonstrated:

1. Dashboard
2. Portfolio Builder
3. Portfolio Details and explanations
4. Scenario comparison
5. Out-of-sample analytics
6. Reports
7. Generated PDF report

### Presentation visuals

Slide-ready assets are stored in [`presentation/generated`](presentation/generated/). PNG files are convenient for PowerPoint, while SVG files are preferable when scalable vector quality is required. See the [presentation visual catalogue](presentation/README.md) for previews and regeneration instructions.

## Asset conventions

- Use lowercase, descriptive, numbered filenames for presentation order.
- Keep editable source files beside their generated outputs.
- Prefer SVG for diagrams and PNG for application screenshots.
- Do not replace verified metrics with invented demonstration values.
- Update the relevant index whenever a visual is added or renamed.
