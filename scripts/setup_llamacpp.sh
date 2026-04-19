#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# setup_llamacpp.sh — Automated High-Precision Setup for PPISec
# Builds the engine and downloads the Llama-3.1 Logic Brain.
# ─────────────────────────────────────────────────────────────────────────────

set -e # Exit on error

# Directory setup
ROOT_DIR="$(pwd)"
LLAMA_DIR="$ROOT_DIR/llama.cpp"
MODEL_DIR="$ROOT_DIR/models"

echo -e "\033[94m[1/2] Building llama.cpp with Metal (M-Series) support...\033[0m"

if [ ! -d "$LLAMA_DIR" ]; then
    git clone https://github.com/ggerganov/llama.cpp "$LLAMA_DIR"
fi

cd "$LLAMA_DIR"
mkdir -p build
cmake -B build -DGGML_METAL=ON
cmake --build build --config Release -j

if [ ! -f "./build/bin/llama-server" ]; then
    echo -e "\033[91mError: Build failed. llama-server binary not found.\033[0m"
    exit 1
fi

echo -e "\033[92mBuild successful!\033[0m"

echo -e "\n\033[94m[2/2] Downloading High-Precision Logic Brain (Llama-3.1-8B)...\033[0m"
mkdir -p "$MODEL_DIR"

# Standardizing on Llama-3.1-8B (4-bit quantization - ~4.7GB)
# This model handles our "Visual Metadata" stream with surgical precision.
MODEL_URL="https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
MODEL_PATH="$MODEL_DIR/llama-3.1-8b-instruct.gguf"

if [ ! -f "$MODEL_PATH" ]; then
    curl -L "$MODEL_URL" -o "$MODEL_PATH"
else
    echo "Model already exists at $MODEL_PATH"
fi

# Cleanup old model if exists to save space
rm -f "$MODEL_DIR/qwen2-vl-7b-q4_k_m.gguf"
rm -f "$MODEL_DIR/mmproj-qwen2-vl.gguf"

echo -e "\n\033[92mSetup Complete.\033[0m"
echo -e "\033[1mRun 'python3 start.py' and select 'Local AI' to begin the demo.\033[0m"
