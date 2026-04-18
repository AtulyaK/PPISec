import { create } from 'zustand';
import { Scenario, SCENARIOS } from '../data/scenarios';
import { DecisionStatus, SourceModality } from '../firewall/types';

export interface ArmState {
  base_x: number;
  base_y: number;
  base_heading: number;
  arm_extended: number;
  arm_x: number;
  arm_z: number;
  gripper_open: boolean;
  held_object: string | null;
  is_navigating: boolean;
  is_arm_moving: boolean;
  last_action: string;
  last_target: string;
  last_decision: string;
  timestamp: number;
}

export interface TelemetryEvent {
  id: string;
  timestamp: number;
  decision: DecisionStatus;
  action: string;
  target: string;
  source_modality: SourceModality;
  reason: string | null;
  latency_ms: number;
  reasoning_trace: string;
  arm_state: ArmState;
  proposed_arm_state?: ArmState;
}

interface DemoStore {
  // Scenario state
  activeScenario: Scenario;
  setScenario: (s: Scenario) => void;

  // Arm & Firewall state
  armState: ArmState;
  proposedArmState: ArmState | null;
  lastDecision: DecisionStatus;
  lastReason: string | null;
  lastLatencyMs: number;
  events: TelemetryEvent[];
  isProcessing: boolean;
  
  // Wasm / Web Worker state
  modelLoaded: boolean;
  setModelLoaded: (loaded: boolean) => void;

  // Actions
  setArmState: (s: Partial<ArmState>) => void;
  addEvent: (e: TelemetryEvent) => void;
  setDecision: (d: DecisionStatus, reason: string | null, latency: number, proposed?: ArmState) => void;
  setProcessing: (p: boolean) => void;
  clearEvents: () => void;
}

const INITIAL_ARM_STATE: ArmState = {
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
  timestamp: Date.now(),
};

export const useDemoStore = create<DemoStore>((set) => ({
  activeScenario: SCENARIOS[0],
  
  setScenario: (scenario) => {
    set({ 
      activeScenario: scenario, 
      events: [], 
      lastDecision: 'IDLE', 
      lastReason: null, 
      isProcessing: false,
      armState: { ...INITIAL_ARM_STATE, timestamp: Date.now() },
      proposedArmState: null
    });
  },

  armState: INITIAL_ARM_STATE,
  proposedArmState: null,
  lastDecision: 'IDLE',
  lastReason: null,
  lastLatencyMs: 0,
  events: [],
  isProcessing: false,
  modelLoaded: false,

  setModelLoaded: (loaded) => set({ modelLoaded: loaded }),
  setArmState: (s) => set((state) => ({ armState: { ...state.armState, ...s, timestamp: Date.now() } })),
  addEvent: (e) =>
    set((state) => ({
      events: [e, ...state.events].slice(0, 100),
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
    // Keep proposed state visible while processing
    proposedArmState: p ? state.proposedArmState : state.proposedArmState 
  })),
  clearEvents: () => set({ events: [] }),
}));
