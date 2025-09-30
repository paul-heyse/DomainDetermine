## 1. Triton Deployment

- [x] 1.1 Pin Triton TRT-LLM container version aligned with TensorRT-LLM build
- [x] 1.2 Provide launch scripts/docker-compose for Triton with GPU access and model repository mount

## 2. Model Repository Configuration

- [x] 2.1 Populate reference repo structure (tensorrt_llm/1/) with engine + tokenizer assets
- [x] 2.2 Configure `config.pbtxt` for in-flight batching, paged KV reuse, chunked context, guided decoding (xgrammar)

## 3. Runtime Policies

- [x] 3.1 Define default decoding parameters per use case (generate_json, rank_candidates, judge)
- [x] 3.2 Document guided JSON schema workflows and tokenizer info generation

## 4. Observability & Health

- [x] 4.1 Add health checks, performance metric collection (return_perf_metrics), and logging requirements
- [x] 4.2 Provide rollback/runbook instructions for Triton deployment
