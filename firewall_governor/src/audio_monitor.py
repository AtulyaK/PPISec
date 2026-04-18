import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Audio Alignment Bridge
#
# Purpose: Cross-check the spoken transcript against the VLM's proposed action.
# This detects VLM hallucinations — cases where what the user said and what the
# model proposes to do are semantically misaligned.
#
# Why sentence-transformers (NOT fuzzy string matching):
#   Levenshtein/RapidFuzz measures CHARACTER-LEVEL edit distance.
#   "throw away the keys" vs. "dispose" has negligible character overlap → VETO.
#   But they are semantically equivalent — this would false-positive every time.
#
#   SentenceTransformer encodes both strings into a 384-dim semantic embedding
#   space where synonyms cluster together. "throw away" and "dispose" land close.
#   Cosine similarity in that space correctly returns ~0.75 for this pair.
#
# Model: 'all-MiniLM-L6-v2' — ~80MB, loads in ~1-2s, runs in ~5ms on CPU.
# ─────────────────────────────────────────────────────────────────────────────


class SemanticAudioBridge:
    """
    Validates that a spoken command is semantically aligned with the VLM's
    proposed action. Used as Stage 3 in the ValidationEngine pipeline.

    Instantiated once at server startup. The sentence-transformer model is
    loaded in __init__ to avoid per-request loading overhead (~1–2s load time).

    In software-only (no microphone) mode:
      - If intent.raw_transcript is empty/None, Stage 3 is skipped entirely.
      - The bridge still validates when a transcript is provided via the
        /start_task payload from the Agent Glass CommandPanel.
    """

    def __init__(self, similarity_threshold: float = 0.60):
        """
        Loads the sentence-transformer model and pre-encodes common actions.

        similarity_threshold: minimum cosine similarity score for the transcript
        and proposed action to be considered aligned. Scores below this are
        treated as possible VLM hallucinations and vetoed.

        Typical calibration:
          > 0.70 → definitely aligned (pick + "grab the bottle")
          0.55–0.70 → likely aligned (move + "go to the shelf")
          < 0.55 → suspicious
          < 0.40 → clear mismatch → VETO

        The model is loaded here. If sentence-transformers is not installed,
        logs an error and sets self._model = None. The ValidationEngine checks
        for None and skips Stage 3 when the model is unavailable.
        """
        self.threshold = similarity_threshold

        # Embedding cache: {phrase_string: np.ndarray}
        # Stores pre-computed embeddings for common action verbs and
        # for any (action + target) phrase that has been seen before.
        # This avoids re-encoding the same phrase on every request.
        self._cache: Dict[str, object] = {}

        # Load the sentence-transformer model at init time.
        # 'all-MiniLM-L6-v2' is the standard lightweight choice:
        #   - Size: ~80MB download on first use (cached to ~/.cache/)
        #   - Inference: ~5ms per sentence on CPU (M2 Mac or Cloud host CPU)
        #   - Quality: excellent for English semantic similarity tasks
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer('all-MiniLM-L6-v2')

            # Pre-encode common action verbs so the first request isn't slow.
            # These cover every action type in models.py and the SYSTEM_PROMPT.
            common_actions = [
                "move", "navigate", "go to",
                "pick", "pick up", "grab", "take",
                "place", "put", "set down",
                "dispose", "throw away", "discard", "remove",
                "stop", "halt", "freeze",
                "drop", "drop off",
                "unlock", "open",
                "extend", "stretch",
                "retract", "pull back",
            ]
            for phrase in common_actions:
                self._cache[phrase] = self._model.encode(phrase)

            logger.info("SemanticAudioBridge: sentence-transformer model loaded.")

        except ImportError:
            logger.error(
                "sentence-transformers not installed — Stage 3 audio alignment disabled. "
                "Run: pip install sentence-transformers"
            )
            self._model = None

    def compute_semantic_similarity(
        self,
        transcript: str,
        proposed_action: str,
        proposed_target: str
    ) -> float:
        """
        Computes cosine similarity between the user's spoken transcript and
        the VLM's proposed (action + target) phrase.

        The action phrase is "{proposed_action} {proposed_target}" — combining
        the verb and the object gives the model enough semantic context.
        e.g., "dispose keys" vs. "throw away the keys" → ~0.78 similarity.
        e.g., "dispose keys" vs. "pick up the bottle" → ~0.20 similarity.

        If self._model is None (not installed), returns 1.0 (perfect score)
        so Stage 3 never blocks when the model is unavailable.

        Steps:
          1. If _model is None: return 1.0 (bypass).
          2. Clean transcript: transcript.lower().strip()
          3. Build action_phrase: f"{proposed_action} {proposed_target}".lower()
          4. Retrieve or compute transcript embedding (check _cache first).
          5. Retrieve or compute action_phrase embedding (check _cache first).
          6. Compute cosine similarity using sentence_transformers.util.cos_sim().
             Returns a 1×1 tensor — convert to float.
          7. Return the float score (0.0–1.0).
        """
        if self._model is None:
            return 1.0  # Model not available — bypass this check

        from sentence_transformers import util

        # Step 2: clean the transcript
        transcript_clean = transcript.lower().strip()

        # Step 3: build the comparison phrase
        action_phrase = f"{proposed_action} {proposed_target}".lower().strip()

        # Step 4: encode transcript (cache it for future reuse if same transcript)
        if transcript_clean not in self._cache:
            self._cache[transcript_clean] = self._model.encode(transcript_clean)
        transcript_emb = self._cache[transcript_clean]

        # Step 5: encode action phrase (cache for repeated calls with same action)
        if action_phrase not in self._cache:
            self._cache[action_phrase] = self._model.encode(action_phrase)
        action_emb = self._cache[action_phrase]

        # Step 6: cosine similarity. cos_sim returns a 2D tensor [[score]].
        score = float(util.cos_sim(transcript_emb, action_emb))

        logger.debug(
            f"SemanticAudioBridge: similarity({transcript_clean!r}, "
            f"{action_phrase!r}) = {score:.3f}"
        )

        return score

    def check_confidence_threshold(self, score: float) -> bool:
        """
        Returns True if the similarity score meets the minimum safety threshold.

        Called by ValidationEngine.evaluate_audio_alignment() to convert the
        raw float score into a binary pass/fail decision.

        True  → the transcript and action are sufficiently aligned → Stage 3 PASSES
        False → possible VLM hallucination → Stage 3 returns VETO
        """
        return score >= self.threshold
