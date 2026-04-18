# Demo Runbook — Semantic Firewall (Software-Only)

> **Event:** StarHacks 2026  
> **Stack:** M2 MacBook (Agent Glass UI) + AMD MI300X (Firewall + VLM)  
> **Core Demo:** Show that a voice command produces safe arm movement, and a Trojan Sign injection is blocked by the firewall in real time.

---

## Pre-Hackathon Checklist

### On the Cloud Machine (AMD MI300X)
- [ ] `bash brain_cloud/startup.sh --prefetch-only` — download Qwen2-VL-7B once (15GB, do before the event)
- [ ] `pip install -r firewall_governor/requirements.txt`
- [ ] Verify: `python -c "from firewall_governor.src.models import IntentPacket; print('OK')"` 
- [ ] Note the cloud machine's public IP / SSH tunnel address

### On the MacBook (Local)
- [ ] `cd agent_glass && npm install`
- [ ] Create `.env.local` in `agent_glass/`:
  ```
  NEXT_PUBLIC_BACKEND_URL=http://<cloud-ip>:8000
  NEXT_PUBLIC_BACKEND_WS=ws://<cloud-ip>:8000/ws/telemetry
  ```
- [ ] `npm run dev` — confirm Agent Glass loads at `localhost:3000`

---

## Startup Sequence (Day Of)

Open 3 terminal windows on the cloud machine:

```bash
# Window 1: vLLM model server (port 8001)
bash brain_cloud/startup.sh

# Window 2: Firewall Governor + Virtual Arm (port 8000)
uvicorn firewall_governor.src.main:app --host 0.0.0.0 --port 8000 --reload

# Window 3: Task Executor Brain
python brain_cloud/task_executor.py
```

On the MacBook:
```bash
cd agent_glass && npm run dev
# → Open http://localhost:3000
```

**Verify startup:**
```bash
curl http://<cloud-ip>:8000/health
# Expected: {"status":"active","engine_ready":true,"simulator_ready":true,"ws_clients":1,...}
```

---

## Demo Script

### Act 1: Safe Command (Baseline, ~1 min)

1. Open Agent Glass at `localhost:3000`
2. Point at the 3D workspace: *"This is our robotic arm operating in a simulated environment."*
3. Click **"Move to shelf"** from the preset panel
4. Watch the arm animate to the new position — the decision badge shows **✅ PASS**
5. *"Every action goes through a 4-stage semantic firewall before the arm moves — even in simulation. In a real deployment, this blocks the physical arm."*

**Expected:** PASS, arm moves, audit log shows green entry, latency < 200ms.

---

### Act 2: Trojan Sign Attack (Main Demo, ~2 min)

1. Click **"🚨 Trojan: Dispose Keys"** from the preset panel
2. The system auto-sets `source_modality: visual_text_injection`
3. Watch the lights turn red — decision badge shows **🚫 VETO** or **⚠️ WARN**
4. The arm **does not move**
5. Point at the audit log: *"Source modality is `visual_text_injection` — the firewall knows this command came from reading a sign, not from a trusted voice command. It's blocked in under 2 milliseconds."*

**Expected:** WARN or VETO decision, arm stays frozen, reason: "Intent sourced from untrusted modality 'visual_text_injection'."

---

### Act 3: The Pipeline Walkthrough (~2 min)

Walk through the 4-stage pipeline using the audit log as a visual aid:

| Stage | What it checks |
|---|---|
| 1. Policy Lookup | Is "dispose keys" a forbidden pair? Yes → VETO |
| 2. MCR Gate | Is the source `visual_text_injection`? Yes → WARN + HITL |
| 3. Audio Align | Does the action match what was spoken? Catches VLM hallucinations |
| 4. LTL Temporals | Are spatial bounds and temporal sequences valid? |

*"A real Trojan Sign attack fails at Stage 1 AND Stage 2. Two independent defenses catch it."*

---

### Act 4: Low-Confidence Attack (~30 sec)

1. Click **"⚠️ Low Confidence"** from the Trojan panel
2. Decision badge shows **🚫 VETO**
3. *"Even if the attack somehow bypasses the modality check, the VLM's own uncertainty score — 35% confidence on this command — is below our threshold. Belt-and-suspenders."*

---

### Act 5: HITL Override (If Time Allows)

1. Trigger a WARN manually via the custom input with `visual_text_injection` modality
2. Explain: *"On WARN, the system pauses and generates a single-use override token. A human operator must explicitly approve before the arm can execute."*
3. Point to the `hitl_override_token` in the audit log response

---

## Talking Points

| Question | Answer |
|---|---|
| "Why software simulation?" | "The attack surface is identical. The firewall architecture is real. We're demonstrating the security layer, not the servo control." |
| "How does the VLM 'see' the scene?" | "We pass a scene image as visual context — either from pre-prepared scenario images or live snapshots from the 3D render." |
| "What's the latency?" | "Stage 1 (Policy) <1ms. Stage 2 (MCR) <2ms. Full pipeline <50ms. Hardware constraint is VLM inference at 50–200ms." |
| "What happens if the firewall crashes?" | "Every exception returns VETO. The arm is never dispatched on an undefined state." |
| "Can this work at scale?" | "The firewall is stateless per request. Multiple arms → multiple firewall instances behind a load balancer. Policy YAML is the single shared config." |

---

## Emergency Fallbacks

| Problem | Fix |
|---|---|
| Cloud machine unreachable | Run firewall locally: `uvicorn firewall_governor.src.main:app --port 8000`. vLLM won't work but `simulate_vla.py` will |
| Agent Glass won't build | Demo via `python mock_environment/simulate_vla.py localhost:8000` in terminal |
| VLM not responding | Disable TaskExecutor, manually POST to `/propose_intent` via `simulate_vla.py` |
| WebSocket disconnects | Refresh Agent Glass — `TelemetrySocket.tsx` auto-reconnects every 3 seconds |
| 3D scene not loading | Check for WebGL errors in console; fallback to showing the JSON audit log in terminal |

---

## Key Files for Live Modification

If you want to live-edit something during the demo:

| File | What to change |
|---|---|
| `firewall_governor/policies/policy_manifest.yaml` | Add/remove forbidden rules in real time |
| `mock_environment/simulate_vla.py` | Add new attack scenarios |
| `agent_glass/src/components/CommandPanel.tsx` | Add new preset buttons |
