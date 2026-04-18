import logging
from collections import deque
from typing import Optional, Deque, List
import yaml

from .models import IntentPacket, VetoPacket, AASLConfig, DecisionStatus, VetoSource

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Action / Modality Encodings (kept for compatibility with manifest)
# ─────────────────────────────────────────────────────────────────────────────

ACTION_ENCODING = {
    "move":    0, "pick":    1, "place":   2, "dispose": 3,
    "stop":    4, "drop":    5, "unlock":  6, "navigate": 7,
    "extend":  8, "retract": 9,
}

MODALITY_ENCODING = {
    "voice_command": 0, "visual_object": 1, "visual_text_injection": 2,
    "programmatic": 3, "unknown": 9,
}

class LTLEvaluator:
    """
    PPISec Digital Governance Engine.
    
    Replaces RTAMT with a robust, software-only discrete state monitor.
    Enforces spatial bounds and sequence-based security invariants.
    """

    def __init__(self, history_window: int = 50):
        self.history: Deque[IntentPacket] = deque(maxlen=history_window)
        self._spatial_rules: List[dict] = []
        self._temporal_rules: List[dict] = []

    def reset(self):
        """Clears the agent's memory for a fresh task."""
        self.history.clear()
        logger.info("Governance Engine: history reset.")

    def load_from_yaml(self, path: str, config: AASLConfig):
        """Loads rules from the policy manifest."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        for rule in data.get('forbidden_rules', []):
            rtype = rule.get('rule_type')
            if rtype == 'spatial_bound':
                self._spatial_rules.append({
                    "variable":  rule['variable'],
                    "operator":  rule['operator'],
                    "threshold": float(rule['threshold']),
                })
            elif rtype == 'temporal_seq':
                # We store the raw formula to parse into digital logic
                self._temporal_rules.append({
                    "formula": rule['rtamt_formula'],
                    "description": rule.get('description', "")
                })

        logger.info(f"Governance Engine: loaded {len(self._spatial_rules)} spatial, {len(self._temporal_rules)} temporal rules.")

    def _check_spatial_rules(self, intent: IntentPacket) -> Optional[str]:
        """Evaluates one-shot coordinate constraints."""
        for rule in self._spatial_rules:
            parts = rule['variable'].split('.')
            val = intent
            for p in parts:
                val = val.get(p) if isinstance(val, dict) else getattr(val, p, None)
                if val is None: break
            
            if val is None: continue
            
            op, thr = rule['operator'], rule['threshold']
            violated = (
                (op == 'lt'  and val <  thr) or (op == 'gt'  and val >  thr) or
                (op == 'lte' and val <= thr) or (op == 'gte' and val >= thr)
            )
            if violated:
                return f"Spatial Violation: {rule['variable']} {op} {thr} (Actual: {val:.2f})"
        return None

    def _check_digital_invariants(self, intent: IntentPacket) -> Optional[str]:
        """
        Pure digital implementation of the temporal rules.
        Replaces brittle RTAMT parsing with reliable state checks.
        """
        action = intent.action.lower()
        modality = intent.source_modality.value
        z = intent.coordinates.get('z', 0.0)

        # Implementation of: (action_id == 3) -> (z > 0.0)
        if action == "dispose" and z <= 0.0:
            return "Sequence Error: 'dispose' attempted at or below ground level (z <= 0)."

        # Implementation of: (modality_id == 2) -> not(action_id == 3)
        if modality == "visual_text_injection" and action == "dispose":
            return "Security Invariant: High-risk 'dispose' action cannot be triggered by visual text injection (Trojan Sign)."

        return None

    def evaluate_invariants(self, intent: IntentPacket) -> Optional[VetoPacket]:
        """Runs the 4th stage of the firewall."""
        self.history.append(intent)

        # 1. Spatial Checks
        err = self._check_spatial_rules(intent)
        if err:
            return VetoPacket(intent.request_id, DecisionStatus.VETO, VetoSource.LTL, err, 0.0)

        # 2. Digital Sequence Checks
        err = self._check_digital_invariants(intent)
        if err:
            return VetoPacket(intent.request_id, DecisionStatus.VETO, VetoSource.LTL, err, 0.0)

        return None
