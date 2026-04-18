import { create } from 'zustand'

export type DecisionStatus = 'PASS' | 'WARN' | 'VETO' | 'PENDING' | 'IDLE'
export type SourceModality =
  | 'voice_command'
  | 'visual_object'
  | 'visual_text_injection'
  | 'programmatic'
  | 'unknown'

export interface ArmState {
  x: number
  y: number
  z: number
  gripper_open: boolean
  is_moving: boolean
  last_action: string
  last_target: string
  timestamp: number
}

export interface TelemetryEvent {
  id: string
  timestamp: number
  decision: DecisionStatus
  action: string
  target: string
  source_modality: SourceModality
  reason: string | null
  latency_ms: number
  reasoning_trace: string
  arm_state: ArmState
}

interface FirewallStore {
  // Current arm state (drives the 3D scene)
  armState: ArmState
  // Latest firewall decision for the current intent
  lastDecision: DecisionStatus
  lastReason: string | null
  lastLatencyMs: number
  // Full audit log for the session
  events: TelemetryEvent[]
  // Whether the system is processing a command right now
  isProcessing: boolean
  // WebSocket connection status
  wsConnected: boolean

  // Actions
  setArmState: (s: ArmState) => void
  addEvent: (e: TelemetryEvent) => void
  setDecision: (d: DecisionStatus, reason: string | null, latency: number) => void
  setProcessing: (p: boolean) => void
  setWsConnected: (c: boolean) => void
  clearEvents: () => void
}

export const useFirewallStore = create<FirewallStore>((set) => ({
  armState: {
    x: 0,
    y: 200,
    z: 100,
    gripper_open: true,
    is_moving: false,
    last_action: 'none',
    last_target: 'none',
    timestamp: Date.now() / 1000,
  },
  lastDecision: 'IDLE',
  lastReason: null,
  lastLatencyMs: 0,
  events: [],
  isProcessing: false,
  wsConnected: false,

  setArmState: (s) => set({ armState: s }),
  addEvent: (e) =>
    set((state) => ({
      events: [e, ...state.events].slice(0, 100), // keep last 100
    })),
  setDecision: (d, reason, latency) =>
    set({ lastDecision: d, lastReason: reason, lastLatencyMs: latency }),
  setProcessing: (p) => set({ isProcessing: p }),
  setWsConnected: (c) => set({ wsConnected: c }),
  clearEvents: () => set({ events: [] }),
}))
