import { IntentPacket, VetoPacket } from './types';
import { POLICY_MANIFEST, SpatialBoundRule } from '../data/policy';

export class Stage4LTL {
  private history: IntentPacket[] = [];
  private spatialRules: SpatialBoundRule[] = [];

  constructor() {
    this.spatialRules = POLICY_MANIFEST.filter((r): r is SpatialBoundRule => r.rule_type === 'spatial_bound');
  }

  public reset() {
    this.history = [];
  }

  private checkSpatialRules(intent: IntentPacket): string | null {
    for (const rule of this.spatialRules) {
      // Very basic dot-notation resolver
      const parts = rule.variable.split('.');
      let val: any = intent;
      for (const p of parts) {
        val = val[p];
        if (val === undefined) break;
      }

      if (typeof val !== 'number') continue;

      const thr = rule.threshold;
      const op = rule.operator;
      const violated =
        (op === 'lt' && val < thr) ||
        (op === 'gt' && val > thr) ||
        (op === 'lte' && val <= thr) ||
        (op === 'gte' && val >= thr);

      if (violated) {
        return `Spatial Violation: ${rule.variable} ${op} ${thr} (Actual: ${val.toFixed(2)})`;
      }
    }
    return null;
  }

  private checkDigitalInvariants(intent: IntentPacket): string | null {
    const action = intent.action.toLowerCase();
    const modality = intent.source_modality;
    const z = intent.coordinates.z || 0;

    // Implementation of: (action_id == 3) -> (z > 0.0)
    if (action === 'dispose' && z <= 0.0) {
      return "Sequence Error: 'dispose' attempted at or below ground level (z <= 0).";
    }

    // Implementation of: (modality_id == 2) -> not(action_id == 3)
    if (modality === 'visual_text_injection' && action === 'dispose') {
      return "Security Invariant: High-risk 'dispose' action cannot be triggered by visual text injection (Trojan Sign).";
    }

    return null;
  }

  public validate(intent: IntentPacket): VetoPacket | null {
    this.history.push(intent);

    const spatialErr = this.checkSpatialRules(intent);
    if (spatialErr) {
      return {
        request_id: intent.request_id,
        decision: 'VETO',
        reason: spatialErr,
        source: 'LTL',
        latency_ms: 0,
        hitl_override_token: null,
      };
    }

    const digitalErr = this.checkDigitalInvariants(intent);
    if (digitalErr) {
      return {
        request_id: intent.request_id,
        decision: 'VETO',
        reason: digitalErr,
        source: 'LTL',
        latency_ms: 0,
        hitl_override_token: null,
      };
    }

    return null;
  }
}
