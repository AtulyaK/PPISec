# API Reference & Policy Guide

This document describes how to interact with the Semantic Firewall and how to define security policies.

---

## 1. IntentPacket Schema
Every action proposed by the VLM must be wrapped in an `IntentPacket`.

| Field | Type | Description |
|---|---|---|
| `request_id` | UUID | Unique identifier for the action. |
| `action` | String | e.g., `pick`, `place`, `dispose`, `navigate`. |
| `target` | String | The object or location targeted by the action. |
| `coordinates` | Object | `{"x": float, "y": float, "z": float}` (in meters). |
| `source_modality` | Enum | `voice_command`, `visual_text_injection`, `visual_object`, `programmatic`, `unknown`. |
| `confidence` | Float | 0.0 - 1.0 score from the VLM. |
| `reasoning_trace` | String | VLM's internal explanation for the action. |
| `raw_transcript` | String | The original user spoken command (if any). |

---

## 2. VetoPacket Schema
The response from the Firewall to the Brain.

| Field | Type | Description |
|---|---|---|
| `request_id` | UUID | Matches the original IntentPacket. |
| `decision` | Enum | `PASS`, `WARN`, `VETO`. |
| `reason` | String | Human-readable explanation for the decision. |
| `source` | Enum | The stage that blocked the action (e.g., `MCR`, `LTL`). |
| `hitl_override_token` | String | Optional. Used to approve a `WARN`'d action. |

---

## 3. Writing Security Policies
Policies are defined in `firewall_governor/policies/policy_manifest.yaml`.

### 3.1 Exact Pair Rules
Forbidden (Action, Target) combinations.
```yaml
- rule_type: exact_pair
  action: dispose
  target: medical_supplies
  aasl_level: 4
```

### 3.2 Wildcard Class Rules
Matches any target containing a specific string.
```yaml
- rule_type: wildcard_class
  action: dispose
  target_class: recalled
  aasl_level: 4
```

### 3.3 Spatial Bound Rules
Enforces physical boundaries.
```yaml
- rule_type: spatial_bound
  variable: coordinates.z
  operator: lt
  threshold: 0.0
```

### 3.4 Temporal Sequence Rules (RTAMT)
Uses STL (Signal Temporal Logic) for history-based invariants.
```yaml
- rule_type: temporal_seq
  rtamt_formula: "G(modality_id == 2.0 -> action_id != 3.0)"
  description: "Visual text injection (id 2) cannot trigger dispose (id 3)."
```
