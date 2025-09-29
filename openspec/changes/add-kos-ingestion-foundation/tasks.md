## 1. Ingestion Foundations
- [ ] 1.1 Document supported input formats (SKOS/RDF, OWL, OBO) and required tooling
- [ ] 1.2 Define canonical concept schema and snapshot manifest structure
- [ ] 1.3 Implement normalization pipeline across sample SKOS, OWL, OBO fixtures
- [ ] 1.4 Set up storage outputs (rdflib graph store + Parquet/DuckDB tables)
- [ ] 1.5 Instrument ingest run with structured logs, metrics, and snapshot IDs
- [ ] 1.6 Add SHACL and tabular validation checks with example thresholds
- [ ] 1.7 Validate proposal with `openspec validate add-kos-ingestion-foundation --strict`
