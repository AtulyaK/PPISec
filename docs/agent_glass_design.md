# Information Architecture & Design: Agent Glass Dashboard

## 1. Dashboard Overview
'Agent Glass' is an observability layer for the Semantic Firewall. It provides a real-time window into the "mind" of the agent, specifically highlighting the tension between **Proposed Intent** and **Authorized Execution**.

## 2. Information Architecture (IA)
The dashboard is divided into four primary quadrants:

### A. The Reality Engine (Center-Left)
*   **Component:** Three.js / React Three Fiber.
*   **Visuals:** 
    *   **Physical Arm:** Solid green/metallic model representing real-time hardware state.
    *   **Ghost Arm:** Translucent red/blue overlay representing the Brain's intended target.
    *   **Scene:** 3D environment with bounding boxes for "Hazard Zones" and "Safe Zones."

### B. The Reasoning Trace (Right Sidebar)
*   **Component:** Hierarchical Tree View (custom React components).
*   **Flow:** 
    *   `Node 1: Intent Perception (VLM Source)`
    *   `Node 2: Task Plan (JSON)`
    *   `Node 3: Firewall Gate (Policy Check)` -> **Status: VETO/AUTHORIZE**
    *   `Node 4: Execution Trace`

### C. Semantic Policy HUD (Bottom Center)
*   **Component:** Scrolling Ticker / Data Grid.
*   **Function:** Real-time logging of which policies are being evaluated against the current intent. Highlights active violations in bold red.

### D. Telemetry & AASL Scorecard (Top Bar)
*   **Stats:** Latency (ms), Current AASL Level (1-4), Veto Count, Heartbeat.

---

## 3. Digital Twin Sync Specification

### Data Structure
The frontend listens to a WebSocket stream from the FastAPI gateway:
```json
{
  "timestamp": "iso-string",
  "physical_state": {"joints": [0, 45, 90, 0, 0, 0], "xyz": [10, 20, 5]},
  "intended_state": {"joints": [0, 90, 90, 0, 0, 0], "xyz": [10, 30, 5]},
  "status": "VETO",
  "policy_id": "P-001"
}
```

### Sync Logic (React Three Fiber)
1.  **Interpolation:** Use `react-spring` or `lerp` to smoothly transition the Ghost Arm to new coordinates received via WS.
2.  **Veto Visualization:** If `status == "VETO"`, trigger a shader effect on the Ghost Arm (e.g., a red pulse) and lock its position until the next valid intent is received.
3.  **Performance:** Run the 3D loop at 60fps, but throttle the WebSocket state updates to 20Hz (50ms) to match the Firewall's evaluation window.

---

## 4. Tech Stack Recommendation
*   **Framework:** Next.js (App Router).
*   **3D Engine:** `@react-three/fiber` + `@react-three/drei`.
*   **State Management:** `Zustand` (for lightweight, high-frequency telemetry updates).
*   **Real-time:** `Socket.io` or native WebSockets.
*   **Styling:** Tailwind CSS + `shadcn/ui` for the data overlays.
*   **Charts:** `uPlot` for the real-time velocity/force graphs.
