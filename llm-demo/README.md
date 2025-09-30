# LLM Demo Warmup

The `llm-demo` directory hosts a self-contained warmup harness for validating that a TensorRT-LLM compiled model can be downloaded, cached, served through Triton, and exercised by an interactive chat loop. The tooling orchestrates:

1. **Preflight validation** – verify GPU/driver/software requirements and record the host manifest.
2. **Model acquisition** – download or reuse cached model weights/tokenizer assets with checksum validation and expiry handling.
3. **Engine build and launch** – compile the TensorRT-LLM engine, start Triton (via Docker Compose or local processes), and block until HTTP/gRPC/metrics endpoints are healthy.
4. **Warmup inference** – run scripted prompts, capture GPU utilization, compare responses to golden expectations, and record structured telemetry.
5. **Chat session** – provide a CLI chat with rolling memory, secret redaction, transcript persistence, and session metadata linkage.
6. **Teardown / cleanup** – stop services, release GPU memory, and optionally purge caches according to retention rules.

## Quick start

```bash
cd llm-demo
python runner.py warmup preflight --prereq-config config/prerequisites.yaml
python runner.py warmup run --config config/model.yaml
python runner.py chat start --config config/model.yaml
python runner.py warmup teardown --config config/model.yaml
python runner.py warmup verify-negative --config config/model.yaml
```

Each warmup run creates a timestamped directory under `logs/<run-id>/` and `state/<run-id>-manifest.json` summarizing environment hashes, GPU snapshots, cache usage, and metrics. Chat transcripts are saved under `transcripts/<session-id>.jsonl` with secrets redacted.

### Offline mode

Set `offline_mode: true` in `config/model.yaml` after a successful online run to reuse cached artifacts. The CLI command `python runner.py warmup verify-negative` exercises failure paths (including offline cache expiry) to ensure diagnostics remain actionable.

Refer to `docs/prerequisites.md` for manual setup steps or `python runner.py warmup preflight --help` for CLI options.
