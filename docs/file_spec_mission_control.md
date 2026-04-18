# File Specification: Mission Control (Lenovo Legion)

This document specifies the files for the `agent_glass/` directory (Mission Control) and local scripts running on the Lenovo Legion. This node handles UI, observability (Digital Twin), and local sensory processing.

## Directory: `agent_glass/`

### 1. `agent_glass/src/app/page.tsx`
- **Purpose:** The Next.js App Router entry point. Composes the overall dashboard layout.
- **Component Signatures:**
  ```typescript
  export default function Dashboard() {
    /**
     * Renders the main Grid containing:
     * 1. The 3D Digital Twin Canvas
     * 2. The Semantic Firewall Log Panel
     * 3. The Audio/Visual Input Feed
     */
  }
  ```
- **System Interaction:** Acts as the presentation layer, connecting React components to the Zustand store.

### 2. `agent_glass/src/components/DigitalTwinCanvas.tsx`
- **Purpose:** A React Three Fiber (R3F) component that visualizes the "Ghost" (Intended) state vs. the "Physical" (Actual) state of the robotic arm.
- **Component Signatures:**
  ```typescript
  import { Canvas } from '@react-three/fiber'
  
  export function DigitalTwinCanvas() {
    /**
     * Uses useTelemetryStore to fetch real-time X,Y,Z coordinates.
     * Renders two RobotArm models:
     * - A red, semi-transparent model representing the Brain's Intent.
     * - A green, solid model representing the physical Bridge state.
     */
  }
  ```
- **System Interaction:** Reacts to WebSocket data streamed from the Governor and Bridge.

### 3. `agent_glass/src/store/telemetryStore.ts`
- **Purpose:** Zustand store for managing real-time WebSocket connections and application state.
- **Function Signatures:**
  ```typescript
  import { create } from 'zustand'
  
  interface TelemetryState {
    ghostArm: { x: number, y: number, z: number };
    physicalArm: { x: number, y: number, z: number };
    vetoLogs: string[];
    connectWebSocket: (url: string) => void;
  }
  
  export const useTelemetryStore = create<TelemetryState>((set) => ({
    // ... implementation
  }))
  ```
- **System Interaction:** Maintains the connection to the FastAPI endpoint on the Governor (`/telemetry/ws`).

### 4. `agent_glass/scripts/npu_audio_processor.py`
- **Purpose:** A background script running on the Lenovo Legion that leverages the local NPU to process audio commands via Whisper-Tiny, providing low-latency transcription before it goes to the Cloud Brain.
- **Class/Function Signatures:**
  ```python
  import sounddevice as sd
  # import whisper optimization library for NPU
  
  def capture_and_transcribe() -> str:
      """
      Continuously listens to the microphone. Upon detecting a wake word or 
      command phrase, uses the NPU to run inference with Whisper-Tiny.
      Returns the transcript string.
      """
      pass
      
  def dispatch_to_brain(transcript: str, current_frame_path: str):
      """
      Packages the transcript and current camera frame, sending it to the 
      AMD MI300X Cloud Brain API.
      """
      pass
  ```
- **System Interaction:** The origin point of the data flow. Feeds the AMD Cloud Brain with the user's intent.
