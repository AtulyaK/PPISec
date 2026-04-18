# Code Evaluation: Semantic Firewall Project
**Date:** 2026-04-16 | **Scope:** All committed source files across all modules

---

## Verdict Summary

> **The project does not function. At all.**
> 
> Every single security check — the Radix Tree lookup, the MCR confidence gate, the LTL evaluator — is commented out and replaced with a hardcoded safe return value (`return False`, `return True`, `return 1.0`). If you submitted this right now, the firewall would **approve 100% of intents, including the "Trojan Sign"** it was specifically designed to block. The demo would prove the opposite of the project's thesis.

This is not a tough draft. It is a skeleton with well-written comments on bones that don't exist yet.

---

## File-by-File Breakdown

### 1. `firewall_governor/src/main.py` — **Critical**

**The API endpoint is a no-op.**

```python
@app.post("/propose_intent", response_model=VetoPacket)
async def evaluate_intent(intent: IntentPacket):
    # TODO: Integrate ValidationEngine
    return VetoPacket(
        intent_id=intent.intent_id,
        status="PASS",
        safety_level=intent.aasl_target_level
    )
```

- `ValidationEngine` is never instantiated anywhere. No policy file is loaded. No radix tree is built. The endpoint takes your intent and immediately returns PASS.
- The `IntentPacket` defined *here* (`intent_id`, `target_object`, `reasoning_trace`, `source_modality`, `aasl_target_level`) is **a completely different schema** from the one in `models.py` (`request_id`, `target`, `raw_transcript` — no `source_modality`, no `aasl_target_level`). These two definitions are **actively incompatible**. The engine cannot use the API's data.
- `VetoPacket` here has fields `status` and `active_policies`. In `models.py` it has `decision`, `source`, `latency_ms`. Same class, two different schemas. If you ever wire them together it will explode with a Pydantic validation error.

---

### 2. `firewall_governor/src/validation_engine.py` — **Critical**

**The entire logic pipeline is a comment block.**

Every step — Radix Tree, MCR, LTL — is written as `# implementation_step:` comments inside the function body. The actual code that runs is:

```python
return VetoPacket(request_id=intent.request_id, decision="PASS", latency_ms=latency)
```

- `evaluate_mcr_score()` always returns `True`.
- `check_policy_manifest()` always returns `False` (no violation found, ever).
- The ValidationEngine is never constructed in `main.py`, so even if you uncommented the steps, nothing would call this class.

---

### 3. `firewall_governor/src/radix_tree.py` — **Critical**

**This is the project's most important component and it does literally nothing.**

- `insert_rule()` calls `pass`. No rules are ever stored.
- `search_violation()` always returns `False`. Every action/target pair is safe, unconditionally.
- `load_from_yaml()` calls `pass`. No policy file is ever read.

There is also **no YAML policy manifest file anywhere in the project.** Not in `docs/`, not in `firewall_governor/`, not anywhere. The code that would load it doesn't work, but even if it did, there is nothing to load.

---

### 4. `firewall_governor/src/ltl_evaluator.py` — **High**

**RTAMT integration is entirely aspirational.**

- `evaluate_invariants()` always returns `True`.
- `load_rtamt_specs()` calls `pass`. The `self.monitor` is never initialized so even if `evaluate_invariants` tried to call `self.monitor.update()`, it would throw `AttributeError: 'NoneType' object has no attribute 'update'`.
- There is no specs file for RTAMT to load. No `.stl` or YAML-formatted temporal spec exists in the project.
- The example invariant in the docstring (`"Always(Not(Action == 'dispose' AND Target == 'medical_supplies'))"`) is not RTAMT syntax. RTAMT uses signal-based arithmetic, not string comparisons like that. You'd need to express this as numerical signals.

---

### 5. `firewall_governor/src/audio_monitor.py` — **High**

**The audio conflict detector is broken by design.**

- `fuzzy_match_action()` always returns `1.0` (perfect match).
- `check_confidence_threshold()` always returns `True`.
- `rapidfuzz` is not in `requirements.txt`. If you uncomment the implementation, it will throw `ModuleNotFoundError` on first call.
- More importantly: this class is **never called from anywhere.** It exists in isolation. The ValidationEngine does not reference it. It would never contribute to a veto even if it were implemented.

---

### 6. `firewall_governor/src/viam_client.py` — **High**

**Zero hardware communication.**

- `connect()` calls `pass`. `self.client` and `self.arm` are always `None`.
- `dispatch_move()` calls `pass`. No physical arm is ever commanded.
- `get_actual_state()` returns hardcoded `{"x": 0.0, "y": 0.0, "z": 0.0}` every single time. The "Physical Arm" in Agent Glass would never move.

---

### 7. `mock_environment/mock_so101.py` — **Medium** (mostly okay)

This is the only file with actual working logic. However:

- `get_end_effector_pose()` always returns `{"x": 10.0, "y": 20.0, "z": 5.0}` regardless of joint state. Joint angles are updated in `move_to_joint_positions()` but the pose computation is hardcoded. The "Ghost Arm" and "Physical Arm" in Agent Glass would show the same position no matter what.
- No joint limits are enforced. You can pass `[9999, 9999, 9999]` and it will silently accept it.

---

### 8. `mock_environment/simulate_vla.py` — **High**

**The demo test script does nothing.**

```python
if __name__ == "__main__":
    # print("Running Semantic Firewall Stress Test...")
    # test_firewall_roundtrip()
    pass
```

`test_firewall_roundtrip()` itself is entirely `# implementation_step:` comments followed by `pass`. Even the `generate_adversarial_intent()` function, which does return a payload dict, is never sent anywhere. You cannot run this file to demo anything.

---

### 9. `hardware_bridge/python/main.py` — **High**

- Imports `from arduino.app_utils import bridge, App`. This is not a standard library. It may be part of the Arduino Uno Q SDK, but there is no documentation, no install instructions, and no mention of it in `requirements.txt`. If this library does not exist or is unavailable, this entire module fails to import.
- `send_to_mcu()` calls `pass`. `receive_telemetry()` returns `{}`. `bridge_loop()` body is all comments.

---

### 10. `hardware_bridge/sketch/sketch.ino` — **Medium**

Structurally reasonable. However:

- `move_joint_handler()` mentions "Calculate Inverse Kinematics" but this is the hardest part of robotics and is not sketched out at all, not even pseudocode. Inverse kinematics for a 6-DOF arm is a non-trivial numerical problem. "// implementation_step: angles = inverse_kinematics(x, y, z);" as if IK is a one-liner is wishful thinking.
- `get_telemetry_handler()` returns `{"status": "ok"}` — no actual joint data. The "Physical Arm" visualisation could never show real position.
- `loop()` body is empty. No watchdog timer. The arm has no heartbeat safety mechanism.

---

### 11. `brain_cloud/startup.sh` — **High**

Every actual command is commented out. Running this script prints one line and exits:

```
Cloud Brain (vLLM) initializing on MI300X...
```

---

### 12. `brain_cloud/Dockerfile` — **Critical**

The `ENTRYPOINT` calls the vLLM server but **passes no `--model` argument**. vLLM requires a model path to start. This container will crash immediately on launch with a missing argument error. It is not deployable.

---

### 13. `agent_glass/src/` — **Critical**

`app/`, `components/`, and `store/` are **completely empty directories.** There is no frontend code at all. The "Ghost Arm" 3D visualisation, the Policy HUD, the Audit Trail dashboard — none of it exists, not even as a stub. The plan calls Agent Glass out as a key demo asset for judges ("judges must be able to see into the mind of the Firewall"). Right now, there is nothing to show.

---

### 14. `firewall_governor/requirements.txt` — **High**

Two broken dependencies:

- `whisper-tiny==0.1.0` — **This package does not exist on PyPI.** The real package is `openai-whisper`. `pip install` will fail.
- `rtamt==0.1.0` — RTAMT's actual latest release is in the `0.3.x` range. `0.1.0` likely does not exist. This will also fail.

---

## Architectural Flaws

### Flaw 1: The Entire Security Case Rests on `source_modality` — Which Is Never Checked

The "Trojan Sign" demo depends on the firewall detecting that `source_modality == "visual_text_injection"` and blocking it. **No code anywhere checks `source_modality`.** Not in ValidationEngine. Not in MCR. Not in the Radix Tree. The field appears in the instructions and in one version of the IntentPacket schema, but is simply ignored in all logic.

This is not a missing feature. It is the central security claim of the project. Without it, the firewall is just a confidence-score threshold check — which any attacker bypasses by setting `confidence: 0.95`.

### Flaw 2: The MCR Is Not "Multimodal"

The MCR as described in instructions says: "If a command overrides a Primary User Goal and originates from a Visual Environment Source, escalate to HITL." The implemented MCR (`evaluate_mcr_score`) checks a single confidence float. It does not compare modality. It cannot distinguish between a voice command and a visual injection. The name is false advertising.

### Flaw 3: There Is No Human-in-the-Loop (HITL) State

The instructions explicitly call for HITL escalation. The VetoPacket has `decision: "WARN"` as a possible value. Nothing ever emits `WARN`. No notification system, no pause mechanism, no operator approval flow exists anywhere.

### Flaw 4: Two Incompatible `IntentPacket` Schemas

`main.py` and `models.py` define the same-named class with different fields. This will cause silent data loss or runtime Pydantic errors the moment you try to pass data between the API layer and the engine layer. You must pick one canonical schema immediately.

### Flaw 5: No Data Flow Connects Any Component

The components are islands:
- `main.py` never imports `ValidationEngine`.
- `ValidationEngine` never uses `AudioMonitor`.
- `ViamBridgeController.connect()` is never called.
- `simulate_vla.py` never sends a real HTTP request.
- `agent_glass` has no code to receive WebSocket state.

You have five modules that could, in theory, form a pipeline. Right now each one is a standalone stub that speaks to no one.

---

## Honest Prioritization

If the hackathon has, say, 8 hours left, here is the brutal ranking of what to actually build:

| Priority | Item | Why |
|---|---|---|
| 1 | **Pick one `IntentPacket` schema and delete the other** | Nothing works until this is resolved |
| 2 | **Wire `ValidationEngine` into `main.py`** | The endpoint must actually call the engine |
| 3 | **Implement `radix_tree.insert_rule()` and `search_violation()`** | 5 lines of real code, trivial, must exist |
| 4 | **Create a real YAML policy manifest** | Engine has nothing to load without it |
| 5 | **Add `source_modality` check to ValidationEngine** | This is the entire security claim |
| 6 | **Uncomment `evaluate_mcr_score()` and `check_policy_manifest()`** | Literally just un-comment 3 lines each |
| 7 | **Fix `requirements.txt`** (`openai-whisper`, correct rtamt version) | Won't even install otherwise |
| 8 | **Build minimal Agent Glass UI** | Judges need to see something visual |
| 9 | **Uncomment `simulate_vla.py` main block** | Need a working demo script |
| 10 | **Fix Dockerfile CMD args** | Brain container won't start |

Items 1 through 6 are all you need for a technically credible demo. They are also all achievable in a few hours because the scaffolding and comments already explain exactly what to write. The design is sound. The execution is the problem.
