## 1. Environment & Dependencies
- [ ] 1.1 Pin NVIDIA driver version and document NGC container tags for build/serve parity
- [ ] 1.2 Define container launch scripts (volumes, CUDA_VISIBLE_DEVICES, HF cache)

## 2. Model Snapshot
- [ ] 2.1 Record Hugging Face model revision hash, tokenizer files, and license acceptance process
- [ ] 2.2 Store snapshot metadata in the governance registry manifest template

## 3. Engine Build Pipeline
- [ ] 3.1 Document HF→TRT-LLM conversion steps for Qwen3-32B and calibration dataset requirements
- [ ] 3.2 Enumerate trtllm-build flags for W4A8, paged context FMHA, paged KV cache, and resource sizing
- [ ] 3.3 Provide reproducible build script (bash or Makefile) producing engine + manifest outputs

## 4. Validation & Handoff
- [ ] 4.1 Define smoke tests (prefill/generation checks) to validate the engine inside the container
- [ ] 4.2 Publish manifest schema capturing engine hash, quantization parameters, upstream hashes
