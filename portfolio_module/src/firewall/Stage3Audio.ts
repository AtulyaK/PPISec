import { IntentPacket, VetoPacket } from './types';
import { pipeline, env } from '@xenova/transformers';

// Tell transformers.js not to look for local file system models
env.allowLocalModels = false;

export class Stage3Audio {
  private threshold = 0.5;
  private embedder: any = null;
  private isLoaded = false;

  public async initialize(onProgress?: (data: any) => void) {
    if (this.isLoaded) return;
    
    try {
      this.embedder = await pipeline(
        'feature-extraction',
        'Xenova/all-MiniLM-L6-v2',
        { progress_callback: onProgress }
      );
      this.isLoaded = true;
    } catch (e) {
      console.error('[Stage3Audio] Failed to load Wasm NLP model:', e);
    }
  }

  private cosineSimilarity(a: number[], b: number[]): number {
    let dot = 0, normA = 0, normB = 0;
    for (let i = 0; i < a.length; i++) {
      dot += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }
    if (normA === 0 || normB === 0) return 0;
    return dot / (Math.sqrt(normA) * Math.sqrt(normB));
  }

  public async validate(intent: IntentPacket): Promise<VetoPacket | null> {
    if (!this.isLoaded || !this.embedder) {
      console.warn('[Stage3Audio] NLP model not loaded. Bypassing Stage 3.');
      return null;
    }

    const transcript = intent.raw_transcript.trim();
    if (!transcript) return null; // No audio to check

    try {
      // Create a semantic description of the proposed action
      const intentDesc = `Command the robot to ${intent.action} the ${intent.target}.`;

      const tOutput = await this.embedder(transcript, { pooling: 'mean', normalize: true });
      const iOutput = await this.embedder(intentDesc, { pooling: 'mean', normalize: true });

      const tVector = Array.from(tOutput.data) as number[];
      const iVector = Array.from(iOutput.data) as number[];

      const score = this.cosineSimilarity(tVector, iVector);

      if (score < this.threshold) {
        return {
          request_id: intent.request_id,
          decision: 'VETO',
          reason: `Semantic alignment failed. Transcript and Intent are too dissimilar (score: ${score.toFixed(2)}). Possible VLM hallucination.`,
          source: 'AudioBridge',
          latency_ms: 0,
          hitl_override_token: null,
        };
      }

      return null;
    } catch (e) {
      console.error('[Stage3Audio] Validation error:', e);
      return null; // Fail open if NLP errors out during inference
    }
  }
}
