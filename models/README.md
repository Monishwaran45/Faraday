# Faraday QNN Model Directory

This directory holds compiled Qualcomm Neural Network (QNN) context binaries optimized for the **Snapdragon® X Elite Hexagon NPU**.

---

##  How Model Loading Works

Faraday is designed with **zero-friction portability**:

1. **Snapdragon X Elite Laptop with QNN Binaries Present:**
   - Faraday automatically detects the compiled binaries in `models/qwen2-7b-qnn/` (or via `FARADAY_MODEL_DIR`).
   - Executes INT4/W4A16 quantized neural inference directly on the **Hexagon NPU**.

2. **Any Machine After Cloning (Intel/AMD, Mac, Linux, or Snapdragon without binaries):**
   - Faraday automatically and gracefully activates `MockBackend` (AST heuristic engine).
   - All CLI commands (`faraday .`), secret scanners, SARIF generation, reports, and unit tests (`uv run pytest`) work **100% out of the box with zero errors**.

---

##  How to Setup QNN Models on a Snapdragon X Elite Machine

If you are cloning this repository onto a Snapdragon X Elite laptop and want to run on the physical NPU:

### Method 1: Export via Qualcomm AI Hub (Recommended)
```bash
# 1. Install Qualcomm AI Hub models package
pip install "qai_hub_models[qwen2-7b-instruct-quantized]"

# 2. Export context binaries compiled for Snapdragon X Elite
python -m qai_hub_models.models.qwen2_7b_instruct_quantized.export \
    --device "Snapdragon X Elite CRD" \
    --skip-inferencing \
    --skip-profiling \
    --output-dir ./models/qwen2-7b-qnn
```

### Method 2: Point to an Existing Models Folder
If you already have your QNN context binary folder downloaded elsewhere on your machine:
```powershell
# In PowerShell:
$env:FARADAY_MODEL_DIR = "C:\path\to\your\qnn_models"

# Or in bash/zsh:
export FARADAY_MODEL_DIR="/path/to/your/qnn_models"
```

### Expected File Structure:
```
models/
└── qwen2-7b-qnn/
    └── qwen2_7b_instruct-qnn_context_binary-w4a16-qualcomm_snapdragon_x_elite/
        ├── weight_sharing_model_1_of_4.serialized.bin
        ├── weight_sharing_model_2_of_4.serialized.bin
        ├── weight_sharing_model_3_of_4.serialized.bin
        └── weight_sharing_model_4_of_4.serialized.bin
```
