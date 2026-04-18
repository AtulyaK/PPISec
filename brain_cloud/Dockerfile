# Universal vLLM Deployment
FROM vllm/vllm-openai:latest

# Expose vLLM port
EXPOSE 8000

# Set default model
ENV VLLM_MODEL="Qwen/Qwen2-VL-7B-Instruct"

ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server"]
CMD ["--model", "Qwen/Qwen2-VL-7B-Instruct", "--max-model-len", "4096"]
