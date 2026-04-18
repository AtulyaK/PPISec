# Quick Start Guide (< 10 Minutes)

Get the Semantic Firewall up and running quickly. This guide assumes you have a basic understanding of terminal commands and Python/Node.js.

## 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **Docker** (for VLM serving)

## 2. Infrastructure Setup
The system is composed of three logical nodes. You can run all on one machine (localhost) or distribute them.

### Node A: Visual Cortex (VLM)
Requires an NVIDIA GPU.
```bash
cd brain_cloud
bash startup.sh
# Port 8001 will be active
```

### Node B: The Mind (Firewall + Brain)
Runs on any CPU.
```bash
# Window 1: Firewall Governor
cd firewall_governor
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export PYOPENGL_PLATFORM=osmesa
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Window 2: Brain Task Executor
export VLLM_URL=http://localhost:8001/v1
python3 ../brain_cloud/task_executor.py
# Port 8002 will be active
```

### Node C: The Window (Agent Glass UI)
Runs on your local machine.
```bash
cd agent_glass
export NEXT_PUBLIC_BRAIN_URL=http://localhost:8002
npm install
npm run dev
# Open http://localhost:3000
```

## 3. Immediate Verification
1. Open the dashboard at `http://localhost:3000`.
2. Select a deployment (e.g., Pharmacy).
3. Type a directive like *"Pick up the bottle"* and press Enter.
4. Observe the **Audit Trail** (should show Protocol::PASS) and the **3D Scene** (arm should move).
5. Open the **Security Lab** (Bug icon) and toggle **Activate Trojan**.
6. Issue a new command and verify the **Protocol::VETO** or **Protocol::WARN** flow.
7. Click the **Master System Reset** (Refresh icon) to clear all backend memory and start a fresh demo.

---
**Next Steps:**
- For detailed multi-node cloud deployment, see [DEPLOYMENT.md](./DEPLOYMENT.md).
- To understand the security logic, see [ARCHITECTURE.md](./ARCHITECTURE.md).
