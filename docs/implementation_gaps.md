# Implementation Gaps — Software-Only Stack

> **Status:** 2026-04-17 — post hardware purge, software transition complete  
> 🟢 = Can fix right now in code (no hardware needed)  
> 🟡 = Needs a decision or external check  
> ✅ = Resolved

---

## ✅ Resolved

<details>
<summary>Click to expand (26 items)</summary>

| # | Item | Resolution |
|---|---|---|
| 1 | Policy Manifest YAML schema | Created `policy_manifest.yaml` with all four rule types |
| 2 | Conflicting `IntentPacket` schemas | Unified in `models.py` |
| 3 | `source_modality` never checked | MCR wired: modality gate + confidence gate |
| 4 | Server startup lifecycle | `main.py` uses FastAPI `lifespan()` |
| 5 | Fail-open on exception | Fail-safe VETO on any exception |
| 6 | PolicyLookupTable | Exact + wildcard class rules |
| 7 | RTAMT string encoding | `ACTION_ENCODING` / `MODALITY_ENCODING` maps |
| 8 | Unbounded LTL history | `deque(maxlen)` |
| 9 | Spatial rules | `LTLEvaluator._check_spatial_rules()` |
| 10 | Audio bridge never called | Wired as Stage 3 |
| 11 | Fuzzy audio matching | Sentence-transformer semantic embeddings |
| 12 | Pose missing orientation | `DEFAULT_ORIENTATION` added (now unused in sw mode) |
| 13 | HITL escalation | `hitl_override_token` + `/hitl_override` endpoint |
| 14 | Wrong pip packages | Fixed `requirements.txt` |
| 15 | Audit log | `_write_audit_log()` JSONL |
| 16 | Brain had no agent loop | `brain_cloud/task_executor.py` created |
| 17 | No VLM system prompt | `SYSTEM_PROMPT` constrains JSON output |
| 18 | Missing `__init__.py` (Gap V) | Created `firewall_governor/src/__init__.py` |
| 19 | `self._start` crash bug (Gap P) | Fixed: `self._start = start_time` in `validate_intent()` |
| 20 | `simulate_vla.py` broken (Gap D) | Full rewrite: 5 scenarios, all required fields, color output |
| 21 | Gripper as separate component (Gap L) | **Moot** — physical arm removed, `SimulatorClient` handles gripper state |
| 22 | No action routing (Gap N) | `SimulatorClient.dispatch_action()` routes all action types |
| 23 | Viam vs Arduino bridge confusion (Gap S) | **Moot** — all hardware removed |
| 24 | NPU → Firewall dispatch conflict (Gap Q) | **Moot** — NPU audio processor removed; commands come from Agent Glass UI |
| 25 | WebSocket telemetry endpoint (Gap B) | `@app.websocket("/ws/telemetry")` implemented in `main.py` |
| 26 | Viam physically not wired (Gap E) | **Moot** — replaced by `SimulatorClient` |
| 27 | `/start_task` endpoint on TaskExecutor (Gap X) | Implemented in `brain_cloud/task_executor.py` |
| 28 | vLLM / Firewall Port Conflict (Gap Y) | Resolved via `VLLM_URL` env var and modular ports |
| 29 | CORS Origin List (Gap Z) | Resolved via `ALLOW_ORIGINS` env var (defaults to wildcard) |
| 30 | HITL token store | Fully implemented in `main.py` |

</details>

---

## 🟡 Open — Decision Required

### W. Visual Input for VLM
**Status:** The VLM needs a scene image for the SENSE phase.
**Resolution:** Implemented `SceneRenderer` (Option B) which combines background scenarios with the virtual robot overlay.

---

## 🟢 Open — Code Now

### Phase 4: Agent Glass Enhancements
| # | Gap | Fix |
|---|---|---|
| — | Scene objects (bottles, boxes) | Add Three.js geometries so screenshots have visual content |
| — | Scenario selector UI | `ScenarioSelector.tsx` component + scenario YAML library |
| — | Three.js screenshot → VLM | `renderer.domElement.toDataURL()` on command submit |
| — | Trojan Sign scene variant | Render a plane mesh with sign texture in the 3D scene |

---

## Hackathon Priority Order

### Must Have (Demo Works)
1. Wire `/start_task` endpoint → TaskExecutor (Gap X)
2. Fix vLLM port conflict (Gap Y)
3. Choose + implement visual input approach (Gap W)
4. Uncomment validation_engine stubs (all `implementation_step` lines)

### Should Have (Demo Is Compelling)
5. Add 3 scenario images to Agent Glass with scenario selector
6. Add Trojan Sign scene variant with visible sign in image
7. Wire full agent loop: Agent Glass → TaskExecutor → VLM → Firewall → SimulatorClient → WebSocket → Agent Glass

### Nice to Have
8. Three.js screenshots as live VLM input
9. Trojan Sign plane mesh rendered in 3D scene
10. RTAMT temporal checks functional
11. Trojan Sign integration test
