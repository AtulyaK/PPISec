import { IntentPacket, VetoPacket, AASLConfig, DEFAULT_CONFIG } from './types';
import { Stage1Policy } from './Stage1Policy';
import { Stage2MCR } from './Stage2MCR';
import { Stage3Audio } from './Stage3Audio';
import { Stage4LTL } from './Stage4LTL';

export class ValidationEngine {
  public stage1 = new Stage1Policy();
  public stage2 = new Stage2MCR(DEFAULT_CONFIG);
  public stage3 = new Stage3Audio();
  public stage4 = new Stage4LTL();

  public async initialize(onNLPProgress?: (data: any) => void) {
    // Stage 3 requires downloading the Wasm model
    await this.stage3.initialize(onNLPProgress);
  }

  public reset() {
    this.stage4.reset();
  }

  public async validateIntent(intent: IntentPacket, hitlApproved: boolean = false): Promise<VetoPacket> {
    const start = performance.now();

    // Helper to format the final VetoPacket
    const finalize = (veto: VetoPacket | null) => {
      const latency = performance.now() - start;
      if (veto) {
        veto.latency_ms = latency;
        return veto;
      }
      return {
        request_id: intent.request_id,
        decision: 'PASS' as const,
        reason: 'All validation stages passed.',
        source: null,
        latency_ms: latency,
        hitl_override_token: null,
      };
    };

    // ── Stage 1: Policy Manifest ──
    const s1 = this.stage1.validate(intent);
    if (s1) return finalize(s1);

    // ── Stage 2: MCR ──
    const s2 = this.stage2.validate(intent, hitlApproved);
    if (s2) return finalize(s2);

    // ── Stage 3: Audio Semantic Alignment ──
    // Await required because of the WebAssembly execution
    const s3 = await this.stage3.validate(intent);
    if (s3) return finalize(s3);

    // ── Stage 4: LTL & Spatial Bounds ──
    const s4 = this.stage4.validate(intent);
    if (s4) return finalize(s4);

    // ── PASS ──
    return finalize(null);
  }
}
