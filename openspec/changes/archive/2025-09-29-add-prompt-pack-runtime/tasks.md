## 1. Runtime Manifests

- [x] 1.1 Define manifest format mapping templates to model routes, parameter ceilings, fallback order
- [x] 1.2 Integrate manifest loading with LLM provider configuration

## 2. Structured Output Enforcement

- [x] 2.1 Implement guided decoding/structured output hooks (XGrammar/jsonschema) per template
- [x] 2.2 Add validation checks ensuring responses conform to schemas before hand-off

## 3. Retrieval & Token Budget Enforcement

- [x] 3.1 Build request builders applying retrieval policies and token budgeting logic
- [x] 3.2 Implement citation enforcement (source tracking, span capture) for proposal/judge templates

## 4. Warm-Up & Health

- [x] 4.1 Create warm-up routines exercising all templates against the serving stack
- [x] 4.2 Integrate warm-up status and health checks into observability dashboards
