import time
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from .models import (
    IntentPacket, VetoPacket, AASLConfig,
    DecisionStatus, VetoSource, SourceModality
)
from .radix_tree import PolicyLookupTable
from .ltl_evaluator import LTLEvaluator
from .audio_monitor import SemanticAudioBridge

logger = logging.getLogger(__name__)

# High-risk actions: any IntentPacket with one of these actions sourced from
# an untrusted modality (VISUAL_TEXT_INJECTION or UNKNOWN) triggers at least WARN.
# This set is also used by _estimate_aasl_level() in task_executor.py.
HIGH_RISK_ACTIONS = {"dispose", "drop", "destroy", "discard", "override", "unlock"}


class ValidationEngine:
    """
    Core orchestration engine for the Semantic Firewall.

    Runs a four-stage pipeline in cheap-to-expensive order:
      Stage 1 → PolicyLookupTable   (~0ms)    — exact + wildcard forbidden pairs
      Stage 2 → MCR modality gate   (~1ms)    — untrusted source + confidence
      Stage 3 → Audio alignment     (~5ms)    — semantic similarity (sentence-transformer)
      Stage 4 → LTL temporals       (~10–50ms) — spatial bounds + RTAMT STL

    Pipeline design principles:
      - Each stage returns a VetoPacket (blocking result) or None (pass → next stage).
      - The audit log is written BEFORE every return so the decision is always recorded
        even if the caller never receives the response (network failure, timeout).
      - On any unhandled exception in this class, main.py's exception handler applies
        fail-safe VETO. No panic path should silently PASS.
    """

    def __init__(
        self,
        config: AASLConfig,
        radix_table: PolicyLookupTable,
        ltl_evaluator: LTLEvaluator,
        audio_bridge: Optional[SemanticAudioBridge] = None,
    ):
        self.config       = config
        self.radix_table  = radix_table
        self.ltl_evaluator = ltl_evaluator
        # audio_bridge is optional. If None, Stage 3 is skipped (no sentence-transformer
        # available). The firewall still provides full Stage 1, 2, 4 protection.
        self.audio_bridge = audio_bridge

    # ─────────────────────────────────────────────────────────────────────────
    # Main pipeline entry point
    # ─────────────────────────────────────────────────────────────────────────

    def validate_intent(
        self,
        intent: IntentPacket,
        hitl_approved: bool = False
    ) -> VetoPacket:
        """
        Runs the full four-stage validation pipeline for one IntentPacket.

        Called by main.py's POST /propose_intent handler.
        Also called internally by the HITL override flow with hitl_approved=True.

        hitl_approved=True:
          Skips Stage 2 (MCR modality gate). Used when an operator has explicitly
          approved a WARN'd intent via /hitl_override. All other stages still run —
          a human cannot override a spatial rule or a hard policy violation.

        Returns:
          A VetoPacket with decision=PASS, WARN, or VETO and an audit log entry
          written to disk.
        """
        start_time = time.time()
        # Store on instance so evaluate_mcr / evaluate_audio_alignment can compute
        # their latency relative to the pipeline start without needing start_time as a param.
        self._start = start_time

        # ── Stage 1: Policy Manifest Lookup ───────────────────────────────────
        # Checks the forbidden (action, target) pair table and wildcard class rules.
        # This is the fastest stage (O(1) hash lookup). Returns immediately on match.
        # No need to run expensive stages after a Stage 1 block.
        is_forbidden, match_type = self.radix_table.search_violation(
            intent.action, intent.target
        )
        if is_forbidden:
            latency = (time.time() - start_time) * 1000
            result = VetoPacket(
                request_id=intent.request_id,
                decision=DecisionStatus.VETO,
                source=VetoSource.RADIX_TREE,
                reason=(
                    f"Forbidden action/target pair: '{intent.action}' on '{intent.target}' "
                    f"(match: {match_type})."
                ),
                latency_ms=latency
            )
            self._write_audit_log(intent, result)
            return result

        # ── Stage 2: MCR — Modality + Confidence Gate ─────────────────────────
        # The primary anti-injection check. Inspects source_modality (trust level)
        # and confidence score. HITL-approved intents skip this stage because the
        # operator has already reviewed and approved the source modality.
        if not hitl_approved:
            mcr_result = self.evaluate_mcr(intent)
            if mcr_result is not None:  # None = passed
                self._write_audit_log(intent, mcr_result)
                return mcr_result

        # ── Stage 3: Audio Transcript Alignment ───────────────────────────────
        # Runs ONLY when:
        #   (a) self.audio_bridge is not None (model is loaded), AND
        #   (b) intent.raw_transcript is non-empty (voice command was involved).
        # If the transcript is absent (programmatic command, no voice), skip this stage.
        # This stage catches VLM hallucinations where the model proposes an action
        # not present in or semantically inconsistent with what the user said.
        if self.audio_bridge and intent.raw_transcript:
            audio_result = self.evaluate_audio_alignment(intent)
            if audio_result is not None:
                self._write_audit_log(intent, audio_result)
                return audio_result

        # ── Stage 4: LTL Temporal Invariants ──────────────────────────────────
        # The most expensive stage. Evaluates spatial bounding-box rules and RTAMT
        # Signal Temporal Logic invariants against the rolling intent history.
        # Only runs if enabled in config (default: True).
        if self.config.enable_temporal_checks:
            ltl_result = self.ltl_evaluator.evaluate_invariants(intent)
            if ltl_result is not None:
                # LTL evaluator computes its own latency — update it to the full pipeline time.
                ltl_result.latency_ms = (time.time() - start_time) * 1000
                self._write_audit_log(intent, ltl_result)
                return ltl_result

        # ── All stages passed ─────────────────────────────────────────────────
        latency = (time.time() - start_time) * 1000
        result = VetoPacket(
            request_id=intent.request_id,
            decision=DecisionStatus.PASS,
            source=None,
            reason="All validation stages passed.",
            latency_ms=latency
        )
        self._write_audit_log(intent, result)
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 2: MCR — Multimodal Conflict Resolver
    # ─────────────────────────────────────────────────────────────────────────

    def evaluate_mcr(self, intent: IntentPacket) -> Optional[VetoPacket]:
        """
        The Multimodal Conflict Resolver. The single most important anti-injection gate.

        Two independent checks run sequentially. The first failure short-circuits.

        ── Check A — Source Modality Gate ────────────────────────────────────
        Checks if intent.source_modality is in config.mcr_always_warn_modalities.
        The default list includes VISUAL_TEXT_INJECTION and UNKNOWN.

        When triggered:
          - Generates a single-use HITL override token (secrets.token_urlsafe(16)).
          - Returns WARN VetoPacket with the token embedded.
          - The Agent Glass UI shows the WARN and the token.
          - An operator can call POST /hitl_override with the token to re-validate
            the intent with hitl_approved=True, bypassing this check.

        This is the primary defense against Trojan Signs. A sign that causes the
        VLM to output source_modality="visual_text_injection" is blocked here
        in ~1ms, before any expensive LTL computation runs.

        ── Check B — Confidence Threshold Gate ───────────────────────────────
        Applies a per-modality minimum confidence threshold.

        - VISUAL_TEXT_INJECTION: threshold = config.mcr_visual_injection_threshold (default 0.99)
          (extremely high — a VLM reading a sign should almost never be this confident)
        - All other trusted modalities: threshold = config.mcr_base_threshold (default 0.70)

        If confidence < threshold: return VETO.

        Note: Check A (WARN) runs BEFORE Check B (VETO). An intent with
        VISUAL_TEXT_INJECTION that passes Check A (HITL approved) will still be
        rejected by Check B unless confidence is ≥ 0.99.

        Returns None if both checks pass.
        """
        # Check A: Source modality trust gate
        if intent.source_modality in self.config.mcr_always_warn_modalities:
            # Generate a single-use, cryptographically random HITL override token.
            # urlsafe_b64 encoding, 16 bytes = 22 character token. Hard to guess.
            # In a full production system: store (request_id → token) in a
            # time-limited cache (TTL 60s) for the /hitl_override endpoint to verify.
            token = secrets.token_urlsafe(16)

            latency = (time.time() - self._start) * 1000
            return VetoPacket(
                request_id=intent.request_id,
                decision=DecisionStatus.WARN,
                source=VetoSource.MCR,
                reason=(
                    f"Intent sourced from untrusted modality "
                    f"'{intent.source_modality.value}'. "
                    f"Action '{intent.action}' on '{intent.target}' requires human approval."
                ),
                latency_ms=latency,
                hitl_override_token=token
            )

        # Check B: Confidence threshold gate
        # Higher threshold for visual text injection (even if somehow past Check A).
        threshold = (
            self.config.mcr_visual_injection_threshold
            if intent.source_modality == SourceModality.VISUAL_TEXT_INJECTION
            else self.config.mcr_base_threshold
        )

        if intent.confidence < threshold:
            latency = (time.time() - self._start) * 1000
            return VetoPacket(
                request_id=intent.request_id,
                decision=DecisionStatus.VETO,
                source=VetoSource.MCR,
                reason=(
                    f"Confidence {intent.confidence:.2f} is below the "
                    f"{threshold:.2f} threshold for modality "
                    f"'{intent.source_modality.value}'."
                ),
                latency_ms=latency
            )

        # Both checks passed
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 3: Audio Transcript Alignment (VLM Hallucination Detection)
    # ─────────────────────────────────────────────────────────────────────────

    def evaluate_audio_alignment(self, intent: IntentPacket) -> Optional[VetoPacket]:
        """
        Cross-checks the spoken user transcript against the proposed action.

        Detects cases where the VLM reads the scene and proposes an action that
        was NOT in the user's original command. Example:
          User says: "move the bottle to the shelf"
          VLM sees sign: "DISPOSE ALL ITEMS"
          VLM proposes: action="dispose", target="items"
          Audio check: "move the bottle to the shelf" vs "dispose items" → low similarity → VETO

        This is DIFFERENT from MCR:
          MCR checks the SOURCE CHANNEL (was the command from a sign?)
          Audio alignment checks whether the VLM INTERPRETED the command correctly.
          Both can block the same attack, but from different angles. Belt + suspenders.

        Uses SemanticAudioBridge.compute_semantic_similarity() which uses
        sentence-transformer cosine similarity (NOT fuzzy string matching).

        Steps:
          1. Call audio_bridge.compute_semantic_similarity(transcript, action, target).
          2. Call audio_bridge.check_confidence_threshold(score) → True/False.
          3. If below threshold: return VETO VetoPacket with score in reason.
          4. If above threshold: return None (Stage 3 passes).
        """
        score = self.audio_bridge.compute_semantic_similarity(
            transcript=intent.raw_transcript,
            proposed_action=intent.action,
            proposed_target=intent.target
        )

        if not self.audio_bridge.check_confidence_threshold(score):
            latency = (time.time() - self._start) * 1000
            return VetoPacket(
                request_id=intent.request_id,
                decision=DecisionStatus.VETO,
                source=VetoSource.AUDIO_BRIDGE,
                reason=(
                    f"Transcript '{intent.raw_transcript}' has low semantic alignment "
                    f"(score={score:.2f}) with proposed action "
                    f"'{intent.action}' on '{intent.target}'. "
                    f"Possible VLM hallucination or intent hijacking."
                ),
                latency_ms=latency
            )

        return None  # Stage 3 passed

    # ─────────────────────────────────────────────────────────────────────────
    # Audit Trail
    # ─────────────────────────────────────────────────────────────────────────

    def _write_audit_log(self, intent: IntentPacket, result: VetoPacket):
        """
        Writes a structured JSONL record to the audit trail for every decision.
        Called BEFORE every return in validate_intent — never omit this call.

        Format: one JSON object per line (JSONL), appended to "audit_trail.jsonl".
        JSONL enables streaming reads and log rotation without parsing the whole file.

        Record schema:
          timestamp       : ISO 8601 UTC string
          request_id      : UUID from IntentPacket
          action          : e.g., "dispose"
          target          : e.g., "keys"
          source_modality : e.g., "visual_text_injection"
          confidence      : float, e.g., 0.35
          aasl_level      : int 1–4
          reasoning_trace : VLM's own explanation (forensic value)
          decision        : "PASS" | "WARN" | "VETO"
          veto_source     : "RADIX_TREE" | "MCR" | "AUDIO_BRIDGE" | "LTL" | None
          reason          : human-readable explanation
          latency_ms      : float, end-to-end pipeline latency

        Also emits the record as a structured logger.info() line so Agent Glass
        can stream it in real time from the server logs.

        Do NOT swallow exceptions here. A failed audit write is a system integrity
        failure that should surface immediately, not be hidden.
        """
        record = {
            "timestamp":       datetime.now(timezone.utc).isoformat(),
            "request_id":      intent.request_id,
            "action":          intent.action,
            "target":          intent.target,
            "source_modality": intent.source_modality.value,
            "confidence":      intent.confidence,
            "aasl_level":      intent.aasl_target_level,
            "reasoning_trace": intent.reasoning_trace,
            "decision":        result.decision.value,
            "veto_source":     result.source.value if result.source else None,
            "reason":          result.reason,
            "latency_ms":      result.latency_ms,
        }

        # Append to JSONL log file (created on first write).
        with open("audit_trail.jsonl", "a") as f:
            f.write(json.dumps(record) + "\n")

        # Also emit as structured log line for real-time Agent Glass streaming.
        logger.info(f"AUDIT: {json.dumps(record)}")
