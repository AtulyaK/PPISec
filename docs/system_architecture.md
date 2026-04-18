# System Architecture: Semantic Firewall — Software-Only Stack

## 1. Overview

The Semantic Firewall is an AASL-compliant middleware layer that prevents **Physical Prompt Injection Attacks (PPIA)** against Vision-Language-Action (VLA) robotic agents. In the software-only configuration, there is no physical hardware: the robotic arm exists as a 3D simulation in the browser, the AI Brain runs on AMD cloud GPUs, and everything communicates over HTTP and WebSocket.

The core security research is unchanged. The attack surface is identical: an adversary can inject malicious intent through environmental text (Trojan Signs), ambiguous audio, or low-confidence VLM outputs. The Firewall's job is to catch these before they produce any action — virtual or physical.

---

## 2. Agnostic Distributed Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Operator Machine (M2 MacBook, Windows PC, etc.)                        │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Agent Glass — Next.js (localhost:3000)                          │   │
│  │  - Renders 3D Sandbox                                            │   │
│  │  - Dispatches commands to Brain Node (port 8002)                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────┼────────────────────────────────┘
                                          │
                              ┌───────────┴─────────────────────────────────┐
                              │  Compute Cluster (Cloud or Local)           │
                              │                                             │
                              │  [GPU Node: Local PC, AWS, Azure, RunPod]   │
                              │  Port 8001: vLLM (Qwen2-VL-7B)              │
                              │  - The "Visual Cortex" of the agent.        │
                              │                                             │
                              │  [Logic Node: Any CPU Machine]              │
                              │  Port 8000: Firewall Governor (FastAPI)     │
                              │  Port 8002: Task Executor (Agent Loop)      │
                              │                                             │
                              │  - Configured via Environment Variables     │
                              └─────────────────────────────────────────────┘
```

---

## 3. Component Descriptions

### A. Agent Glass (Browser UI)
The entire user-facing interface. Replaces the previous Mission Control + physical arm combo.

- **3D Arm Scene (`Scene3D.tsx`):** Three.js robotic arm rendered with `@react-three/fiber`. Arm position lerp-animates smoothly to new coordinates received over WebSocket. Lights shift red/amber/green to reflect the current firewall decision. Gripper opens/closes.
- **Command Panel (`CommandPanel.tsx`):** Normal command presets, one-click Trojan Sign attack presets (auto-sets `source_modality: visual_text_injection`), free-text custom commands, and modality selector.
- **Audit Log (`AuditLog.tsx`):** Session event history showing every decision, reason, source, and latency.
- **Arm State HUD (`ArmStatePanel.tsx`):** Live X/Y/Z coordinates, gripper state, WebSocket connection status.
- **Telemetry Socket (`TelemetrySocket.tsx`):** Headless component that manages the WebSocket connection and dispatches messages into the Zustand store. Reconnects automatically.
- **Zustand Store (`store/firewall.ts`):** Single source of truth for all shared UI state.

### B. Firewall Governor (Logic Node — port 8000)
Core security middleware. Can run anywhere with Python 3.10+ (local, cloud VM, Raspberry Pi).

- **`/propose_intent` (POST):** Accepts `IntentPacket`, runs 4-stage validation, returns `VetoPacket`. On PASS, dispatches to `SimulatorClient`.
- **`/ws/telemetry` (WebSocket):** Agent Glass subscribes here. Receives push updates: `arm_state`, `decision`, `processing` messages.
- **`/hitl_override` (POST):** Endpoint for human-in-the-loop approvals of `WARN`'d actions.
- **`SimulatorClient`:** Replaces the physical hardware. Manages a `VirtualArmState`. On PASS, simulates movement delay and broadcasts state changes.

### C. Brain Cloud — TaskExecutor (Logic Node — port 8002)
The sense-plan-act agent loop. Orchestrates communication between Agent Glass, the VLM (on GPU Node), and the Firewall.

- **SENSE:** Accepts a scene description or image from the Agent Glass `/start_task` payload.
- **PLAN:** Sends context to the VLM via the vLLM API (configurable via `VLLM_URL`).
- **VALIDATE:** POSTs the `IntentPacket` to the Firewall (configurable via `FIREWALL_URL`).
- **ACT:** On PASS, waits for `SimulatorClient` to finish the virtual movement.
- **LOOP:** Continues until VLM outputs `task_complete: true` or max steps are reached.

---

## 4. Security Model: AASL Levels

| Level | Name | Description | Default Response |
|---|---|---|---|
| 1 | Routine | Low-risk, reversible movement | PASS (if all checks clear) |
| 2 | Interaction | Object interaction, medium risk | PASS (if confidence + modality OK) |
| 3 | High-Value | Irreversible action | PASS with elevated confidence threshold |
| 4 | Hijacking | Intent hijacking, critical risk | WARN always; VETO if modality untrusted |

---

## 5. Source Modality Trust Model

The central security innovation: `source_modality` is a first-class security signal.

| Modality | Trusted | MCR Behavior |
|---|---|---|
| `voice_command` | Yes | Standard confidence threshold (0.70) |
| `visual_object` | Yes | Standard confidence threshold (0.70) |
| `visual_text_injection` | **No** | Always WARN + HITL; elevated threshold (0.99) |
| `programmatic` | Yes | Standard confidence threshold |
| `unknown` | **No** | Always WARN + HITL |

A Trojan Sign injection is blocked at Stage 2 in ~1ms, before expensive LTL computation runs.

---

## 6. Data Flow per Loop Iteration

1. **User types a command** in Agent Glass → `POST /start_task {transcript, source_modality}`
2. **TaskExecutor** receives command → sends scene context to **Qwen2-VL-7B** (vLLM)
3. **VLM** outputs one atomic `IntentPacket` JSON
4. **TaskExecutor** POSTs to `Firewall /propose_intent`
5. **Firewall** broadcasts `{type: "processing"}` to Agent Glass WebSocket
6. **Firewall** runs 4-stage pipeline → `VetoPacket`
7. **Firewall** broadcasts `{type: "decision", decision, reason, latency_ms, ...}` to Agent Glass
8. **Agent Glass** → Zustand store updates → 3D scene lights shift color, audit log entry added
9. If **PASS**: `SimulatorClient` animates the virtual arm → broadcasts `{type: "arm_state"}` updates → Agent Glass 3D arm moves smoothly
10. If **WARN/VETO**: arm stays frozen, UI shows red/amber glow

---

## 7. Communication Protocols

| Link | Protocol | Address |
|---|---|---|
| Agent Glass → Firewall (commands) | HTTP REST | `<cloud-ip>:8000/start_task` |
| TaskExecutor → vLLM | HTTP REST (OpenAI-compat.) | `localhost:8001/v1` |
| TaskExecutor → Firewall | HTTP REST | `localhost:8000/propose_intent` |
| Firewall → Agent Glass (push) | WebSocket | `<cloud-ip>:8000/ws/telemetry` |
| Operator → HITL endpoint | HTTP REST | `localhost:8000/hitl_override` |
