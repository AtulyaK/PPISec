import logging
import time
from collections import deque
from typing import Optional, Deque, List
import yaml

from .models import IntentPacket, VetoPacket, AASLConfig, DecisionStatus, VetoSource

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# RTAMT Integration Notes:
#
# RTAMT evaluates Signal Temporal Logic (STL) formulas over NUMERICAL signals.
# It cannot process strings like action="dispose" directly.
#
# String → integer encoding maps are defined below. These MUST match the
# rtamt_formula strings in policy_manifest.yaml (e.g., "G(action_id == 3 -> z > 0)")
#
# action_id == 3 means action == "dispose" (see ACTION_ENCODING below).
# ─────────────────────────────────────────────────────────────────────────────

# Action name → integer ID used in RTAMT STL formulas.
# Add new actions here AND update policy_manifest.yaml rtamt_specs accordingly.
ACTION_ENCODING = {
    "move":    0,
    "pick":    1,
    "place":   2,
    "dispose": 3,
    "stop":    4,
    "drop":    5,
    "unlock":  6,
    "navigate": 7,
    "extend":  8,
    "retract": 9,
}

# Source modality → integer ID used in RTAMT STL formulas.
MODALITY_ENCODING = {
    "voice_command":          0,
    "visual_object":          1,
    "visual_text_injection":  2,
    "programmatic":           3,
    "unknown":                9,
}


class LTLEvaluator:
    """
    Evaluates temporal safety invariants using RTAMT (Signal Temporal Logic).
    Operates on a bounded rolling history of recent IntentPackets.

    What this evaluates that PolicyLookupTable cannot:
      - Spatial bounding-box rules: "Always z >= 0 when action == dispose"
      - Sequence rules: "No dispose within 10 steps of a previous dispose"
      - Rate limits: "No more than 3 high-risk actions in 60 seconds"

    RTAMT is optional — if unavailable (ImportError), temporal checks are
    disabled and only spatial checks run. The server still starts.
    """

    def __init__(self, history_window: int = 50):
        # Bounded rolling window — deque(maxlen=N) auto-evicts the oldest item
        # when a new one is appended beyond capacity. This bounds memory use.
        # Size the window to hold at least the longest temporal rule's lookback.
        self.history: Deque[IntentPacket] = deque(maxlen=history_window)

        # Monotonically increasing step index for RTAMT discrete-time monitor.
        self.current_step = 0

        # RTAMT StlDiscreteTimeSpecification instance.
        # None until _init_rtamt_monitor() succeeds. evaluate_invariants
        # checks for None before calling monitor.update().
        self.monitor = None

        # List of spatial bound rules parsed from YAML.
        # Each entry is a dict: {variable: str, operator: str, threshold: float}
        # These are evaluated via simple Python comparisons, not RTAMT.
        self._spatial_rules: List[dict] = []

    def reset(self):
        """
        Resets the temporal monitor state and clears history.
        Essential for clearing violations between unrelated tasks/tests.
        """
        self.history.clear()
        self.current_step = 0
        if self.monitor is not None:
            self.monitor.reset()
        logger.info("LTLEvaluator state reset.")

    def load_from_yaml(self, path: str, config: AASLConfig):
        """
        Loads spatial and temporal rules from the policy manifest YAML.

        Routing:
          - rule_type == 'spatial_bound' → appended to self._spatial_rules list
            (evaluated in _check_spatial_rules using plain Python comparisons)
          - rule_type == 'temporal_seq' → collected into an RTAMT spec string,
            then compiled by _init_rtamt_monitor()

        If config.enable_temporal_checks is False, temporal rules are parsed
        but the RTAMT monitor is not initialized (temporal checks skipped at runtime).
        """
        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        temporal_formulas = []

        for rule in data.get('forbidden_rules', []):
            rtype = rule.get('rule_type')

            if rtype == 'spatial_bound':
                # Store as dict for _check_spatial_rules() to evaluate.
                # Example: {variable: "coordinates.z", operator: "lt", threshold: 0.0}
                self._spatial_rules.append({
                    "variable":  rule['variable'],
                    "operator":  rule['operator'],
                    "threshold": float(rule['threshold']),
                })

            elif rtype == 'temporal_seq':
                # RTAMT formula string, e.g.:
                #   "G(action_id == 3 -> z > 0)"
                # Multiple formulas will be ANDed together into one spec.
                temporal_formulas.append(rule['rtamt_formula'])

        logger.info(
            f"LTLEvaluator: loaded {len(self._spatial_rules)} spatial rules, "
            f"{len(temporal_formulas)} temporal formulas from '{path}'."
        )

        if temporal_formulas and config.enable_temporal_checks:
            self._init_rtamt_monitor(temporal_formulas)

    def _init_rtamt_monitor(self, formulas: List[str]):
        """
        Initializes the RTAMT STL monitor with the given formula strings.

        RTAMT is imported here (not at module level) so that if the package
        is not installed, only temporal checking is disabled — the rest of the
        firewall still works.

        The monitor evaluates a combined spec:
            (formula_1) and (formula_2) and ...

        Signal variables declared must match those produced by
        _encode_intent_as_signals():
            action_id  : float  (integer encoded action)
            z          : float  (z-coordinate from intent.coordinates)
            modality_id: float  (integer encoded source modality)

        On parse failure (malformed formula in YAML), the monitor is set to
        None and temporal checks are disabled — logged as an error.
        """
        try:
            import rtamt
        except ImportError:
            logger.warning(
                "RTAMT not installed — temporal invariant checks disabled. "
                "Run: pip install rtamt"
            )
            return

        try:
            monitor = rtamt.StlDiscreteTimeSpecification()

            # Declare all signal variables that formulas may reference.
            # Type must be 'float' — RTAMT works with floating-point signals.
            monitor.declare_var('action_id',   'float')
            monitor.declare_var('z',           'float')
            monitor.declare_var('modality_id', 'float')

            # Combine multiple formulas with AND so all must hold.
            # Parentheses ensure operator precedence is respected.
            combined_spec = " and ".join(f"({f})" for f in formulas)
            monitor.spec = combined_spec

            # parse() compiles the spec. Raises on syntax errors.
            monitor.parse()
            self.monitor = monitor

            logger.info(f"RTAMT monitor compiled successfully. Spec: {combined_spec}")

        except Exception as e:
            logger.error(
                f"RTAMT formula parse failure: {e}. "
                f"Temporal checks disabled. Fix the rtamt_formula in policy_manifest.yaml."
            )
            self.monitor = None

    def _encode_intent_as_signals(self, intent: IntentPacket, step: int) -> dict:
        """
        Converts an IntentPacket into a dictionary of signal datasets.
        RTAMT expects: { 'var_name': [[time_index, value]] }
        """
        action_id   = ACTION_ENCODING.get(intent.action.lower(), 99)
        modality_id = MODALITY_ENCODING.get(intent.source_modality.value, 9)

        # intent.coordinates is Dict[str, float] — use .get() not attribute access.
        z = intent.coordinates.get('z', 0.0)
        if z is None:
            z = 0.0

        return {
            'action_id':   [[step, float(action_id)]],
            'z':           [[step, float(z)]],
            'modality_id': [[step, float(modality_id)]],
        }

    def _check_spatial_rules(self, intent: IntentPacket) -> Optional[str]:
        """
        Evaluates simple spatial bounding-box rules without RTAMT.

        These are one-shot comparisons on a single IntentPacket — no history
        needed. Examples:
          - "VETO if z < 0.0" (below the table surface / floor)
          - "VETO if x > 600.0" (outside the workspace boundary)

        Variable resolution:
          "coordinates.z" → intent.coordinates.z
          The variable path is split on '.' and each segment resolved via
          getattr / dict.get. This handles nested model fields.

        Operator codes:
          "lt"  → value <  threshold (less than)
          "gt"  → value >  threshold (greater than)
          "lte" → value <= threshold (less than or equal)
          "gte" → value >= threshold (greater than or equal)

        Returns:
          A human-readable violation string if any rule is violated,
          or None if all rules pass. The first violation short-circuits.
        """
        for rule in self._spatial_rules:
            # Walk the dotted path: e.g., "coordinates.z" → intent.coordinates.z
            parts = rule['variable'].split('.')
            obj = intent
            for part in parts:
                if isinstance(obj, dict):
                    obj = obj.get(part)
                else:
                    obj = getattr(obj, part, None)
                if obj is None:
                    break  # Path not resolvable — skip this rule conservatively

            value = obj
            if value is None:
                logger.warning(
                    f"LTLEvaluator: could not resolve '{rule['variable']}' "
                    f"on intent — skipping spatial rule."
                )
                continue

            op        = rule['operator']
            threshold = rule['threshold']

            violated = (
                (op == 'lt'  and value < threshold)  or
                (op == 'gt'  and value > threshold)  or
                (op == 'lte' and value <= threshold) or
                (op == 'gte' and value >= threshold)
            )

            if violated:
                return (
                    f"Spatial rule violated: {rule['variable']} {op} {threshold} "
                    f"(actual: {value:.3f})"
                )

        return None  # All rules passed

    def evaluate_invariants(self, intent: IntentPacket) -> Optional[VetoPacket]:
        """
        Runs all temporal and spatial invariant checks for the given intent.
        Returns a VetoPacket if any invariant is violated, None if all pass.

        Step 1 — Append to history:
            self.history.append(intent)
            The deque handles eviction of old entries automatically.

        Step 2 — Spatial checks (no RTAMT needed, runs always):
            Call _check_spatial_rules(intent).
            If a violation is returned, immediately return VETO VetoPacket
            with source=VetoSource.LTL and the violation message as reason.

        Step 3 — Temporal checks (RTAMT, optional):
            If self.monitor is None, skip and return None (no temporal check).
            Otherwise:
              - Encode intent as signals via _encode_intent_as_signals().
              - Call monitor.update(signals) → returns robustness degree (float).
              - Increment self.current_step for the next call.
              - If robustness < 0: the STL formula is violated → return VETO VetoPacket.

        Step 4 — Return None (all checks passed).
        """
        # Step 1: Append to rolling history
        self.history.append(intent)

        # Step 2: Spatial bounding-box checks
        spatial_violation = self._check_spatial_rules(intent)
        if spatial_violation:
            return VetoPacket(
                request_id=intent.request_id,
                decision=DecisionStatus.VETO,
                source=VetoSource.LTL,
                reason=spatial_violation,
                latency_ms=0.0
            )

        # Step 3: RTAMT temporal checks
        if self.monitor is None:
            # RTAMT unavailable or temporal checks disabled — pass this stage
            return None

        try:
            # Encode as a dataset dict with integer time steps
            dataset = self._encode_intent_as_signals(intent, self.current_step)
            # Pass the dataset as a single argument to update()
            robustness = self.monitor.update(dataset)

            # Important: Increment step counter AFTER successful update
            self.current_step += 1

            if robustness < 0:
                return VetoPacket(
                    request_id=intent.request_id,
                    decision=DecisionStatus.VETO,
                    source=VetoSource.LTL,
                    reason=(
                        f"Temporal invariant violated "
                        f"(STL robustness={robustness:.3f}). "
                        f"Action '{intent.action}' violates a sequence safety rule."
                    ),
                    latency_ms=0.0
                )
        except Exception as e:
            # Any RTAMT error fails safe: block the intent.
            logger.error(f"RTAMT monitor.update() failed: {e} — applying fail-safe VETO.")
            return VetoPacket(
                request_id=intent.request_id,
                decision=DecisionStatus.VETO,
                source=VetoSource.LTL,
                reason=f"Temporal check error (fail-safe): {e}",
                latency_ms=0.0
            )

        # Step 4: All checks passed
        return None
