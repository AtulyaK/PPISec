# Full Deployment Guide (Step-by-Step)

This guide provides exhaustive instructions for deploying the Semantic Firewall across a distributed environment (Local + Cloud).

---

## 1. Node A: The GPU Node (Visual Cortex)
The GPU Node handles heavy VLM inference. This can be a local machine with an NVIDIA GPU or a cloud instance (AWS G4dn, RunPod, Lambda Labs, etc.).

### 1.1 Prerequisites
- Ubuntu 22.04 LTS (Recommended)
- NVIDIA Drivers + Docker + NVIDIA Container Toolkit

### 1.2 Installation
```bash
git clone https://github.com/AtulyaK/PPISec.git
cd PPISec/brain_cloud
```

### 1.3 Execution
Launch the VLM server. By default, it uses Qwen2-VL-7B.
```bash
# Optional: Set environment variables for custom config
export VLLM_PORT=8001
export VLLM_QUANTIZATION=awq  # Use awq for lower VRAM (e.g., T4/16GB)

bash startup.sh
```
**Verification:** Run `curl http://localhost:8001/v1/models`. You should see the model list.

---

## 2. Node B: The Logic Node (Governor & Brain)
The Logic Node runs the security middleware and the agent loop. It requires minimal CPU resources.

### 2.1 Installation
```bash
git clone https://github.com/AtulyaK/PPISec.git
cd PPISec/firewall_governor
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install sentence-transformers rtamt
```

### 2.2 Configure Connections
Set the IP address of your GPU Node so the Brain can reach it.
```bash
export VLLM_URL=http://<GPU_NODE_IP>:8001/v1
export ALLOW_ORIGINS="*"  # Allow MacBook UI to connect
```

### 2.3 Execution
Start the Governor (Security) and the Task Executor (Orchestrator).
```bash
# Window 1: Firewall Governor
export PYOPENGL_PLATFORM=osmesa
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Window 2: Brain Task Executor
python3 ../brain_cloud/task_executor.py
```

---

## 3. Node C: The Operator Machine (MacBook/PC)
The dashboard where you interact with the system.

### 3.1 Installation
```bash
git clone https://github.com/AtulyaK/PPISec.git
cd PPISec/agent_glass
npm install
```

### 3.2 Configure Connection
Point the UI to your Logic Node's IP.
```bash
export NEXT_PUBLIC_BRAIN_URL=http://<LOGIC_NODE_IP>:8002
```

### 3.3 Execution
```bash
npm run dev
```

---

## 4. Networking & Security Tips

### 4.1 Tunnels (Tailscale)
If your nodes are behind NAT (not public IPs), install **Tailscale** on all three. Use the Tailscale `100.x.x.x` IPs for all configuration variables. This is the most secure and reliable method.

### 4.2 Port Summary
- **8000:** Firewall Governor API
- **8001:** vLLM OpenAI-Compatible API
- **8002:** Brain Task Executor API
- **3000:** Agent Glass Dashboard UI
