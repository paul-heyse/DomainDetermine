## 1. Candidate Mining
- [x] 1.1 Implement corpus-driven candidate extraction (YAKE/KeyBERT, collocations) scoped by Module 2 gap diagnostics
- [x] 1.2 Build ontology-driven hole detection (sibling clustering, external KOS lookup) with policy filters applied

## 2. Retrieval-Augmented Prompting
- [x] 2.1 Assemble evidence packs: parent definitions, sibling summaries, editorial rules, corpus snippets
- [x] 2.2 Design structured JSON schemas and grammar-constrained decoding for LLM proposal generation
- [x] 2.3 Implement self-critique prompts to test overlap, annotatability, and policy compliance referencing guardrail text

## 3. Automated Vetting
- [x] 3.1 Add duplicate/conflict scoring using lexical + embedding similarity against Module 1+overlay nodes
- [x] 3.2 Validate citations against evidence pack offsets and reject hallucinated references
- [x] 3.3 Run editorial linting (naming, length, language availability) and graph sanity rules (no cycles, child count limits)

## 4. Split/Merge & Synonym Handling
- [x] 4.1 Extend structured outputs to capture split/merge proposals with migration hints
- [x] 4.2 Persist synonym suggestions as altLabels with language tags after vetting passes
