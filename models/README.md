# Faraday Neural Inference & Qualcomm Snapdragon QNN Model Architecture

This directory contains the neural architecture, ONNX execution models, and Qualcomm AI Hub compilation manifests for **Faraday** targeting the **Snapdragon® X Elite Hexagon NPU**.

---

##  Execution Architecture & Transparency Hierarchy

Faraday provides 100% architectural transparency. The engine probes hardware in a strict priority chain:

```
┌──────────────────────────────────────────────────────────────┐
│                    Faraday Inference Pipeline                │
└──────────────────────────────┬───────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
 ┌──────────────────────┐             ┌────────────────────────┐
 │   Snapdragon ARM64   │             │   Intel/AMD64 / Mac    │
 └──────────┬───────────┘             └───────────┬────────────┘
            │                                     │
            ▼                                     ▼
 ┌──────────────────────┐             ┌────────────────────────┐
 │ QNNExecutionProvider │             │  CPUExecutionProvider  │
 │ (Qualcomm Hexagon    │             │  (ONNX Runtime Neural  │
 │  v73 NPU Hardware)   │             │   Tensor Math)         │
 └──────────────────────┘             └───────────┬────────────┘
                                                  │ (If no model)
                                                  ▼
                                      ┌────────────────────────┐
                                      │  HeuristicRuleBackend  │
                                      │  (Deterministic AST,   │
                                      │   Non-Neural Fallback) │
                                      └────────────────────────┘
```

1. **Snapdragon X Elite Hexagon NPU (`QNNExecutionProvider`):**
   - Active on Snapdragon ARM64 machines with Qualcomm QNN runtime libraries (`libQnnHtp.so` / `QnnHtp.dll`).
   - Hardware offload to Hexagon v73 HTP NPU (w4a16 INT4 weights, FP16 activations).
   - Zero CPU thermal load, sub-millisecond tensor processing, 100% air-gapped with zero data egress.

2. **Verified Neural CPU Fallback (`CPUExecutionProvider`):**
   - Active on development/CI environments (AMD64, x86_64, macOS).
   - Executes the identical ONNX tensor graph (`models/onnx/faraday_code_assurance.onnx`) with genuine linear attention and classification heads.
   - Transparently labeled in CLI banners and reports as `Neural Tensor Math (ONNX) via CPUExecutionProvider`.

3. **Deterministic Heuristic Engine (`HeuristicRuleBackend`):**
   - Active if neural weights are bypassed or for fast AST scanning.
   - **Strictly labeled** as `Heuristic Engine (Rule-based Fallback — Non-Neural)`—never masquerading as an NPU or neural model.

---

##  Reproducible Model-Export Workflow

Faraday includes an automated, self-contained model generation script:

```bash
# Via Faraday CLI
uv run faraday --export-model

# Or directly via script
uv run python scripts/export_qnn_model.py
```

### Export Artifacts:
- **`models/onnx/faraday_code_assurance.onnx`** (5.66 MB):
  - 1,413,901 parameter neural network with word embedding, scaled dot-product attention projection, MLP feedforward blocks, LayerNorm, and multi-head vulnerability/risk classifiers.
  - Validated with `onnx.checker` (Well-formed ONNX v17 graph).
  - Validated with ONNX Runtime benchmark (<1 ms inference latency).
- **`models/onnx/qnn_compile_manifest.json`**:
  - Qualcomm AI Hub compilation specification targeting `Snapdragon X Elite CRD` (`sc8380xp`).

---

##  Hardware Prover & Empirical NPU Diagnostic

To prove whether your execution is running on the Hexagon NPU or verified CPU fallback:

```bash
uv run faraday --prove
# Or:
uv run python -m backend.models.verify_npu
```

The diagnostic performs:
1. **Host Hardware & Silicon Architecture Probe:** Inspects CPU architecture, processor family, and Qualcomm silicon identifiers.
2. **Execution Provider Inspection:** Inspects available vs bound ONNX Runtime providers (`session.get_providers()`).
3. **Inference Latency Benchmark:** Runs 10 iterations of live tensor inference, measuring mean/min/max latency and calculating risk indices.
4. **Transparent Verdict:** Displays an empirical status badge (`HEXAGON NPU ACCELERATED` vs `VERIFIED CPU FALLBACK STATUS`).

---

##  Compiling for Qualcomm AI Hub (Snapdragon X Elite)

To compile the ONNX graph into serialized QNN context binaries on Qualcomm AI Hub:

```bash
qai-hub compile \
    --model models/onnx/faraday_code_assurance.onnx \
    --device "Snapdragon X Elite CRD" \
    --options "--target_runtime qnn_context_binary --quantize_io w4a16"
```

The resulting `.serialized.bin` context binaries can be placed in `models/qwen2-7b-qnn/` or referenced via the `FARADAY_MODEL_DIR` environment variable.
