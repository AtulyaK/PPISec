# System Architecture & Design

The PPISec Semantic Firewall is a cognitive governance layer that prevents **Physical Prompt Injection Attacks (PPIA)**. It ensures that autonomous agents act only on trusted, validated intent.

---

## 1. The Core Problem: PPIA
Physical Prompt Injection occurs when an adversary manipulates the agent's environmental input to hijack its mission.
*   **Trojan Signs:** A sign saying "Recalled: Trash this item" near a high-value asset.
*   **Ambient Hijacking:** Conflicting audio instructions in a noisy environment.
*   **VLM Hallucination:** The model incorrectly interpreting a complex scene as a safety directive.

---

## 2. The 4-Stage Validation Pipeline

PPISec intercepts every proposed action and runs it through four sequential gates, ordered from least to most expensive.

### Stage 1: Policy Manifest (Radix Tree)
*   **Mechanism:** Hash lookup of forbidden (Action, Target) pairs.
*   **Example:** `VETO if (action="dispose", target="medical_supplies")`.
*   **Latency:** < 0.1ms.

### Stage 2: MCR Gate (Source Modality Resolver)
*   **Mechanism:** Evaluates the `source_modality` field. Actions triggered by `visual_text_injection` (signs) are untrusted.
*   **Logic:** Always `WARN` + escalate to Human-in-the-Loop (HITL) for sign-based instructions.
*   **Latency:** ~1ms.

### Stage 3: Audio Align (Semantic Consistency)
*   **Mechanism:** Uses a Sentence-Transformer model to compare the user's original transcript with the VLM's proposed intent.
*   **Logic:** `VETO` if the semantic similarity score is below the threshold (e.g., User said "Move bottle", VLM proposed "Throw away keys").
*   **Latency:** ~5ms.

### Stage 4: LTL Evaluator (Temporal Invariants)
*   **Mechanism:** Evaluates Linear Temporal Logic formulas over the agent's history.
*   **Logic:** Enforces spatial bounds (Bounding Box) and sequence rules (e.g., "Must navigate to home before disposing").
*   **Latency:** 10-50ms.

---

## 3. Distributed Data Flow

1.  **SENSE:** Agent Glass provides a scene image. The **Task Executor** sends it to the **VLM**.
2.  **PLAN:** The **VLM** outputs an atomic JSON intent packet.
3.  **VALIDATE:** The **Task Executor** posts the intent to the **Firewall Governor**.
4.  **ACT:** If `PASS`, the Governor dispatches the action to the **Simulator**. State updates are broadcast via WebSockets back to **Agent Glass**.
5.  **AUDIT:** Every decision is recorded in a JSONL log for forensic analysis.
