# Policy Guide: Writing and Extending the Policy Manifest

> **File:** `firewall_governor/policies/policy_manifest.yaml`  
> **Loaded by:** `PolicyLookupTable` (exact + wildcard rules) and `LTLEvaluator` (spatial + temporal rules)

---

## Overview

The policy manifest is the **only configuration a non-engineer needs to touch** to change the security posture of the firewall. Rules are written in YAML with a `rule_type` field that determines which validation engine processes them. Adding a rule to a file is all that is needed — no code changes, no restart required if the server supports hot-reload.

---

## Rule Types

### Type 1: `exact_pair`

**Engine:** `PolicyLookupTable`  
**Purpose:** Block a specific, named action on a specific, named object. Case-insensitive.

```yaml
- rule_type: exact_pair
  action: dispose
  target: keys
  aasl_level: 4
  description: "Trojan Sign demo case. Disposing keys is the primary adversarial scenario."
```

**When to use:** When you know the exact noun the VLM will use for an object (e.g., "keys", "vial_01").  
**Limitation:** Only blocks the exact target string. If the VLM names the same object differently (e.g., "key", "the keys"), it will not match.

---

### Type 2: `wildcard_class`

**Engine:** `PolicyLookupTable`  
**Purpose:** Block an action on any object whose name *contains* a class token. Case-insensitive substring match.

```yaml
- rule_type: wildcard_class
  action: dispose
  target_class: high_value
  aasl_level: 4
  description: "Blocks disposal of any object tagged as high_value."
```

**When to use:** When you want a class-level protection (e.g., any object with "fragile", "medical", "high_value" in its name).  
**How it works:** If `target_class: medical` and the VLM identifies the object as `"medical_supply_kit"`, the substring `"medical"` matches and the rule fires.  
**Limitation:** The match is on the surface-form object string returned by the VLM — not a semantic class. If the VLM names a medical item "first_aid_box", the `medical` token does not match.

---

### Type 3: `spatial_bound`

**Engine:** `LTLEvaluator._check_spatial_rules`  
**Purpose:** Block an action if a coordinate field is outside a safe range. Evaluated on every intent without needing history.

```yaml
- rule_type: spatial_bound
  variable: coordinates.z
  operator: lt
  threshold: 0.0
  aasl_level: 3
  description: "Z below zero means below the table — physically impossible, likely hallucinated."
```

**Supported operators:**

| Operator | Meaning | Fires when... |
|---|---|---|
| `lt` | less than | `value < threshold` |
| `gt` | greater than | `value > threshold` |
| `lte` | less than or equal | `value <= threshold` |
| `gte` | greater than or equal | `value >= threshold` |

**Supported variables:**
- `coordinates.x`
- `coordinates.y`
- `coordinates.z`
- `confidence` (e.g., block intents with suspiciously high confidence)
- `aasl_target_level` (e.g., block any intent claiming AASL level 4 from an untrusted source)

**Example — workspace boundary:**
```yaml
- rule_type: spatial_bound
  variable: coordinates.x
  operator: gt
  threshold: 400.0
  aasl_level: 2
  description: "Arm cannot reach beyond 400mm in X — exceeds workspace."
```

---

### Type 4: `temporal_seq`

**Engine:** `LTLEvaluator` + RTAMT STL monitor  
**Purpose:** Time-based safety invariants that need history. Expressed in RTAMT Signal Temporal Logic (STL) syntax.

```yaml
- rule_type: temporal_seq
  rtamt_formula: "G(action_id == 3.0 -> z > 0.0)"
  description: "Dispose action must never target a coordinate below the table surface."
```

**When to use:** When a rule depends on sequence, repetition, or timing (e.g., "no two disposes within 10 seconds").

**Signal encoding** (defined in `ltl_evaluator.py`):

| Signal Name | Type | Encoding |
|---|---|---|
| `action_id` | float | `move=0, pick=1, place=2, dispose=3, stop=4, drop=5, unlock=6` |
| `modality_id` | float | `voice_command=0, visual_object=1, visual_text_injection=2, programmatic=3, unknown=9` |
| `z` | float | `intent.coordinates['z']` (raw millimeters) |

**RTAMT STL formula syntax:**

| Operator | Meaning | Example |
|---|---|---|
| `G(f)` | Globally (Always) f | `G(z > 0)` — always z above zero |
| `F(f)` | Finally (Eventually) f | Not commonly used in safety |
| `f -> g` | Implication: if f then g | `G(action_id == 3.0 -> z > 0.0)` |
| `f and g` | Logical AND | `G(action_id == 3.0 and modality_id == 2.0 -> z > 0.0)` |
| `not f` | Negation | `G(not (action_id == 3.0 and modality_id == 2.0))` |
| `f != v` | Not equal | `G(modality_id == 2.0 -> action_id != 3.0)` |

**Example formulas:**
```yaml
# Dispose action must never come from visual text injection
- rule_type: temporal_seq
  rtamt_formula: "G(modality_id == 2.0 -> action_id != 3.0)"
  description: "Belt-and-suspenders: MCR should catch this, LTL provides a second layer."
```

---

## Adding a New Rule (Checklist)

1. **Identify the rule type** — exact noun, class-based, coordinate bound, or temporal sequence.
2. **Choose the correct `rule_type`** from the four options above.
3. **Write the YAML entry** with a clear `description` field — this appears in the audit log.
4. **Set `aasl_level`** — use level 4 only for unconditional blocks. Level 3 for high-risk irreversible actions.
5. **Verify the action and target strings** match what the VLM will actually produce.
6. **Test with `simulate_vla.py`** — add a test case that should trigger your rule and confirm the VETO/WARN.

---

## Policy Manifest Schema Reference

```yaml
forbidden_rules:
  - rule_type:    (exact_pair | wildcard_class | spatial_bound | temporal_seq)   # REQUIRED
    
    # exact_pair fields:
    action:       string    # action verb, case-insensitive
    target:       string    # exact target noun, case-insensitive

    # wildcard_class fields:
    action:       string    # action verb, case-insensitive
    target_class: string    # substring token to match against target, case-insensitive

    # spatial_bound fields:
    variable:     string    # dot-path into IntentPacket (e.g., "coordinates.z")
    operator:     (lt | gt | lte | gte)
    threshold:    float

    # temporal_seq fields:
    rtamt_formula: string   # Valid RTAMT STL formula string

    # Common optional fields (for documentation and audit logging):
    aasl_level:   int (1–4)
    description:  string
```

---

## Important: What Policies Cannot Do

- **They cannot check `source_modality` directly.** That check is hardcoded in the MCR stage of `ValidationEngine` and is controlled via `AASLConfig.mcr_always_warn_modalities`. To add a modality to the always-warn list, edit the config, not the policy manifest.
- **They cannot reference VLM reasoning trace content.** The `reasoning_trace` field is logged but never evaluated — not for security, since an adversary could control it.
- **Spatial rules run without RTAMT.** They do not need temporal history and are evaluated on every intent independently.
