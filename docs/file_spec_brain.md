# File Specification: Cloud Brain (AMD MI300X)

> **Updated to reflect the Sense-Plan-Act agent loop architecture.**  
> The Brain is no longer a passthrough — it runs a closed-loop `TaskExecutor` that decomposes user commands into atomic actions.

---

## Directory: `brain_cloud/`

### `brain_cloud/startup.sh` — **vLLM Server Launch**

Starts the VLM inference server on the MI300X with ROCm acceleration.

**Key flags:**
- `--prefetch-only` — downloads the 15GB model without launching the server (run before hackathon)
- `--tensor-parallel-size` — must match actual GPU count (verify with `rocm-smi --showid`)
- `--trust-remote-code` — required for Qwen2-VL models

**Model:** `Qwen/Qwen2-VL-7B-Instruct` — Vision + Language. Accepts image/video frames + text. Does **not** accept raw audio. Audio is pre-transcribed by Whisper on the Legion and sent as text.

---

### `brain_cloud/task_executor.py` — **Sense-Plan-Act Agent Loop**

The core control loop that decomposes high-level user commands into atomic `IntentPacket`s.

**Classes:**

```python
@dataclass
class BrainConfig:
    vllm_base_url: str       # vLLM endpoint (default: http://localhost:8000/v1)
    vllm_model_id: str       # Model name (default: Qwen/Qwen2-VL-7B-Instruct)
    firewall_url: str        # Governor endpoint (default: http://rubik-pi.local:8000)
    camera_device: int       # Camera index for cv2.VideoCapture (default: 0)
    frames_per_sense: int    # Frames per SENSE step (default: 1 = snapshot)
    max_steps: int           # Loop cap — prevents infinite loops (default: 20)
    action_timeout_s: float  # Wait for arm completion (default: 15.0)
    poll_interval_s: float   # Telemetry polling interval (default: 0.5)
```

```python
class TaskExecutor:
    async def initialize(self)
    # Opens camera + HTTP client. Call once at startup.

    async def shutdown(self)
    # Releases camera + closes HTTP client. Call on exit.

    async def execute_task(self, transcript: str) -> dict
    # The main loop. Runs SENSE → PLAN → VALIDATE → ACT → VERIFY
    # until VLM says task_complete or max_steps or abort condition.
    # Returns summary dict with steps, decisions, completion status.

    def _capture_frames(self) -> list[str]
    # Captures N camera frames as base64-encoded JPEGs

    async def _get_arm_state(self) -> dict
    # Queries Governor telemetry for current joints + xyz

    async def _query_vlm(self, frames, transcript, arm_state) -> dict
    # Sends multimodal chat completion to vLLM (OpenAI-compatible API)
    # Returns parsed JSON: {action, target, coordinates, confidence, source_modality, ...}

    async def _submit_to_firewall(self, vlm_output, transcript) -> dict
    # Wraps VLM output into canonical IntentPacket, POSTs to /propose_intent
    # Returns VetoPacket response

    @staticmethod
    def _estimate_aasl_level(vlm_output) -> int
    # Maps (action, modality) to AASL level 1–4

    async def _wait_for_completion(self) -> bool
    # Polls telemetry until arm reports idle or timeout
```

**System Prompt (`SYSTEM_PROMPT`):**
- Forces VLM to output **one atomic action** per turn in a fixed JSON schema
- Defines valid action verbs: `move | pick | place | dispose | stop | drop`
- Requires correct `source_modality` labeling — especially `visual_text_injection`
- Requires `task_complete: true` only when fully verifiable
- Fallback: ambiguous commands → `action: stop, confidence: < 0.5`

**Termination conditions:**

| Condition | Behavior |
|---|---|
| `task_complete: true` | Normal completion |
| `max_steps` reached | Warning, loop ends |
| Two consecutive VETOs | Abort — VLM is stuck |
| WARN decision | Pause — wait for HITL override |

**Dependencies (not in Governor's requirements.txt — install on MI300X):**
- `httpx` — async HTTP client
- `opencv-python` — camera capture
- `numpy` — frame processing

---

### `brain_cloud/Dockerfile` — **ROCm vLLM Container**

Minimal Dockerfile for building the vLLM inference container with ROCm support.

---

## Integration Points

### Input: How the TaskExecutor Receives Commands

**Current gap (see implementation_gaps.md Item J):** The NPU audio processor currently dispatches transcripts to the firewall, but the TaskExecutor needs to receive them to start a new task loop.

**Planned approach:** Add a `/start_task` REST endpoint to the TaskExecutor that accepts `{"transcript": "..."}` from the NPU audio processor.

### Output: How the TaskExecutor Submits to the Firewall

Each loop iteration POSTs one `IntentPacket` to `POST {firewall_url}/propose_intent`. The `TaskExecutor` adds:
- `request_id` — new UUID per iteration
- `raw_transcript` — the original user command (same across all iterations)
- `aasl_target_level` — estimated from action type

### Feedback: How the TaskExecutor Knows an Action Completed

After a PASS, the executor polls the Governor's telemetry endpoint until the arm reports `status: idle`, then captures a new frame for the next SENSE step.
