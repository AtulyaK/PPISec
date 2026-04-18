# vLLM Deployment on AMD MI300X
FROM rocm/vllm:rocm6.3.1_mi300_ubuntu22.04_py3.12_vllm_0.6.6

# Set environment variables for AMD optimized kernels
ENV VLLM_ROCM_USE_AITER=1

# Expose the OpenAI-compatible endpoint port
EXPOSE 8000

# Entrypoint for serving a VLM
ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server"]
