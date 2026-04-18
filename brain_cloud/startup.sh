#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# startup.sh — Universal VLM Launcher (NVIDIA/CUDA)
#
# This script launches the vLLM server on any machine with an NVIDIA GPU.
# It uses the official NVIDIA Docker container to avoid driver/dependency hell.
# Works on: Local PCs, AWS, Azure, RunPod, Lambda Labs, GCP.
# ─────────────────────────────────────────────────────────────────────────────

# --- Configuration (Override via env vars) ---
MODEL=${VLLM_MODEL:-"Qwen/Qwen2-VL-7B-Instruct"}
PORT=${VLLM_PORT:-8001}
MAX_LEN=${VLLM_MAX_LEN:-4096}
QUANTIZATION=${VLLM_QUANTIZATION:-""} # e.g., "awq" or "gptq" for smaller VRAM

echo "Starting vLLM Server (Platform Agnostic)..."
echo "Model: $MODEL"
echo "Port:  $PORT"

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found."
    echo "Please install Docker and the NVIDIA Container Toolkit:"
    echo "https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    exit 1
fi

# Build optional quantization flag
QUANT_FLAG=""
if [ -n "$QUANTIZATION" ]; then
    QUANT_FLAG="--quantization $QUANTIZATION"
    echo "Quantization: $QUANTIZATION"
fi

# Launch vLLM via Docker
docker run --gpus all -d --name vllm-server \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p $PORT:8000 \
    --ipc=host \
    vllm/vllm-openai:latest \
    --model $MODEL \
    --max-model-len $MAX_LEN \
    --dtype auto \
    $QUANT_FLAG

echo "vLLM is starting in the background (Docker container: vllm-server)."
echo "Check logs with: docker logs -f vllm-server"
