# Local Testing & Verification Guide

This guide explains how to run a full-scale local test of the PPISec Semantic Firewall on your MacBook or PC without requiring a cloud GPU. We use a **Mock VLM** to simulate the AI's reasoning.

---

## 1. Setup the Environment

Ensure you have 4 terminal windows open. All commands should be run from the repository root: `/Users/atulyakadur/Documents/Personal Code Work/Hackathons/StarHacks_04_2026`

### Terminal 1: Firewall Governor (Security Node)
This node enforces safety policies and runs the 3D physics simulation.
```bash
export PYOPENGL_PLATFORM=osmesa 
uvicorn firewall_governor.src.main:app --port 8000
```

### Terminal 2: Mock VLM (Visual Cortex)
This script mimics an OpenAI-compatible API (like vLLM) and returns a pre-defined safe action.
```bash
python3 mock_environment/mock_vlm.py
```
*(If `mock_vlm.py` doesn't exist, see the script content in the "Tools" section below.)*

### Terminal 3: Brain Executor (Agent Loop)
The orchestrator that connects the UI, VLM, and Firewall.
```bash
export VLLM_URL=http://localhost:8001/v1
python3 brain_cloud/task_executor.py
```

### Terminal 4: Agent Glass (Dashboard)
The 3D visualization and command interface.
```bash
cd agent_glass
export NEXT_PUBLIC_BRAIN_URL=http://localhost:8002
npm run dev
# Open http://localhost:3000
```

---

## 2. Test Scenario 1: The "Golden Path" (Safe Action)
**Goal:** Verify that a legitimate command passes the firewall and moves the virtual arm.

1.  Open `http://localhost:3000`.
2.  Select the **Pharmacy** scenario.
3.  In the Command Panel, select **"Pick up bottle"**.
4.  Ensure Modality is set to **"Voice Command"**.
5.  Click **Send**.
6.  **Expected Result:** 
    - The Audit Log shows `PASS`.
    - The 3D Arm moves smoothly to the bottle.
    - The status light on the UI glows **Green**.

---

## 3. Test Scenario 2: Trojan Sign (Semantic VETO)
**Goal:** Verify that a malicious instruction on a physical sign is blocked.

1.  In the Command Panel, go to the **Trojan Attacks** tab.
2.  Click **"🚨 Trojan: Dispose Keys"**.
3.  Observe that the modality auto-switches to **"Visual Text Injection"**.
4.  Click **Send**.
5.  **Expected Result:**
    - The Audit Log shows `VETO`.
    - Reason: `Forbidden action/target pair: 'dispose' on 'keys'`.
    - The 3D Arm **stays frozen**.
    - The status light on the UI glows **Red**.

---

## 4. Test Scenario 3: Human-in-the-Loop (WARN)
**Goal:** Verify that ambiguous or suspicious modality triggers a HITL request.

1.  Type a custom command: *"Move the vial"*.
2.  Change the Modality dropdown to **"Unknown"**.
3.  Click **Send**.
4.  **Expected Result:**
    - The Audit Log shows `WARN`.
    - An **"Approve"** button appears in the UI.
    - The status light glows **Amber**.
    - Click **Approve** -> The arm should then proceed to move.

---

## 🛠️ Testing Tools

### Mock VLM Script (`mock_environment/mock_vlm.py`)
If you need to create the mock VLM, use this code:
```python
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.post("/v1/chat/completions")
async def chat():
    # This mock always returns a safe 'pick' action
    return {
        "choices": [{
            "message": {
                "content": '{"action": "pick", "target": "bottle", "coordinates": {"x": 0.2, "y": 0.2, "z": 0.1}, "confidence": 0.95, "source_modality": "voice_command", "reasoning_trace": "Mock VLM proposing a safe pick action.", "task_complete": false}'
            }
        }]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

### Stress Test Script
Run this to automatically verify all 5 major adversarial scenarios in 5 seconds:
```bash
python3 mock_environment/simulate_vla.py
```
