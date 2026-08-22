# OptiVest Architecture Diagram Assets

These four diagrams are maintained as Mermaid source and committed as rendered SVG assets. The shared configuration keeps the visual language consistent with OptiVest while using a light neutral canvas so GitHub and PDF exports remain legible.

## Prerequisites

- Node.js 20+
- npm/npx
- Mermaid CLI `@mermaid-js/mermaid-cli@11.16.0`

## Regenerate All SVGs

Run these commands from the repository root:

```bash
npx -y @mermaid-js/mermaid-cli@11.16.0 -i docs/diagrams/src/system-architecture.mmd -o docs/diagrams/system-architecture.svg -c docs/diagrams/mermaid-theme.json -b white
npx -y @mermaid-js/mermaid-cli@11.16.0 -i docs/diagrams/src/optimize-request-flow.mmd -o docs/diagrams/optimize-request-flow.svg -c docs/diagrams/mermaid-theme.json -b white
npx -y @mermaid-js/mermaid-cli@11.16.0 -i docs/diagrams/src/entity-relationship.mmd -o docs/diagrams/entity-relationship.svg -c docs/diagrams/mermaid-theme.json -b white
npx -y @mermaid-js/mermaid-cli@11.16.0 -i docs/diagrams/src/ai-ml-pipeline.mmd -o docs/diagrams/ai-ml-pipeline.svg -c docs/diagrams/mermaid-theme.json -b white
```

The version is deliberately pinned so Mermaid layout and SVG structure do not drift between regenerations. Edit the `.mmd` sources, not the generated SVG XML, then rerun the corresponding command and visually inspect the result before committing.

## Visual System

The assets use numbered reading stages, strong card hierarchy, rounded containers, subtle generated shadows, and consistent semantic color: blue for the authoritative OR core, amber for the additive AI layer, green for persisted data or successful outcomes, and charcoal for the user-facing OptiVest surface. Backgrounds remain white and all important meaning is also expressed in text, preserving print and accessibility legibility.
