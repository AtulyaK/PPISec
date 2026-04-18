import { IntentPacket, VetoPacket, AASLConfig } from './types';

export class Stage2MCR {
  private config: AASLConfig;

  constructor(config: AASLConfig) {
    this.config = config;
  }

  public validate(intent: IntentPacket, hitlApproved: boolean = false): VetoPacket | null {
    // If HITL approved, skip all MCR checks
    if (hitlApproved) return null;

    const modality = intent.source_modality;

    // Check A: Always WARN modalities (e.g. Visual Text Injection)
    if (this.config.mcr_always_warn_modalities.includes(modality)) {
      return {
        request_id: intent.request_id,
        decision: 'WARN',
        reason: `Intent sourced from untrusted modality '${modality}'. Action '${intent.action}' on '${intent.target}' requires human approval.`,
        source: 'MCR',
        latency_ms: 0,
        hitl_override_token: crypto.randomUUID(),
      };
    }

    // Check B: Confidence threshold based on modality
    let threshold = this.config.mcr_base_threshold;
    if (modality === 'visual_text_injection') {
      threshold = this.config.mcr_visual_injection_threshold;
    }

    if (intent.confidence < threshold) {
      return {
        request_id: intent.request_id,
        decision: 'VETO',
        reason: `Confidence ${intent.confidence.toFixed(2)} is below the ${threshold.toFixed(2)} threshold for modality '${modality}'.`,
        source: 'MCR',
        latency_ms: 0,
        hitl_override_token: null,
      };
    }

    return null;
  }
}
