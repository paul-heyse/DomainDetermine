## 1. Triton Deployment
- [ ] 1.1 Pin Triton TRT-LLM container version aligned with TensorRT-LLM build
- [ ] 1.2 Provide launch scripts/docker-compose for Triton with GPU access and model repository mount

## 2. Model Repository Configuration
- [ ] 2.1 Populate reference repo structure (tensorrt_llm/1/) with engine + tokenizer assets
- [ ] 2.2 Configure `config.pbtxt` for in-flight batching, paged KV reuse, chunked context, guided decoding (xgrammar)

## 3. Runtime Policies
- [ ] 3.1 Define default decoding parameters per use case (generate_json, rank_candidates, judge)
- [ ] 3.2 Document guided JSON schema workflows and tokenizer info generation

## 4. Observability & Health
- [ ] 4.1 Add health checks, performance metric collection (return_perf_metrics), and logging requirements
- [ ] 4.2 Provide rollback/runbook instructions for Triton deployment
