# On-Device VLA: Full Local Execution Guide

This document explains how to run the entire PPISec pipeline—including the **Vision-Language Model (VLM)**—locally on your MacBook M2. This replaces the "Mock VLM" with actual local AI inference.

---

## 1. Feasibility & Hardware Requirements

Running a "Full" setup on-device means your computer must act as both the **Mind** (Logic) and the **Visual Cortex** (GPU).

| Component | Resource | M2 Requirement |
| :--- | :--- | :--- |
| **Firewall & UI** | CPU / RAM | Minimal (fits on any M2) |
| **VLM (Qwen2-VL-7B)** | Unified Memory | **Min: 16GB** (8-bit) / **Rec: 32GB+** |

*Note: If you have an 8GB RAM MacBook, you cannot run a 7B model locally; you must continue using the `mock_vlm.py` or a Cloud VLM.*

---

# On-Device VLA: Local Execution Guide

This document explains how to run the real AI models locally on your MacBook M2. We offer two paths: **Ollama** (Easiest) and **llama.cpp** (Highest Efficiency).

---

## 1. Engine Comparison

| Feature | **Ollama** | **llama.cpp** |
| :--- | :--- | :--- |
| **Best For** | "It just works" setup. | Pro users / Highest performance. |
| **Effort** | Low (1-click app install). | Medium (build from source). |
| **Overhead** | Moderate management service. | Near-Zero (raw binary). |
| **Hardware** | Apple Metal (Automatic). | Apple Metal (Customizable). |

---

## 2. Path A: Ollama (Recommended for Hackathons)

1. **Install:** Download from [ollama.com](https://ollama.com).
2. **Launch:** Run `python3 start.py` and select **Option 2**.
3. **Model:** The wizard will list your installed models. If none are found, run `ollama pull qwen2-vl` in your terminal.

---

## 3. Path B: llama.cpp (The "Pro" Setup)

Directly running `llama.cpp` is the most efficient way to use your M2's GPU.

1. **Automated Setup:**
   ```bash
   bash scripts/setup_llamacpp.sh
   ```
   *This clones the repo, builds the `llama-server` binary with Metal support, and downloads an optimized 4-bit Qwen2-VL model.*

2. **Launch:**
   Run `python3 start.py` and select **Option 3**. The wizard will automatically find the binary and start the server on port 8080.

---

## 4. Hardware Guidelines (RAM)

- **16GB RAM:** Run `qwen2-vl` (7B) in 4-bit quantization or `moondream` (1.6B).
- **32GB+ RAM:** Can comfortably run the full 7B or 14B models.
2.  **Agnostic API:** Because `llama.cpp` and `MLX` provide OpenAI-compatible endpoints, the `brain_cloud/task_executor.py` doesn't know (or care) if the model is on an AMD Cloud cluster or your local Metal GPU.
3.  **Local Rendering:** The `firewall_governor` uses `osmesa` (CPU rendering) or `egl` (GPU rendering). On your Mac, it defaults to a stable CPU render, ensuring it doesn't fight the VLM for GPU cycles.

---

## 5. Potential Performance Gaps
*   **Latency:** Inference on an M2 will be slower than a Cloud A100. Expect **2–5 seconds** per "Plan" step.
*   **Thermal Throttling:** Running a 7B model locally will generate heat. Ensure your MacBook has airflow for long-running simulations.
