# Detailed Design Flow: Semantic Firewall

This document outlines the step-by-step data flow and interaction between the four hardware nodes in the Semantic Firewall robotics project.

## 1. Hardware Nodes Overview

| Node | Hardware | Role |
| :--- | :--- | :--- |
| **Mission Control** | Lenovo Legion | Local NPU (Audio), Digital Twin UI, Telemetry Aggregator |
| **Cloud Brain** | AMD MI300X | Large Vision-Language Model (vLLM), High-level Reasoning |
| **Governor** | Qualcomm Rubik Pi | Semantic Firewall, Policy Enforcement, Intent Validation |
| **Bridge** | Arduino Uno Q | Real-time Hardware Execution, MPU-to-MCU Bridge |

## 2. Interaction Flow

The lifecycle of an agentic action follows this path:

### Step 1: Sensing & Local Processing (Mission Control)
- **Action:** User gives a voice command. The Lenovo Legion's local NPU processes audio via Whisper-Tiny.
- **Payload:** `AudioPacket`
```json
{
  "timestamp": "2024-04-20T10:00:00Z",
  "transcript": "Pick up the bottle and throw it in the trash.",
  "audio_features": [0.12, -0.45, ...],
  "device_id": "legion-01"
}
```

### Step 2: High-Level Reasoning (Cloud Brain)
- **Action:** Mission Control sends the transcript + current camera frame to the AMD MI300X Cloud Brain. The vLLM generates a plan.
- **Payload:** `VLA_Request` -> `IntentPacket`
```json
{
  "intent_id": "uuid-v4-12345",
  "action": "dispose",
  "target_object": "plastic_bottle",
  "target_class": "trash",
  "coordinates": {"x": 0.5, "y": 0.2, "z": 0.1},
  "reasoning_trace": "The user requested to discard the bottle. It is identified as waste.",
  "source_modality": "voice_and_vision",
  "aasl_target_level": 3
}
```

### Step 3: Semantic Validation (Governor)
- **Action:** The Cloud Brain's `IntentPacket` is intercepted by the Qualcomm Rubik Pi Governor. It runs the **Radix Tree** (forbidden object/action pairs) and **LTL Evaluator** (safety invariants).
- **Payload:** `VetoPacket` (Internal & to Mission Control)
```json
{
  "intent_id": "uuid-v4-12345",
  "status": "PASS",
  "active_policies": ["P-001", "P-002"],
  "mcr_score": 0.98,
  "execution_token": "jwt-token-secure"
}
```

### Step 4: Hardware Bridge Execution (Bridge)
- **Action:** If `PASS`, the Governor sends the command to the Arduino Uno Q. The Dragonwing MPU calls the STM32 MCU via the Bridge API.
- **Payload:** `BridgeCommand`
```json
{
  "method": "move_to_coords",
  "params": [0.5, 0.2, 0.1],
  "token": "jwt-token-secure"
}
```

### Step 5: Digital Twin Synchronization (Mission Control)
- **Action:** Both the Governor (Intent) and the Bridge (Actual State) stream telemetry back to the Lenovo Legion.
- **Payload:** `TelemetryStream`
```json
{
  "ghost_state": {"x": 0.5, "y": 0.2, "z": 0.1},
  "actual_state": {"x": 0.49, "y": 0.21, "z": 0.1},
  "firewall_logs": ["Policy P-002 satisfied: Target is trash."]
}
```

## 3. Communication Protocols
- **Mission Control <-> Cloud Brain:** HTTPS / gRPC (vLLM API).
- **Cloud Brain <-> Governor:** WebHooks / REST API.
- **Governor <-> Bridge:** Serial over USB / Viam RDK.
- **Governor/Bridge <-> Mission Control:** WebSockets (Socket.io) for real-time telemetry.
