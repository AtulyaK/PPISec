# File Specification: Governor (Qualcomm Rubik Pi)

> **Updated to reflect the post-evaluation scaffold revision.**  
> All class names, method signatures, and field names in this document match the current code.

---

## Directory: `firewall_governor/`

### `firewall_governor/src/models.py` — **Canonical Data Models**

The single source of truth for all data contracts. Every other file imports from here.

**Classes:**
- `SourceModality(Enum)` — `voice_command`, `visual_object`, `visual_text_injection`, `programmatic`, `unknown`
- `DecisionStatus(Enum)` — `PASS`, `WARN`, `VETO`
- `VetoSource(Enum)` — `RadixTree`, `MCR`, `AudioBridge`, `LTL`, `Exception`
- `IntentPacket(BaseModel)` — request schema: `request_id`, `action`, `target`, `coordinates` (required, no default), `confidence`, `source_modality`, `reasoning_trace`, `raw_transcript`, `aasl_target_level`
- `VetoPacket(BaseModel)` — response schema: `request_id`, `decision`, `reason`, `source`, `latency_ms`, `hitl_override_token`
- `ViamConnectionConfig(BaseModel)` — typed Viam credentials: `address`, `api_key`, `api_key_id`, `arm_component_name`
- `AASLConfig(BaseModel)` — governor config: `policy_manifest_path`, `mcr_base_threshold`, `mcr_visual_injection_threshold`, `mcr_always_warn_modalities`, `enable_temporal_checks`, `ltl_history_window`, `viam_config`

---

### `firewall_governor/src/main.py` — **FastAPI Gateway**

**Lifespan (`@asynccontextmanager async def lifespan`):**
- Startup: loads `AASLConfig`, builds `PolicyLookupTable`, initializes `LTLEvaluator`, constructs `ValidationEngine`
- Shutdown: disconnects Viam, flushes audit logs

**Endpoints:**
```python
@app.post("/propose_intent", response_model=VetoPacket)
async def evaluate_intent(intent: IntentPacket) -> VetoPacket
# Fail-safe: returns VETO on uninitialized engine or any exception

@app.post("/hitl_override")
async def hitl_override(request_id: str, override_token: str, operator_id: str)
# Validates HITL token, re-runs pipeline with elevated trust

@app.get("/health")
async def health_check()
# Returns engine_ready, policy_rules_loaded, ltl_enabled
```

---

### `firewall_governor/src/validation_engine.py` — **4-Stage Pipeline**

```python
class ValidationEngine:
    def __init__(self, config: AASLConfig, radix_table: PolicyLookupTable,
                 ltl_evaluator: LTLEvaluator, audio_bridge: Optional[SemanticAudioBridge])

    def validate_intent(self, intent: IntentPacket, hitl_approved: bool = False) -> VetoPacket
    # Runs: PolicyLookup → MCR → AudioAlign → LTL → PASS
    # Writes audit log BEFORE every return

    def evaluate_mcr(self, intent: IntentPacket) -> Optional[VetoPacket]
    # Check A: source_modality in mcr_always_warn_modalities → WARN + HITL token
    # Check B: confidence < threshold → VETO
    # Returns None on pass

    def evaluate_audio_alignment(self, intent: IntentPacket) -> Optional[VetoPacket]
    # Calls SemanticAudioBridge.compute_semantic_similarity()
    # Returns None on pass, VetoPacket(VETO, source=AudioBridge) on fail

    def _write_audit_log(self, intent: IntentPacket, result: VetoPacket)
    # JSONL append to audit_trail.jsonl; also emits structured logger line
```

---

### `firewall_governor/src/radix_tree.py` — **PolicyLookupTable**

> **Name change:** `ForbiddenActionTree` → `PolicyLookupTable`. It is a nested hash map, not a Radix Tree.

```python
class PolicyLookupTable:
    def insert_rule(self, action: str, target: str)
    # Exact forbidden pair. Normalizes to lowercase.

    def _insert_wildcard_rule(self, action: str, target_class: str)
    # Class-based rule. Substring match on target at query time.

    def search_violation(self, action: str, target: str) -> Tuple[bool, str]
    # Returns (is_violation, match_type) where match_type is "exact", "wildcard", or ""

    def load_from_yaml(self, path: str)
    # Loads exact_pair and wildcard_class rules.
    # Skips spatial_bound and temporal_seq rules (with a warning — those go to LTLEvaluator).

    def rule_count(self) -> int
    # Total exact rules loaded; used by /health endpoint.
```

---

### `firewall_governor/src/ltl_evaluator.py` — **Temporal & Spatial Safety**

```python
class LTLEvaluator:
    def __init__(self, history_window: int = 50)
    # history is a deque(maxlen=history_window) — bounded, auto-evicting

    def load_from_yaml(self, path: str, config: AASLConfig)
    # Routes: spatial_bound → self._spatial_rules list
    #         temporal_seq → self._init_rtamt_monitor()

    def _init_rtamt_monitor(self, formulas: list)
    # Initializes rtamt.StlDiscreteTimeSpecification with declared signals
    # Signals: action_id (float), z (float), modality_id (float)
    # On parse error: logs and sets self.monitor = None (temporal checks disabled)

    def _encode_intent_as_signals(self, intent: IntentPacket, timestamp: float) -> dict
    # Converts string fields to numerical signals using ACTION_ENCODING / MODALITY_ENCODING

    def _check_spatial_rules(self, intent: IntentPacket) -> Optional[str]
    # Evaluates spatial_bound rules without RTAMT. Returns violation string or None.

    def evaluate_invariants(self, intent: IntentPacket) -> Optional[VetoPacket]
    # Runs spatial checks + RTAMT temporal checks.
    # Returns None on pass, VetoPacket(VETO, source=LTL) on violation.
```

**Encoding maps** (must match `policy_manifest.yaml` RTAMT formulas):
```python
ACTION_ENCODING  = {"move": 0, "pick": 1, "place": 2, "dispose": 3, "stop": 4, "drop": 5, "unlock": 6}
MODALITY_ENCODING = {"voice_command": 0, "visual_object": 1, "visual_text_injection": 2, "programmatic": 3, "unknown": 9}
```

---

### `firewall_governor/src/audio_monitor.py` — **SemanticAudioBridge**

```python
class SemanticAudioBridge:
    def __init__(self, similarity_threshold: float = 0.60)
    # Loads sentence-transformers 'all-MiniLM-L6-v2' once at init.
    # Pre-encodes common action verbs into self._action_cache.

    def compute_semantic_similarity(self, transcript: str, proposed_action: str, proposed_target: str) -> float
    # Constructs action phrase as f"{proposed_action} {proposed_target}"
    # Uses cosine similarity between sentence-transformer embeddings.
    # NOT fuzzy string matching — Levenshtein cannot handle semantic equivalents.

    def check_confidence_threshold(self, score: float) -> bool
    # Returns score >= self.threshold
```

---

### `firewall_governor/src/viam_client.py` — **ViamBridgeController**

```python
class ViamBridgeController:
    DEFAULT_ORIENTATION = {"o_x": 0.0, "o_y": 0.0, "o_z": -1.0, "theta": 0.0}
    # Fixed neutral orientation (pointing down). All 6 Viam Pose fields required.

    async def connect(self)
    # Uses typed ViamConnectionConfig fields (no dict key typos possible)
    # Called once in main.py lifespan startup

    async def disconnect(self)
    # Called in main.py lifespan shutdown

    async def dispatch_move(self, intent: IntentPacket) -> bool
    # Builds Viam Pose with DEFAULT_ORIENTATION + intent.coordinates
    # Verifies position post-move (tolerance: 5mm warn, 20mm fail)

    async def get_actual_state(self) -> dict
    # Returns {"x": float, "y": float, "z": float}
    # Used by /ws/telemetry WebSocket for Agent Glass physical_state
```

---

### `firewall_governor/policies/policy_manifest.yaml` — **Safety Rules**

Contains all four rule types. See [`policy_guide.md`](./policy_guide.md) for full syntax.

| Rule Type | Engine | Count |
|---|---|---|
| `exact_pair` | PolicyLookupTable | 5 |
| `wildcard_class` | PolicyLookupTable | 3 |
| `spatial_bound` | LTLEvaluator | 4 |
| `temporal_seq` | RTAMT | 2 |

---

### `firewall_governor/requirements.txt`

```
fastapi==0.110.0
uvicorn==0.27.1
pydantic==2.6.3
pyyaml==6.0.1
numpy==1.26.4
viam-sdk==0.21.0
rtamt==0.3.3           # NOT 0.1.0 (doesn't exist)
openai-whisper==20231117  # NOT whisper-tiny (doesn't exist)
sounddevice==0.4.6
librosa==0.10.1        # Required for 44.1→16kHz resampling
sentence-transformers==2.7.0  # For SemanticAudioBridge
```
