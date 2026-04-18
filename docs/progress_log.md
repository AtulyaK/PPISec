# Progress Log: Semantic Firewall

---

## 📅 2026-04-16 — Pre-Hackathon Scaffold Phase

### Pre-Hackathon Research & Planning
- [x] Reviewed `research.txt` — understood PPIA threat model
- [x] Analyzed `instructions.md` — extracted project requirements and execution plan
- [x] Created `docs/` folder with initial documentation
- [x] Developed initial `system_architecture.md`, `system_design.md`, `repo_structure.md`
- [x] Initialized project directory structure across 4 hardware nodes
- [x] Created `brain_cloud/Dockerfile` for MI300X vLLM deployment
- [x] Created `firewall_governor/` boilerplate (FastAPI + Pydantic models)
- [x] Created `hardware_bridge/` stubs for Uno Q MPU/MCU communication
- [x] Created `agent_glass/` package.json
- [x] Implemented `mock_environment/mock_so101.py` for local simulation

### Scaffold Logic Evaluation & Fixes (same session)
- [x] Full code evaluation performed — identified two fatal issues and 14 high/medium issues
- [x] **FATAL FIX:** Unified two conflicting `IntentPacket` schemas into single canonical `models.py`
- [x] **FATAL FIX:** Added `source_modality` check to MCR — the core PPIA defense
- [x] Added `SourceModality`, `DecisionStatus`, `VetoSource` enums to `models.py`
- [x] Added typed `ViamConnectionConfig` replacing bare `Dict[str, str]`
- [x] Rewrote `main.py`: FastAPI `lifespan()` startup, fail-safe VETO on exception, `/hitl_override` endpoint
- [x] Rewrote `validation_engine.py`: 4-stage pipeline, MCR modality gate, MCR confidence gate, audit log before return, audio bridge as Stage 3
- [x] Renamed `ForbiddenActionTree` → `PolicyLookupTable` (it's a hash map, not a Radix Tree)
- [x] Added wildcard class-based rule support to `PolicyLookupTable`
- [x] Added `ACTION_ENCODING` / `MODALITY_ENCODING` maps to `ltl_evaluator.py` for RTAMT compatibility
- [x] Added `deque(maxlen)` bounded history buffer in `LTLEvaluator`
- [x] Added `_check_spatial_rules()` for bounding-box checks without RTAMT
- [x] Added RTAMT signal encoding and monitor init steps to `ltl_evaluator.py`
- [x] Replaced fuzzy string matching with sentence-transformer semantic embeddings in `audio_monitor.py`
- [x] Added `DEFAULT_ORIENTATION` (all 6 Viam Pose fields) to `viam_client.py`
- [x] Added `ViamBridgeController.disconnect()` for clean shutdown
- [x] Added position verification step to `dispatch_move()`
- [x] Fixed resampling step (44.1kHz → 16kHz) in `npu_audio_processor.py`
- [x] Added `dispatch_to_firewall()` to `npu_audio_processor.py` (the missing last mile)
- [x] Fixed hardware bridge loop ordering: command → dispatch → telemetry → broadcast
- [x] Scoped MCU to joint-space control; documented IK resolution in Viam RDK
- [x] Added emergency stop handler and watchdog heartbeat to `sketch.ino`
- [x] Added `--prefetch-only` flag and GPU count check to `startup.sh`
- [x] Created `firewall_governor/policies/policy_manifest.yaml` (was missing entirely)
- [x] Fixed `requirements.txt`: `whisper-tiny` → `openai-whisper`, `rtamt 0.1.0` → `0.3.3`, added `librosa`, `sentence-transformers`

### Documentation Updated
- [x] Updated `docs/README.md` — comprehensive project README with pipeline table and design decisions
- [x] Updated `docs/system_architecture.md` — reflects actual 4-stage pipeline and modality trust model
- [x] Updated `docs/system_design.md` — canonical schemas, pipeline ASCII diagram, policy routing table
- [x] Updated `docs/implementation_gaps.md` — 21 resolved items, remaining open items with priority
- [x] Created `docs/api_reference.md` — full IntentPacket/VetoPacket field reference with examples
- [x] Created `docs/policy_guide.md` — rule type reference with syntax and examples
- [x] Created `docs/demo_runbook.md` — pre-hackathon checklist + 4-scene demo script

---

## 📅 2026-04-17 — Agent Loop & Control Flow Architecture

### Brain Task Executor (new component)
- [x] **GAP IDENTIFIED:** Brain had no agent loop — treated each command as a single IntentPacket
- [x] Created `brain_cloud/task_executor.py` with full Sense-Plan-Act closed loop
- [x] Implemented `TaskExecutor` class with phases: SENSE → PLAN → VALIDATE → ACT → VERIFY
- [x] Added `BrainConfig` dataclass for all URLs + tuning knobs (camera device, max steps, timeouts)
- [x] Added `SYSTEM_PROMPT` that constrains the VLM to output ONE atomic action JSON per turn
- [x] System prompt forces correct `source_modality` labeling (especially `visual_text_injection`)
- [x] Added task history tracking — VLM receives summary of previous actions for context
- [x] Added termination conditions: `task_complete`, `max_steps`, two-consecutive-VETO abort, WARN pause
- [x] Added AASL level estimation based on action type and modality
- [x] Added fail-safe: unreachable firewall or VLM returns synthetic VETO / emergency stop

### Documentation Updated (agent loop pass)
- [x] Updated `docs/README.md` — new loop diagram, TaskExecutor in repo tree, updated startup, new design decision
- [x] Updated `docs/system_architecture.md` — Cloud Brain component description and data flow reflect agent loop
- [x] Updated `docs/system_design.md` — added Section 9: Brain's Sense-Plan-Act Loop with phases table, termination conditions, prompt design
- [x] Updated `docs/demo_runbook.md` — added TaskExecutor to startup sequence, updated demo talking points, added troubleshooting entries
- [x] Updated `docs/implementation_gaps.md` — resolved #22 and #23, added open items J and K
- [x] Updated `docs/progress_log.md` — this entry

---

## 🚧 Current Status (Pre-Hackathon)

All scaffold files have been written and logically validated. The design is sound and all major holes have been plugged. The project is in **implementation-ready** state.

**What still has `# implementation_step:` comments (not yet running code):**
- `validation_engine.py` — pipeline steps are described but not uncommented
- `radix_tree.py` — `insert_rule()` and `search_violation()` not implemented
- `ltl_evaluator.py` — RTAMT init and evaluation not implemented
- `audio_monitor.py` — semantic similarity not implemented
- `viam_client.py` — `connect()`, `dispatch_move()` not implemented
- `npu_audio_processor.py` — audio capture loop not running
- `hardware_bridge/python/main.py` — socket and bridge calls not implemented
- `sketch.ino` — servo writes not implemented
- `brain_cloud/startup.sh` — vLLM launch commented out
- `brain_cloud/task_executor.py` — VLM query, camera capture, firewall submission commented out
- `agent_glass/src/` — frontend entirely empty

---

## ⏭️ Next Steps (Hackathon Clock)

Priority order for the first 4 hours:

1. [ ] Uncomment `PolicyLookupTable.insert_rule()` and `search_violation()` — 5 lines
2. [ ] Wire `ValidationEngine` into `/propose_intent` handler
3. [ ] Implement `ValidationEngine.evaluate_mcr()` — the critical security check
4. [ ] Implement `ValidationEngine._write_audit_log()`
5. [ ] Add `/ws/telemetry` WebSocket endpoint to `main.py`
6. [ ] Uncomment `simulate_vla.py` — creates working demo script
7. [ ] Wire `ViamBridgeController.connect()` into lifespan
8. [ ] Wire transcript trigger: NPU audio processor → TaskExecutor (new `/start_task` endpoint)
9. [ ] Uncomment `task_executor.py` implementation_step lines (camera, VLM query, firewall POST)
10. [ ] Uncomment all remaining `implementation_step` lines across Python files
11. [ ] Build Agent Glass: Ghost Arm + Physical Arm Three.js scene
12. [ ] Record short video backup of working demo
