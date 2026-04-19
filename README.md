<div align="center">
  <img src="./docs/assets/hero.png" alt="PPISec Hero Banner" width="100%">

  # PPISec: Semantic Firewall for VLA Robotic Agents

  **Preventing Physical Prompt Injection Attacks (PPIA) through Cognitive Governance.**

  [![Platform Agnostic](https://img.shields.io/badge/platform-agnostic-blue.svg)](https://github.com/AtulyaK/PPISec)
  [![Status: Hackathon Prototype](https://img.shields.io/badge/status-hackathon_prototype-orange.svg)](https://github.com/AtulyaK/PPISec)
  [![Security: AASL Evaluated](https://img.shields.io/badge/security-AASL_Compliant-success.svg)](https://github.com/AtulyaK/PPISec)
</div>

## 🌟 Overview

PPISec is an AASL-compliant (Autonomous Agent Safety Layer) middleware designed to intercept and validate the semantic intent of Vision-Language-Action (VLA) robotic agents. It specifically targets **Physical Prompt Injection Attacks (PPIA)**—where an adversary manipulates a robot's behavior by placing malicious "instructions" in the physical environment (e.g., Trojan Signs, ambiguous audio, or adversarial stickers).

At its core, PPISec acts as a **Cognitive Governor**, serving as an unbypassable checkpoint between the "Brain" (Large Vision-Language Models) and the "Muscle" (Robot Control Systems). Every proposed action is subjected to a strict 4-stage, millisecond-latency security pipeline before physical execution is permitted.

---

## 🛡️ The 4-Stage Security Pipeline

| Stage | Component | Defense Mechanism | Latency |
|---|---|---|---|
| **1** | **Policy Manifest** | O(1) Radix Tree lookup for forbidden action/target pairs. | ~0ms |
| **2** | **MCR Gate** | Multimodal Conflict Resolver. Validates source modality trust and confidence thresholds. | ~1ms |
| **3** | **Audio Align** | Sentence-Transformer semantic cross-check between user transcript and VLM intent. | ~5ms |
| **4** | **LTL Evaluator** | Linear Temporal Logic & STL monitors for spatial bounds and temporal invariants. | ~10-50ms |

---

## 🏗️ System Architecture

The project is designed with a **Platform-Agnostic Distributed Architecture**, allowing components to run across local hardware and cloud providers seamlessly.

<div align="center">
  <img src="./docs/assets/dashboard.png" alt="Agent Glass SOC Dashboard" width="90%">
  <br>
  <em>The Agent Glass SOC Dashboard monitoring real-time VLA logic evaluation.</em>
</div>

- **Agent Glass (Frontend):** A Next.js + Three.js dashboard providing a 3D "Sandbox" for real-time visualization of the robot's state and the Firewall's decisions.
- **Firewall Governor (Security Node):** A FastAPI-based security gateway that orchestrates the 4-stage pipeline and manages the virtual robot simulation.
- **Brain Cloud (Agent Loop):** The sense-plan-act orchestrator that queries the Vision-Language Model (VLM) and submits intents to the Firewall.
- **VLM (Visual Cortex):** Served via vLLM, providing OpenAI-compatible multimodal inference (e.g., Qwen2-VL-7B).

---

## 🚀 Quick Start

### 1. Requirements
- **Python 3.10+** (for Firewall and Brain)
- **Node.js 18+** (for Agent Glass)
- **NVIDIA GPU** (optional, for local VLM inference) or a Cloud GPU endpoint.

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/AtulyaK/PPISec.git
cd PPISec

# Install Backend dependencies
cd firewall_governor
pip install -r requirements.txt

# Install Frontend dependencies
cd ../agent_glass
npm install
```

### 3. Launching the System

The system is configured via environment variables. See [Deployment Guide](docs/deployment_guide.md) for detailed distributed setup.

**Node 1: The VLM (GPU Required)**
```bash
cd brain_cloud
bash startup.sh
```

**Node 2: The Firewall & Brain**
```bash
# In Window 1: Start Firewall
export PYOPENGL_PLATFORM=osmesa
uvicorn firewall_governor.src.main:app --host 0.0.0.0 --port 8000

# In Window 2: Start Brain Executor
export VLLM_URL=http://localhost:8001/v1
python3 brain_cloud/task_executor.py
```

**Node 3: The Dashboard**
```bash
cd agent_glass
export NEXT_PUBLIC_BRAIN_URL=http://localhost:8002
npm run dev
```

---

## 📚 Documentation

Detailed documentation is available in the [`/docs`](./docs) folder:

- 🏅 **[COMPREHENSIVE_VLA_VULNERABILITY_STUDY.md](./docs/COMPREHENSIVE_VLA_VULNERABILITY_STUDY.md)**: Extensively charts VLA failure rates against empirical Physical Injections.
- **[QUICKSTART.md](./docs/QUICKSTART.md)**: Get running in under 10 minutes.
- **[LOCAL_TESTING.md](./docs/LOCAL_TESTING.md)**: Full scale simulation test guide.
- **[ON_DEVICE_VLA.md](./docs/ON_DEVICE_VLA.md)**: Guide for running real AI models locally on M2.
- **[DEPLOYMENT.md](./docs/DEPLOYMENT.md)**: Detailed step-by-step distributed setup.
- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)**: High-level design and security logic.
- **[COMPONENTS.md](./docs/COMPONENTS.md)**: File structure and component breakdown.
- **[API_AND_POLICIES.md](./docs/API_AND_POLICIES.md)**: API schemas and rule-writing guide.

---

## 📂 Repository Structure

- `/agent_glass`: Next.js dashboard and 3D simulation.
- `/brain_cloud`: Task executor loop and VLM serving scripts.
- `/firewall_governor`: Core security middleware and validation engines.
- `/mock_environment`: Hardware-free simulation and testing harness.
- `/docs`: Detailed design, API references, and deployment guides.
- `/portfolio_module`: A 100% client-side, standalone version of the dashboard and engine, designed for seamless integration into personal websites (e.g., `atulyakadur.com`). Includes built-in Wasm NLP models.

## 📄 License
This project is released under the MIT License. See [LICENSE](LICENSE) for details.
