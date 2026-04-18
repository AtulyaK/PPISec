# Universal Deployment Guide (Platform Agnostic)

This guide explains how to deploy the Semantic Firewall stack on **any** platform: local machines, AWS, GCP, Azure, RunPod, Lambda Labs, etc.

## 1. Architecture Overview

The system consists of three logical components, which can be run on a single machine or distributed across multiple nodes.

1.  **VLM / Visual Cortex (Port 8001):** Requires an NVIDIA GPU. Runs Qwen2-VL-7B via vLLM.
2.  **Logic Node (Ports 8000, 8002):** Requires a basic CPU. Runs the Firewall Governor and the Brain Task Executor.
3.  **Agent Glass (Port 3000):** Runs on your local machine. The Next.js frontend.

## 2. Deploying the GPU Node (VLM)

You can run this on any machine with an NVIDIA GPU and Docker installed.

```bash
# 1. SSH into your GPU machine
# 2. Clone the repository
git clone <your-repo-url>
cd StarHacks_04_2026/brain_cloud

# 3. Launch vLLM via the universal script
# This downloads the official NVIDIA Docker image and starts the server on port 8001.
bash startup.sh
```

## 3. Deploying the Logic Node (Firewall + Brain)

You can run this on the same GPU machine, a cheap cloud VPS, or your local laptop.

```bash
# 1. Install Python 3.10+
cd StarHacks_04_2026/firewall_governor
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
pip install sentence-transformers rtamt

# 3. Start Firewall (Window 1)
export PYOPENGL_PLATFORM=osmesa
export ALLOW_ORIGINS="*" # Be more restrictive in production
uvicorn src.main:app --host 0.0.0.0 --port 8000

# 4. Start Task Executor (Window 2)
# Replace <GPU_NODE_IP> with the IP of your GPU Node. If running on the same machine, leave it as localhost.
export VLLM_URL=http://<GPU_NODE_IP>:8001/v1
export FIREWALL_URL=http://localhost:8000
python3 ../brain_cloud/task_executor.py
```

## 4. Connecting the Frontend (Agent Glass)

On your local machine (e.g., MacBook):

```bash
cd StarHacks_04_2026/agent_glass

# Set the URL to where your Logic Node's Task Executor is running (Port 8002)
# If running locally: http://localhost:8002
export NEXT_PUBLIC_BRAIN_URL=http://<LOGIC_NODE_IP>:8002

npm install
npm run dev
```

## 5. Networking Notes

*   **Ports:** Ensure ports `8000`, `8001`, and `8002` are open on the respective machines' firewalls/security groups.
*   **Tunnels:** If your machines don't have public IPs or you want secure communication, install **Tailscale** on all nodes (GPU Node, Logic Node, Local MacBook). Use the Tailscale `100.x.x.x` IPs in the configuration variables.
