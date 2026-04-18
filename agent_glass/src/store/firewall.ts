import { create } from 'zustand'
import { Scenario, SCENARIOS } from '../data/scenarios'

const API_URL = process.env.NEXT_PUBLIC_BRAIN_URL ?? 'http://localhost:8002'
const FIREWALL_URL = process.env.NEXT_PUBLIC_FIREWALL_URL ?? 'http://localhost:8000'

export type DecisionStatus = 'PASS' | 'WARN' | 'VETO' | 'PENDING' | 'IDLE'
export type SourceModality =
  | 'voice_command'
  | 'visual_object'
  | 'visual_text_injection'
  | 'programmatic'
  | 'unknown'

export interface ArmState {
  // Mobile Base
  base_x: number
  base_y: number
  base_heading: number
  // Arm manipulation
  arm_extended: number
  arm_x: number
  arm_z: number
  // Gripper & Status
  gripper_open: boolean
  held_object: string | null
  is_navigating: boolean
  is_arm_moving: boolean
  // Context
  last_action: string
  last_target: string
  last_decision: string
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
  proposed_arm_state?: ArmState
}

interface FirewallStore {
  // Scenario state
  activeScenario: Scenario
  setScenario: (s: Scenario) => Promise<void>

  // Current robot state (drives the 3D scene)
  armState: ArmState
  // Ghost arm state (proposed by brain, potentially vetoed)
  proposedArmState: ArmState | null
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
  setDecision: (d: DecisionStatus, reason: string | null, latency: number, proposed?: ArmState) => void
  setProcessing: (p: boolean) => void
  setWsConnected: (c: boolean) => void
  clearEvents: () => void
}

export const useFirewallStore = create<FirewallStore>((set, get) => ({
  activeScenario: SCENARIOS[0],
  
  setScenario: async (scenario) => {
    set({ activeScenario: scenario, isProcessing: true })
    try {
      await fetch(`${FIREWALL_URL}/set_scenario`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          scenario_id: scenario.id,
          objects: scenario.objects 
        }),
      })
      // Clear events on scenario change for purity
      set({ events: [], lastDecision: 'IDLE', lastReason: null, isProcessing: false })
    } catch (e) {
      console.error('[FirewallStore] Failed to set scenario', e)
      set({ isProcessing: false })
    }
  },

  armState: {
    base_x: 0,
    base_y: 0,
    base_heading: 0,
    arm_extended: 0,
    arm_x: 0,
    arm_z: 1.2,
    gripper_open: true,
    held_object: null,
    is_navigating: false,
    is_arm_moving: false,
    last_action: 'none',
    last_target: 'none',
    last_decision: 'none',
    timestamp: Date.now() / 1000,
  },
  proposedArmState: null,
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
  setDecision: (d, reason, latency, proposed) =>
    set({ 
      lastDecision: d, 
      lastReason: reason, 
      lastLatencyMs: latency,
      proposedArmState: proposed || null
    }),
  setProcessing: (p) => set((state) => ({ 
    isProcessing: p,
    proposedArmState: p ? state.proposedArmState : state.proposedArmState // keep it until next decision
  })),
  setWsConnected: (c) => set({ wsConnected: c }),
  clearEvents: () => set({ events: [] }),
}))
