# System Design: Semantic Firewall — Implementation Details

> This document describes the canonical schemas, component interfaces, and design decisions.  
> For the runnable API reference, see [`api_reference.md`](./api_reference.md).  
> For the policy rule format, see [`policy_guide.md`](./policy_guide.md).

---

## 1. Canonical Data Schema

All models are defined in `firewall_governor/src/models.py`. **This file is the single source of truth.** No other file defines these models.

### IntentPacket (Brain → Firewall)

```json
{
  "request_id":        "uuid4 string",
  "action":            "string — verb: move | pick | place | dispose | stop | drop | unlock",
  "target":            "string — VLM-identified object noun",
  "coordinates":       {"x": "float mm", "y": "float mm", "z": "float mm"},
  "confidence":        "float 0.0–1.0",
  "source_modality":   "voice_command | visual_object | visual_text_injection | programmatic | unknown",
  "reasoning_trace":   "string — VLM chain-of-thought, logged only",
  "raw_transcript":    "string — spoken command; empty if no audio",
  "aasl_target_level": "int 1–4"
}
```

**Design note:** `coordinates` is required with no default. A missing coordinate should not silently pass bounding-box checks. Any intent without coordinates must be explicitly rejected.

**Producer:** IntentPackets are produced by the `TaskExecutor` (`brain_cloud/task_executor.py`), which wraps raw VLM JSON output into the canonical schema. The VLM outputs one atomic action per loop iteration; the `TaskExecutor` adds `request_id`, `raw_transcript`, and `aasl_target_level` before POSTing to the firewall.

### VetoPacket (Firewall → Brain)

```json
{
  "request_id":          "string — echoes IntentPacket.request_id",
  "decision":            "PASS | WARN | VETO",
  "reason":              "string | null — null on PASS",
  "source":              "RadixTree | MCR | AudioBridge | LTL | Exception | null",
  "latency_ms":          "float",
  "hitl_override_token": "string | null — non-null on WARN only; single-use, expires 60s"
}
```

---

## 2. The Four-Stage Validation Pipeline

Each stage runs only if the previous stage passed. Cheap stages run first.

```
IntentPacket received
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 1: PolicyLookupTable (O(1) hash lookup)                    │
│   • Checks exact (action, target) forbidden pairs               │
│   • Checks wildcard class matches (substring in target name)    │
│   • Source: policy_manifest.yaml → rule_type: exact_pair        │
│             policy_manifest.yaml → rule_type: wildcard_class    │
│   → VETO on hit / continue on miss                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 2: MCR — Multimodal Conflict Resolver                      │
│   Check A (Modality Gate):                                       │
│     • Is source_modality in mcr_always_warn_modalities?          │
│     • VISUAL_TEXT_INJECTION and UNKNOWN → WARN + HITL token     │
│   Check B (Confidence Gate):                                     │
│     • confidence >= threshold? (0.7 base, 0.99 for visual_text) │
│     • Below threshold → VETO                                    │
│   → WARN or VETO on hit / continue on miss                      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 3: SemanticAudioBridge (only if raw_transcript is set)     │
│   • Encodes transcript + "action target" phrase as embeddings   │
│   • Computes cosine similarity (sentence-transformers)          │
│   • Below threshold (0.60) → VETO (possible VLM hallucination)  │
│   → VETO on low similarity / continue on pass                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 4: LTLEvaluator (only if enable_temporal_checks = true)   │
│   Part A (Spatial):                                             │
│     • Evaluates spatial_bound rules without RTAMT               │
│     • e.g., coordinates.z < 0 → VETO                           │
│   Part B (Temporal — RTAMT):                                    │
│     • Encodes intent as numerical signals (ACTION_ENCODING)     │
│     • Feeds to RTAMT STL monitor                                │
│     • Negative robustness → VETO                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
                    decision = PASS
```

---

## 3. Policy Manifest Structure

The manifest at `firewall_governor/policies/policy_manifest.yaml` is routed at load time:

| rule_type | Engine | Example |
|---|---|---|
| `exact_pair` | `PolicyLookupTable` | `{action: dispose, target: keys}` |
| `wildcard_class` | `PolicyLookupTable` | `{action: dispose, target_class: high_value}` |
| `spatial_bound` | `LTLEvaluator._check_spatial_rules` | `{variable: coordinates.z, operator: lt, threshold: 0.0}` |
| `temporal_seq` | RTAMT monitor in `LTLEvaluator` | `{rtamt_formula: "G(action_id == 3.0 -> z > 0.0)"}` |

For full syntax, see [`policy_guide.md`](./policy_guide.md).

---

## 4. MCR Configuration

The MCR is controlled by `AASLConfig`, not the policy manifest. To change which modalities are always escalated:

```python
AASLConfig(
    mcr_always_warn_modalities=[
        SourceModality.VISUAL_TEXT_INJECTION,
        SourceModality.UNKNOWN,
    ],
    mcr_base_threshold=0.7,            # Standard confidence floor
    mcr_visual_injection_threshold=0.99,  # Elevated floor for visual text
)
```

---

## 5. Audit Trail Design

**Format:** JSON Lines (JSONL) — one object per line, append mode.  
**File:** `audit_trail.jsonl` in the Governor's working directory.  
**Written:** Before every `return` in `validate_intent()` — not after.

**Rationale for write-before-return:** If a network error prevents the caller from receiving the response, the audit record still exists. The audit trail is the authoritative record of all decisions.

---

## 6. API Endpoints Summary

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/propose_intent` | Submit intent for validation |
| `POST` | `/hitl_override` | Operator override of a WARN'd intent |
| `GET` | `/health` | Server liveness + readiness |
| `WS` | `/ws/telemetry` | 20Hz stream of arm state + last decision |

For full schema and examples, see [`api_reference.md`](./api_reference.md).

---

## 7. Joint-Space Control Architecture

The MCU (STM32) receives **pre-solved joint angles** in degrees, not Cartesian XYZ coordinates. The IK translation chain is:

```
IntentPacket.coordinates (x, y, z mm)
        │
        ▼ Viam RDK motion planner (on Rubik Pi)
joint angles [j1, j2, j3, j4, j5, j6] in degrees
        │
        ▼ RouterBridge RPC: bridge.call("move_joints", j1..j6)
MCU: constrain to JOINT_MIN/JOINT_MAX → PWM → servos
```

**Why:** Writing IK from scratch during a hackathon is impractical for a 6-DOF arm. Viam's built-in motion planner handles this. The MCU's only job is to safely execute pre-solved angles.

---

## 8. Agent Glass: Digital Twin Specification

The Agent Glass dashboard provides real-time visualization of two arm states:

| Visual Element | Data Source | Update Rate |
|---|---|---|
| **Ghost Arm** (red, translucent) | `intended_state` from the vetoed `IntentPacket` | On each new intent |
| **Physical Arm** (green, solid) | `physical_state` from `ViamBridgeController.get_actual_state()` | 20Hz via WebSocket |
| **VETO pulse** | `last_decision == VETO or WARN` | On each decision |

On `VETO` or `WARN`: the Ghost Arm pulses red and freezes. The Physical Arm does not move.

**Tech stack:** Next.js (App Router), `@react-three/fiber`, `@react-three/drei`, Zustand, native WebSockets.

See [`agent_glass_design.md`](./agent_glass_design.md) for the full UI specification.

---

## 9. Brain's Sense-Plan-Act Loop

The Cloud Brain does **not** stream video frames continuously at 30fps. Instead, the `TaskExecutor` (`brain_cloud/task_executor.py`) runs a discrete closed loop:

```
User says: "Move the blue bottle to the right shelf"
    │
    ├── Iteration 1:  SENSE → VLM: "move above bottle" → FIREWALL: PASS → arm moves
    ├── Iteration 2:  SENSE → VLM: "pick bottle"       → FIREWALL: PASS → gripper closes
    ├── Iteration 3:  SENSE → VLM: "move to shelf"     → FIREWALL: PASS → arm moves
    ├── Iteration 4:  SENSE → VLM: "place bottle"      → FIREWALL: PASS → gripper opens
    └── Iteration 5:  SENSE → VLM: "task_complete: true" → done
```

### Loop Phases

| Phase | What Happens | Implementation |
|---|---|---|
| **SENSE** | Capture camera frame(s) + read arm telemetry (joint positions) | `_capture_frames()` + `_get_arm_state()` |
| **PLAN** | Send frame + transcript + arm state + history to VLM; VLM returns ONE atomic action JSON | `_query_vlm()` via OpenAI-compatible `/v1/chat/completions` |
| **VALIDATE** | Wrap VLM output into `IntentPacket`, POST to Firewall Governor | `_submit_to_firewall()` → `POST /propose_intent` |
| **ACT** | If PASS: wait for arm completion via telemetry polling | `_wait_for_completion()` |
| **VERIFY** | Next iteration's SENSE phase serves as verification — VLM sees what happened | Implicit in loop structure |

### Termination Conditions

| Condition | Behavior |
|---|---|
| VLM outputs `task_complete: true` | Loop ends normally |
| `max_steps` (default: 20) reached | Loop ends with warning |
| Two consecutive VETOs | Task aborted — VLM is stuck |
| WARN decision | Loop pauses, waits for HITL override |

### System Prompt Design

The VLM system prompt constrains the model to:
1. Output **exactly one atomic action** in a fixed JSON schema
2. Correctly label `source_modality` — especially `visual_text_injection` for text read from signs
3. Set `task_complete: true` only when the full task is verifiably done
4. Output `action: stop` with `confidence < 0.5` if the command is ambiguous

This structured prompting ensures the VLM's output maps cleanly to the `IntentPacket` schema and prevents multi-step outputs that would bypass per-action firewall validation.

### Security Benefit

Each atomic action is independently validated. If a Trojan Sign appears mid-task (e.g., between the pick and place steps), only that specific iteration's IntentPacket is affected. The firewall catches it at Stage 2 (MCR), and the arm freezes with the object still safely in the gripper.
