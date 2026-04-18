# Scaffold Logic Evaluation: Semantic Firewall Project
**Date:** 2026-04-16 | **Scope:** Logical correctness and design completeness of all commented scaffolds

> **Ground rules for this review:** Code is not running yet. This evaluates whether the *intended logic, described in the comments and implementation_steps, is coherent, complete, and sufficient to produce the claimed result when implemented.* Bugs are not the target — design holes are.

---

## Overall Scaffold Assessment

The scaffold is about **60% logically sound**. The core data model is well-conceived, the pipeline ordering is correct, and the FastAPI/Pydantic structure is a good choice. However, there are significant holes: several components describe *what* they do but not *how*, the central security claim has no described mechanism to actually execute it, and two components have logical steps that are incorrect in a way that would produce silent wrong answers at runtime.

---

## Component-by-Component Analysis

---

### `models.py` — The Data Contracts

**Rating: Design Sound, Execution Has a Critical Split**

The model separation into `IntentPacket`, `VetoPacket`, and `AASLConfig` is a good instinct. Separating config from request/response models is clean architecture.

**Problems in the logic:**

- `IntentPacket` in `models.py` has `request_id`, `target`, `raw_transcript`. The `IntentPacket` in `main.py` has `intent_id`, `target_object`, `reasoning_trace`, `source_modality`, `aasl_target_level`. **These are two different schemas for the same concept.** The scaffold never describes which one wins or why. When you go to wire them together, you will have to choose and rewrite one. The cost is low now; it grows with every file that imports either version. **Fix this before writing any more files.**

- `IntentPacket.coordinates` in `models.py` defaults to `{"x": 0.0, "y": 0.0, "z": 0.0}`. The LTL invariant `VETO IF coordinates.z < 0` (from instructions) cannot trigger on a packet that defaults to z=0. A packet omitting coordinates entirely looks valid. The scaffold should make `coordinates` required with no default, or explicitly handle None as a rejection case. A missing coordinate should not silently pass the bounding-box check.

- `AASLConfig.viam_config` is typed as `Dict[str, str]`. The steps in `viam_client.py` need `address` and `credentials`. A bare `Dict[str, str]` has no schema enforcement — if a key is misspelled, nothing catches it at config load time. A named inner model would be safer and would catch errors one step earlier.

---

### `main.py` — The API Gateway

**Rating: Structurally Correct, Missing One Critical Step**

The FastAPI skeleton is fine. The `/propose_intent` endpoint and `/health` route are appropriate.

**Logic problem:**

- The described steps say "Integrate ValidationEngine" but there are no described steps for *startup*. When the server boots, who loads the policy YAML? Who builds the `ForbiddenActionTree`? Who initializes the `LTLEvaluator`? FastAPI uses a lifespan pattern (`@app.on_event("startup")`) for this. Without it, `ValidationEngine` would have to be instantiated inside the endpoint handler on every request, which defeats the purpose of preloading the tree. The scaffold has no described step for server startup/initialization. This is a missing logical step, not just a missing line of code.

- There is no described error handling. What happens when `ValidationEngine.validate_intent()` raises an exception? The scaffold implies the response is always `PASS` or `VETO`, but real hardware failure, YAML parse errors, or RTAMT crashes would surface as unhandled 500 errors. Should the default-on-error be `VETO` (fail safe) or `PASS` (fail open)? For a safety system, this answer must be `VETO`. It is not described anywhere.

---

### `validation_engine.py` — The Orchestration Core

**Rating: Pipeline Order Is Correct, MCR Logic Is Incomplete**

The pipeline order — Radix Tree first, then MCR confidence, then LTL temporals — is the right order. Cheap checks (dictionary lookup) before expensive checks (LTL monitor) is correct engineering.

**Logic problems:**

- **The MCR step only checks confidence.** The `evaluate_mcr_score` docstring says "Evaluate the Multimodal Conflict Resolution score against the AASL threshold" and its step is literally just `return confidence >= threshold`. That is a confidence gate. That is not multimodal conflict resolution. The described MCR in the instructions is: "if a command overrides a Primary User Goal AND originates from a visual environment source, escalate." The scaffold has no described step for checking `source_modality`. This means the "Trojan Sign" scenario — where the sign gives a command with high confidence — would pass the MCR even when fully implemented. A sign that generates a 0.95-confidence intent would sail through because the MCR never looks at where the intent came from. **This is the single biggest logical hole in the project.** The fix is to add a step in `evaluate_mcr_score` (or a separate method) that checks `if source_modality in HIGH_RISK_SOURCES and confidence < ELEVATED_THRESHOLD: return False`.

- **No described escalation path.** The docstring in `validate_intent` lists three outcomes: return `VETO` from Radix Tree, return `VETO` from MCR, return `VETO` from LTL. The instruction document calls for a `WARN` / HITL state. There is no described step for *when* to emit `WARN` vs. immediate `VETO`, and no described mechanism to pause execution and wait for human approval. The `VetoPacket.decision` field supports `"WARN"` as a value but nothing describes when it gets set. If you implement what is described, you get a binary PASS/VETO system with no escalation path — which contradicts the project spec.

- **No described order-of-operations for the failure path.** Steps 2-7 all find violations and return immediately. That is correct. But there is no described logging step between detection and return. The audit trail should be written *before* the return, not as an afterthought. If you implement verbatim and add logging later, you will have to touch every return statement.

---

### `radix_tree.py` — The Policy Lookup

**Rating: Data Structure Choice Is Wrong For The Stated Goal**

The class is named `ForbiddenActionTree` and the docstring says "Uses a nested dictionary structure to simulate a Radix Tree/Trie." That sentence is self-contradictory. A nested dict `{action: {target: True}}` is **not a Radix Tree and not a Trie.** It is a nested hash map — a perfectly valid structure, but the name and description are misleading. This matters because if a judge asks "how does your Radix Tree work?" and you explain a hash map, it will look like you don't know what you're talking about.

**More importantly — the lookup logic has a described gap:**

- The described steps for `search_violation` only check for exact action/target matches. The instructions show a policy rule with a wildcard concept: `VETO IF action == 'dispose' AND target_class == 'high_value'`. The scaffold describes checking a specific target (`"keys"`, `"vial_01"`), not a class. If your YAML has `{action: dispose, target: high_value_equipment}` and the intent comes in with `target: microscope`, the tree would not catch it. The scaffold does not describe any fuzzy matching, class hierarchy, or wildcard expansion. This means your policy granularity is limited to exact noun matches, which is extremely brittle for a real scenario where the VLA might name an object differently each time.

- `load_from_yaml` describes iterating over `data.get('forbidden_rules', [])` and calling `insert_rule(rule['action'], rule['target'])`. This assumes a flat list of exact pairs. But the instructions describe rules like `VETO IF coordinates.z < 0`. Spatial/numerical rules cannot be expressed as action/target pairs — they are a different type of constraint entirely. The scaffold does not describe where these rules land. They cannot go in the Radix Tree. They must go in the LTL evaluator. The YAML schema needs to describe both types of rule, and the loader needs to route them to the right engine. That routing logic is completely absent from any scaffold.

---

### `ltl_evaluator.py` — Temporal Safety Invariants

**Rating: The Described Integration Is Non-Functional As Described**

The RTAMT integration steps have a fundamental correctness problem.

- RTAMT is a **Signal Temporal Logic (STL)** library. It monitors continuous numerical signals over time — sensor readings, positions, etc. The described step is: "Feed the new state/signal to the RTAMT monitor." But `IntentPacket` contains strings (`action`, `target`) not numerical signals. RTAMT cannot evaluate `"dispose"` as a signal. To make this work, you would need a preprocessing layer that encodes the intent as numerical features first (e.g., `action_id: 3, target_class_id: 7, z_coord: -5.0`). That encoding layer is not described anywhere in the scaffold.

- The described step says "Evaluate if any invariants are violated in the current window." RTAMT requires you to specify the signal names when defining the monitor, and then feed named time-value pairs. The scaffold does not describe which fields of `IntentPacket` map to which RTAMT signal names. Without this mapping described, whoever implements this step will have to reverse-engineer what the monitor expects.

- The `history: List[IntentPacket]` buffer is described but its size is never bounded. An unbounded buffer that grows with every intent will accumulate over hours. No eviction strategy is described (e.g., rolling window of last N seconds). For a temporal invariant like "never attempt dispose twice within 5 seconds," you only need a finite window. The scaffold implies the full history is needed, which is both memory-wasteful and architecturally unconstrained.

---

### `audio_monitor.py` — Semantic Audio Bridge

**Rating: Logic Is Internally Consistent But Architecturally Orphaned**

The two described steps — fuzzy match the transcript against the proposed action, then threshold — are logically sound for what they do.

**The problem is architectural:**

The scaffold does not describe *when* this class is called in the pipeline. `ValidationEngine.validate_intent()` has no step that mentions `SemanticAudioBridge`. `npu_audio_processor.py` transcribes audio but has no step to call `SemanticAudioBridge`. These are two components designed for the same purpose (audio validation) with no described connection between them or to the main pipeline. How the transcript gets from the NPU into the firewall and cross-checked against the proposed action — the entire flow — is absent.

Also: `fuzzy_match_action()` compares the raw transcript to `proposed_action` (an action verb like `"dispose"`). Fuzzy-matching "Throw away those keys" against "dispose" will give a low score even though they are semantically identical. Levenshtein/RapidFuzz measures character-level similarity, not semantic similarity. The scaffold should describe using semantic embeddings (e.g., a sentence transformer), not fuzzy string matching, for transcript-to-action alignment. As described, this step will produce unreliable results and may VETO valid voice commands while passing adversarial ones with similar surface spelling.

---

### `viam_client.py` — Hardware Dispatch

**Rating: Structurally Correct, Missing Critical Safety Semantics**

The three-step described flow — connect, dispatch_move, get_actual_state — is the right high-level structure.

**Logic problems:**

- `dispatch_move` describes creating a Viam `Pose` with X, Y, Z coordinates and calling `move_to_position()`. The Viam Pose object requires six components: x, y, z, o_x, o_y, o_z, theta (position and orientation). The scaffold only passes three. An arm dispatched without orientation data will behave unpredictably or error. The scaffold should describe where orientation comes from — either a fixed default, derived from the action type, or passed in the `IntentPacket`.

- There is no described step for verifying the move completed successfully. `dispatch_move()` fires and forgets. There is no described step for reading back actual position and comparing it to the intent's requested coordinates. Without this feedback loop, `get_actual_state()` is decorative — it reads state but nothing compares it to expected state or triggers a fault if they diverge.

- There is no described disconnect/cleanup step. If the app crashes, ViaM connections should be closed gracefully. This is both good practice and important for the hardware's safety.

---

### `npu_audio_processor.py` — NPU Audio Pipeline

**Rating: Steps 1-4 Are Individually Sound, But Step 3 Has an Integration Problem**

The flow — capture → denoise → transcribe → dispatch — is the correct pipeline shape.

**Logic problems:**

- Step 3 says "Feed audio frames through a pre-loaded RNNoise or DeepFilterNet model running on the NPU." RNNoise and DeepFilterNet are models that exist, but they are not standard ONNX models out of the box. RNNoise is a C library; DeepFilterNet has Python bindings but is not typically deployed as an ONNX model for NPU execution. The scaffold implies this is a drop-in step but it requires model conversion (ONNX export + Vitis-AI quantization) that can take significant time and may fail on hardware you haven't tested. This is a high-risk dependency.

- `transcribe_with_whisper`: Step 2 says "Tokenize/Pre-process the audio data into the required spectral format (Mel-filterbank)." Whisper's preprocessing pipeline is specific — 16kHz mono, 30-second chunks, log-Mel spectrogram. The scaffold doesn't describe resampling the `sounddevice` output to 16kHz before feeding it to Whisper. Most microphones default to 44.1kHz or 48kHz. Without a resampling step (e.g., using `librosa.resample`), the transcription would be either garbled or error.

- The `__main__` block calls `setup_amd_xdna_npu()` and then the listener loop. But there is no described step for passing the transcript to the Firewall. The comment says `# dispatch_to_brain(text)` but `dispatch_to_brain` is not defined anywhere in the project. The audio pipeline produces a transcript and then that transcript goes nowhere. The last mile of the audio modality — getting the transcript into the `IntentPacket.raw_transcript` field — is not described.

---

### `hardware_bridge/python/main.py` — Uno Q Bridge

**Rating: Design Pattern Is Plausible, Critical Timing Risk**

The described flow — socket listener → `send_to_mcu()` bridge call → 20Hz loop — is architecturally reasonable for an embedded bridge.

**Logic problems:**

- Step 3 in `bridge_loop` describes receiving telemetry *before* processing incoming commands (Step 1 & 2). This ordering means you read old state before handling a new command, not current state after executing it. The more useful ordering is: receive command → dispatch to MCU → read state → broadcast state. The telemetry should confirm the command took effect, not precede it.

- The described 20Hz loop uses `time.sleep(0.05)` *outside* the try/except block, at the module level. If `bridge_loop()` is called once and `time.sleep()` is not inside the function's loop, then `app.run()` presumably handles the loop timing. This is ambiguous — the described step doesn't clarify whether `bridge_loop` is a one-shot function called by `App` on each tick, or whether it should contain its own `while True` loop. If you implement it wrong, you either get one iteration or an infinite nested loop.

- No described handshake or acknowledgment. The bridge calls `bridge.call("move_arm", ...)` but there is no described check that the STM32 received and accepted the command. For physical hardware, silent failure is dangerous.

---

### `hardware_bridge/sketch/sketch.ino` — STM32 MCU

**Rating: The Most Significant Logical Gap in the Entire Project**

- Step 1 in `move_joint_handler` says "Calculate Inverse Kinematics (IK) for the 3-DOF/6-DOF arm." This is described as a single step. **Inverse kinematics for a 6-DOF arm is a full sub-project.** It requires joint geometry parameters (link lengths, DH parameters), a numerical solver (e.g., Jacobian pseudo-inverse) or an analytical solution, and singularity handling. Writing "// angles = inverse_kinematics(x, y, z)" as a one-liner comment implies this is a known, solved function you can just call. It is not. If the SO-101 arm doesn't come with its own IK library, this step alone could consume the entire hackathon. The scaffold should either (a) scope to joint-space control (skip IK, command joints directly instead of XYZ), or (b) acknowledge that IK is a pre-solved dependency that must exist before the hackathon.

- Step 2 says "Constrain angles to physical hardware limits (Safety Layer 0)." But the hardware limits are not described anywhere — not in the sketch, not in any config. If you don't know the actual joint limits of the SO-101, this step cannot be implemented correctly. The scaffold should include where those limits come from (hardware datasheet, Viam config, hardcoded constants).

- Step 3 in `loop()` says "Apply PID smoothing to any active movements." PID controllers require tuning parameters (Kp, Ki, Kd) that are specific to the hardware's mass and motor specs. These are not described anywhere. Without tuning, a PID either oscillates or is so slow it misses timing requirements.

---

### `brain_cloud/startup.sh` — vLLM Brain

**Rating: Steps Are Correct But Incomplete**

The described steps — ROCm env setup → model load → vLLM launch — are in the right order.

**Logic gap:**

- The model described is `Qwen2-VL-7B-Instruct`. This is a 7-billion parameter vision-language model. On launch, vLLM will download this model from HuggingFace (~15GB). During a hackathon, this is a critical path risk — if the model isn't pre-cached, startup could take 20–40 minutes depending on bandwidth. The scaffold has no described step for pre-downloading the model before the event. This should be Step 0.

- `--tensor-parallel-size 8` implies 8 MI300X chiplets. If the hardware available has a different topology, this parameter would cause vLLM to fail on startup. No fallback is described.

---

## Summary: Design Holes That Must Be Resolved Before Writing Code

These are not style issues. Each one will produce a system that behaves differently than intended.

| # | Hole | Severity | Where |
|---|---|---|---|
| 1 | Two incompatible `IntentPacket` schemas — pick one | **Fatal** | `models.py` vs `main.py` |
| 2 | `source_modality` is never checked in MCR — the core security claim has no mechanism | **Fatal** | `validation_engine.py` → `evaluate_mcr_score` |
| 3 | Server startup lifecycle (who loads YAML, who builds the tree) is not described | **High** | `main.py` |
| 4 | Fail-safe vs. fail-open on exception is not described | **High** | `validation_engine.py` |
| 5 | Radix Tree only handles exact noun matches; class-based and spatial rules have no home | **High** | `radix_tree.py` + `ltl_evaluator.py` |
| 6 | RTAMT requires numerical signals; `IntentPacket` has strings — encoding layer not described | **High** | `ltl_evaluator.py` |
| 7 | `SemanticAudioBridge` is never called from the pipeline — audio modality is disconnected | **High** | `audio_monitor.py` |
| 8 | Transcript-to-IntentPacket dispatch step is missing from `npu_audio_processor.py` | **High** | `npu_audio_processor.py` |
| 9 | Fuzzy string matching for semantic alignment will produce unreliable results | **Medium** | `audio_monitor.py` |
| 10 | IK for 6-DOF arm is described as a one-liner — this needs to be a scoped decision | **High** | `sketch.ino` |
| 11 | Viam Pose needs orientation (6 values) not just XYZ (3 values) | **Medium** | `viam_client.py` |
| 12 | `VetoPacket.decision = "WARN"` / HITL escalation path is never described in any step | **Medium** | `validation_engine.py` |
| 13 | Audio input needs resampling to 16kHz before Whisper — not described | **Medium** | `npu_audio_processor.py` |
| 14 | Model pre-download for vLLM is not described — could block startup | **Medium** | `startup.sh` |
| 15 | Bridge loop ordering: telemetry polled before command, should be after | **Low** | `hardware_bridge/python/main.py` |
| 16 | `ForbiddenActionTree` is mislabeled as Radix Tree; it's a nested HashMap — fix the name | **Low** | `radix_tree.py` |
