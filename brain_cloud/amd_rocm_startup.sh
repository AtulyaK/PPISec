#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# amd_rocm_startup.sh — AMD Cloud ROCm VLM Launcher
#
# This script launches the vLLM server optimized for AMD GPUs (Instinct/Radeon)
# using ROCm. Perfect for the AMD Cloud Hackathon Track.
# ─────────────────────────────────────────────────────────────────────────────

# --- Configuration ---
MODEL=${VLLM_MODEL:-"Qwen/Qwen2-VL-7B-Instruct"}
PORT=${VLLM_PORT:-8001}
MAX_LEN=${VLLM_MAX_LEN:-4096}

echo "Starting vLLM Server on AMD ROCm Infrastructure..."
echo "Model: $MODEL"
echo "Port:  $PORT"

# Check for Docker before continuing
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found."
    exit 1
fi

# Launch vLLM using the official ROCm optimized container
docker run -d --name vllm-rocm-server \
    --device /dev/kfd --device /dev/dri \
    --security-opt seccomp=unconfined \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p $PORT:8000 \
    --ipc=host \
    rocm/vllm-rocm:latest \
    --model $MODEL \
    --max-model-len $MAX_LEN \
    --dtype auto

echo "AMD vLLM is starting in the background (Docker container: vllm-rocm-server)."
echo "Check logs with: docker logs -f vllm-rocm-server"
