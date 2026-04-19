# Quick Start Guide (< 10 Minutes)

Get the Semantic Firewall up and running quickly. This guide assumes you have a basic understanding of terminal commands and Python/Node.js.

## 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **Docker** (for VLM serving)

## 2. Infrastructure Setup (Unified CLI)

The easiest way to launch the entire system is using the **Interactive Setup Wizard**. This script will walk you through environment selection, model auto-detection, and feature toggles.

```bash
python3 start.py
```

### Wizard Features:
- **Environment:** Choose between Mock (No AI), Local (Ollama), or Cloud (vLLM).
- **Model Auto-Detect:** If using Ollama, the script lists your locally installed models for you to pick from.
- **Feature Toggles:** Enable/Disable the 3D Dashboard or Stage 3 Audio alignment on the fly.
- **Automatic Cleanup:** Pressing `Ctrl+C` once will gracefully shut down all background servers.

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
