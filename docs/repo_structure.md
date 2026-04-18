# Repository Structure & Architecture Plan: Semantic Firewall

This document outlines the full repository structure and technical integration details for the Semantic Firewall, designed to run across an AMD MI300X Cloud, a Qualcomm Rubik Pi 3 (Governor), and an Arduino Uno Q (Muscle Bridge).

## 1. Directory Structure

```text
/
├── brain_cloud/                 # Code for AMD MI300X vLLM deployment
│   ├── Dockerfile               # Uses rocm/vllm:rocm6.3.1_mi300_ubuntu22.04 base
│   ├── deployment.yaml          # K8s or Docker Compose specs
│   └── startup.sh               # vLLM server launch script
├── firewall_governor/           # Semantic Firewall for Qualcomm Rubik Pi 3
│   ├── src/
│   │   ├── main.py              # FastAPI entrypoint for the firewall
│   │   ├── policy_manifest.yaml # AASL safety rules
│   │   ├── validation_engine.py # Radix tree logic & Intent validation
│   │   ├── audio_monitor.py     # Whisper-Tiny integration for spectral gating
│   │   └── viam_client.py       # Intercepts and sends commands via Viam
│   ├── tests/
│   ├── requirements.txt
│   └── viam.json                # Viam hardware config for the arm/gripper
├── hardware_bridge/             # Arduino Uno Q logic (Dragonwing MPU <-> STM32 MCU)
│   ├── python/
│   │   └── main.py              # Dragonwing client using arduino.app_utils
│   └── sketch/
│   │   └── sketch.ino           # STM32 C++ code exposing Bridge.provide()
├── mock_environment/            # Local simulation (Phase 1)
│   ├── mock_so101.py            # Simulates Viam API for the SO-101 arm
│   └── simulate_vla.py          # Simulates VLA intent packets
├── agent_glass/                 # Observability Dashboard (Three.js/Next.js)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Scene3D.tsx      # React Three Fiber canvas
│   │   │   └── ReasoningLog.tsx # Renders trace and veto points
│   │   ├── pages/
│   │   └── store/
│   │       └── telemetry.ts     # Zustand store for WebSocket data
│   ├── package.json
│   └── tailwind.config.js
├── docs/                        # Documentation
│   ├── system_architecture.md
│   ├── system_design.md
│   ├── implementation_report.md
│   ├── technical_analysis_ppia.md
│   ├── formal_verification_research.md
│   ├── agent_glass_design.md
│   └── repo_structure.md        # (This file)
└── README.md
```

## 2. Interface Contract (JSON Schema)

### Intent Packet (From Brain to Governor)
```json
{
  "action": "string",
  "target": "string",
  "reasoning": "string",
  "confidence": "float",
  "source": "audio" | "visual"
}
```

### Veto Packet (Governor Output)
```json
{
  "status": "BLOCK" | "PASS",
  "reason": "string",
  "safety_level": "integer"
}
```

## 3. Hardware Integration Details

### A. Viam Hardware Config (Rubik Pi)
The `viam.json` on the Qualcomm Rubik Pi must define the arm and gripper, pointing to the serial port connected to the Uno Q or the servos directly:
```json
{
  "components": [
    {
      "name": "so101-arm",
      "model": "devrel:so101:arm",
      "type": "arm",
      "attributes": {
        "port": "/dev/ttyUSB0",
        "baud_rate": 1000000
      }
    }
  ]
}
```

### B. Uno Q Bridge API (MPU to MCU)
The Dragonwing MPU (Linux) communicates with the STM32 MCU via the Bridge API.

**Dragonwing MPU (`hardware_bridge/python/main.py`):**
```python
from arduino.app_utils import bridge, App
import time

def loop():
    # Send validated command to STM32
    bridge.call("move_joint", 1, 90.0)

app = App(loop=loop)
if __name__ == "__main__":
    app.run()
```

**STM32 MCU (`hardware_bridge/sketch/sketch.ino`):**
```cpp
#include "Arduino_RouterBridge.h"

void setup() {
  Bridge.begin();
  Bridge.provide("move_joint", move_joint_handler);
}

void loop() {}

void move_joint_handler(int joint_id, float angle) {
  // PWM/Servo logic here
}
```

### C. vLLM on AMD MI300X
To serve the VLM (e.g., Llama-3-Vision) efficiently on the AMD MI300X Developer Cloud, use the optimized ROCm Docker image:
```bash
docker run -it --rm \
    --network=host \
    --device=/dev/kfd --device=/dev/dri \
    --group-add video \
    --shm-size 16G \
    rocm/vllm:latest \
    vllm serve Qwen/Qwen2-VL-7B-Instruct --trust-remote-code
```
This exposes an OpenAI-compatible endpoint at `http://localhost:8000/v1` for the Rubik Pi to query.
