export type SourceModality =
  | 'voice_command'
  | 'visual_object'
  | 'visual_text_injection'
  | 'programmatic'
  | 'unknown';

export type DecisionStatus = 'PASS' | 'WARN' | 'VETO' | 'PENDING' | 'IDLE';

export type VetoSource =
  | 'RadixTree'
  | 'MCR'
  | 'LTL'
  | 'AudioBridge'
  | 'Exception'
  | null;

export interface IntentPacket {
  request_id: string;
  action: string;
  target: string;
  coordinates: {
    x: number;
    y: number;
    z: number;
  };
  confidence: number;
  source_modality: SourceModality;
  reasoning_trace: string;
  raw_transcript: string;
  aasl_target_level: number;
}

export interface VetoPacket {
  request_id: string;
  decision: DecisionStatus;
  reason: string | null;
  source: VetoSource;
  latency_ms: number;
  hitl_override_token: string | null;
}

export interface AASLConfig {
  mcr_base_threshold: number;
  mcr_visual_injection_threshold: number;
  mcr_always_warn_modalities: SourceModality[];
  enable_temporal_checks: boolean;
  ltl_history_window: number;
}

export const DEFAULT_CONFIG: AASLConfig = {
  mcr_base_threshold: 0.7,
  mcr_visual_injection_threshold: 0.99,
  mcr_always_warn_modalities: ['visual_text_injection', 'unknown'],
  enable_temporal_checks: true,
  ltl_history_window: 50,
};
