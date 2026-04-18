import { useCallback, useRef } from 'react';
import { useDemoStore } from '../store/useDemoStore';
import { MockVLM } from './MockVLM';
import { ValidationEngine } from '../firewall/ValidationEngine';
import { SourceModality } from '../firewall/types';

// Instantiate the engine once per session
const engine = new ValidationEngine();

export function useAgentLoop() {
  const store = useDemoStore();
  const engineRef = useRef(engine);

  /**
   * Initializes the WebAssembly NLP model for Stage 3.
   * Call this when the component mounts.
   */
  const initializeEngine = useCallback(async (onProgress?: (data: any) => void) => {
    if (store.modelLoaded) return;
    await engineRef.current.initialize(onProgress);
    store.setModelLoaded(true);
  }, [store]);

  /**
   * Executes a single Sense-Plan-Validate-Act iteration.
   */
  const executeTask = useCallback(async (transcript: string, modality: SourceModality) => {
    if (store.isProcessing) return;
    store.setProcessing(true);

    try {
      // ── 1. PLAN ──
      // In a real system, we'd send the scene image to the VLM here.
      // We use the deterministic MockVLM instead.
      // Small artificial delay to simulate network/VLM latency.
      await new Promise(r => setTimeout(r, 600)); 
      
      const intent = MockVLM.plan(transcript, modality, store.activeScenario.id);

      // ── 2. VALIDATE ──
      // Run the intent through the 4-stage TypeScript Firewall
      const vetoPacket = await engineRef.current.validateIntent(intent);

      // ── 3. ACT (or Block) ──
      // Construct a proposed arm state so the UI can show the "ghost" arm
      const proposedState = {
        ...store.armState,
        base_x: intent.action === 'navigate' ? intent.coordinates.x : store.armState.base_x,
        base_y: intent.action === 'navigate' ? intent.coordinates.y : store.armState.base_y,
        arm_z: intent.action !== 'navigate' ? intent.coordinates.z : store.armState.arm_z,
        last_action: intent.action,
        last_target: intent.target,
      };

      store.addEvent({
        id: intent.request_id,
        timestamp: Date.now(),
        decision: vetoPacket.decision,
        action: intent.action,
        target: intent.target,
        source_modality: intent.source_modality,
        reason: vetoPacket.reason,
        latency_ms: vetoPacket.latency_ms,
        reasoning_trace: intent.reasoning_trace,
        arm_state: store.armState,
        proposed_arm_state: proposedState,
      });

      store.setDecision(vetoPacket.decision, vetoPacket.reason, vetoPacket.latency_ms, proposedState);

      if (vetoPacket.decision === 'PASS') {
        // Dispatch action to 3D scene (update Zustand state to trigger lerp)
        store.setArmState({
          base_x: proposedState.base_x,
          base_y: proposedState.base_y,
          arm_z: proposedState.arm_z,
          last_action: intent.action,
          last_target: intent.target,
          last_decision: 'PASS',
        });
      }

    } catch (e) {
      console.error('[AgentLoop] Unhandled error during task execution', e);
      store.setDecision('VETO', 'Internal engine error.', 0);
    } finally {
      store.setProcessing(false);
    }
  }, [store]);

  /**
   * Resets the temporal LTL history. Call this when switching scenarios.
   */
  const resetState = useCallback(() => {
    engineRef.current.reset();
    store.clearEvents();
  }, [store]);

  return {
    initializeEngine,
    executeTask,
    resetState,
    isLoaded: store.modelLoaded,
    isProcessing: store.isProcessing,
  };
}
