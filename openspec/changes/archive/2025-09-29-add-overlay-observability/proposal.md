## Why
Overlay operations require tight observability, risk controls, and internationalization support to maintain trust and comply with policy. We currently lack dashboards, logging, and multilingual safeguards for Module 4.

## What Changes
- Instrument overlay workflows with structured logging of prompts, evidence payloads, and LLM outputs, including hashes for reproducibility.
- Define dashboards and KPIs for proposal throughput, acceptance rate, rejection reasons, coverage gain, and pilot performance.
- Enforce risk controls (hallucination, bias, licensing) and internationalization requirements (language tags, jurisdiction variants, cross-lingual duplicate detection).
- Integrate risk signals and observability data into governance registry SLAs.

## Impact
- Affected specs: overlay
- Affected code: observability pipelines, metrics collectors, dashboard configuration, risk control validators, cross-lingual duplicate detectors
