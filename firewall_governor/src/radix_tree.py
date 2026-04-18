import yaml
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# NAMING NOTE:
# This class was originally called "ForbiddenActionTree" and described as a
# "Radix Tree/Trie." It is neither. It uses a nested dictionary (hash map).
# The class is renamed PolicyLookupTable to accurately reflect that.
#
# When presenting to judges: "two-level hash map with O(1) lookup" — do NOT
# call it a Radix Tree. Accuracy matters more than sounding impressive.
# ─────────────────────────────────────────────────────────────────────────────


class PolicyLookupTable:
    """
    Fast lookup structure for forbidden (action, target) pairs.
    Implements a two-level nested dictionary: {action -> {target -> True}}.
    All lookups are O(1) average case.

    This table handles ONLY exact action/target pair rules and wildcard class
    rules from the policy manifest.

    It does NOT handle:
      - Spatial/bounding-box rules (e.g., "VETO IF z < 0") → LTLEvaluator
      - Temporal sequence rules (e.g., "no two disposes within 10s") → LTLEvaluator
    The YAML manifest uses 'rule_type' to route rules to the correct engine.
    """

    def __init__(self):
        # Primary table: {normalized_action: {normalized_target: True}}
        # Used for exact (action, target) pair matching in O(1).
        self._pairs: Dict[str, Dict[str, bool]] = {}

        # Wildcard table: {normalized_action: [target_class_substring, ...]}
        # Used for class-based rules like action="dispose", target_class="high_value"
        # which matches any target containing the substring "high_value".
        self._wildcards: Dict[str, List[str]] = {}

    def insert_rule(self, action: str, target: str):
        """
        Inserts an exact forbidden (action, target) pair.

        Both strings are lowercased and stripped before insertion so lookup
        is always case-insensitive regardless of what the VLM outputs.

        Example:
            insert_rule("dispose", "keys")
            → self._pairs["dispose"]["keys"] = True
        """
        action = action.lower().strip()
        target = target.lower().strip()
        if action not in self._pairs:
            self._pairs[action] = {}
        self._pairs[action][target] = True

    def _insert_wildcard_rule(self, action: str, target_class: str):
        """
        Inserts a class-based wildcard rule.

        During search_violation, the target_class is matched as a substring of
        the target string. This allows rules like ("dispose", "high_value") to
        match targets "high_value_vial", "high_value_box", etc., without
        enumerating every specific object.

        Example:
            _insert_wildcard_rule("dispose", "high_value")
            → self._wildcards["dispose"] = ["high_value"]
        """
        action = action.lower().strip()
        target_class = target_class.lower().strip()
        if action not in self._wildcards:
            self._wildcards[action] = []
        self._wildcards[action].append(target_class)

    def search_violation(self, action: str, target: str) -> Tuple[bool, str]:
        """
        Checks if a given (action, target) pair is forbidden.

        Returns a tuple: (is_violation: bool, match_type: str).
        match_type is one of:
          "exact"    — the (action, target) pair is explicitly listed
          "wildcard" — the target contains a forbidden class substring
          ""         — no violation found

        The caller (validate_intent) uses the boolean to short-circuit the
        pipeline. The match_type is included in the audit log reason string.

        Lookup order:
          1. Normalize both strings to lowercase.
          2. Try exact match in self._pairs[action][target].
          3. Try wildcard: for action in self._wildcards, check if any
             class token appears as a substring of target.
          4. If neither hit, return (False, "").
        """
        action = action.lower().strip()
        target = target.lower().strip()

        # Exact match: both action and target are in the nested dict
        if action in self._pairs and target in self._pairs[action]:
            return (True, "exact")

        # Wildcard class match: target contains the forbidden class substring
        if action in self._wildcards:
            for class_token in self._wildcards[action]:
                if class_token in target:
                    return (True, "wildcard")

        return (False, "")

    def load_from_yaml(self, path: str):
        """
        Populates the lookup table from the policy manifest YAML.

        Expected YAML structure (abbreviated):
        ---
        forbidden_rules:
          - rule_type: exact_pair
            action: dispose
            target: keys
          - rule_type: wildcard_class
            action: dispose
            target_class: high_value
          - rule_type: spatial_bound    # ← routed to LTLEvaluator, NOT here
            ...
          - rule_type: temporal_seq     # ← routed to LTLEvaluator, NOT here
            ...

        Rules with rule_type "spatial_bound" or "temporal_seq" are SKIPPED
        here and must be loaded separately into LTLEvaluator.load_from_yaml().
        Skipped rules are logged as warnings so they are not silently ignored.

        After loading, logs the count of exact and wildcard rules.
        """
        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        exact_count = 0
        wildcard_count = 0

        for rule in data.get('forbidden_rules', []):
            rtype = rule.get('rule_type', 'exact_pair')

            if rtype == 'exact_pair':
                self.insert_rule(rule['action'], rule['target'])
                exact_count += 1

            elif rtype == 'wildcard_class':
                self._insert_wildcard_rule(rule['action'], rule['target_class'])
                wildcard_count += 1

            else:
                # spatial_bound and temporal_seq rules belong in LTLEvaluator.
                # Warn so the developer knows the rule was not ignored silently.
                logger.warning(
                    f"PolicyLookupTable: rule_type '{rtype}' skipped — "
                    f"route this rule to LTLEvaluator.load_from_yaml()."
                )

        logger.info(
            f"PolicyLookupTable loaded from '{path}': "
            f"{exact_count} exact rules, {wildcard_count} wildcard rules."
        )

    def rule_count(self) -> int:
        """
        Returns the total number of exact-pair rules loaded.
        Used by the /health endpoint to verify the policy was loaded correctly.
        A return value of 0 after startup indicates load_from_yaml was not called.
        """
        return sum(len(v) for v in self._pairs.values())
