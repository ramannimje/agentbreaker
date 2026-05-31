"""Deterministic fingerprint engine for loop detection."""
from __future__ import annotations

import hashlib
from typing import List

from agentbreaker.models import ToolCallRecord


class FingerprintEngine:
    def __init__(self, window_size: int = 10, repeat_threshold: int = 3):
        self.window_size = window_size
        self.repeat_threshold = repeat_threshold

    def compute(self, recent_calls: List[ToolCallRecord]) -> str:
        """SHA-256 of concatenated (tool_name:args_hash) tuples in order."""
        seq = [f"{c.tool_name}:{c.args_hash}" for c in recent_calls]
        joined = "|".join(seq)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    def detect_loop(self, recent_calls: List[ToolCallRecord]) -> bool:
        """Detect loops in the recent calls.

        True if any (tool_name,args_hash) appears >= repeat_threshold times in window
        or a rotating subsequence repeats (e.g., A->B->A->B) detected by repeated
        consecutive subsequences.
        """
        seq = [f"{c.tool_name}:{c.args_hash}" for c in recent_calls]
        n = len(seq)
        if n == 0:
            return False

        # simple repetition check
        counts = {}
        for item in seq:
            counts[item] = counts.get(item, 0) + 1
            if counts[item] >= self.repeat_threshold:
                return True

        # detect consecutive repeating subsequence (rotating loops)
        max_k = max(2, n // 2)
        for k in range(2, max_k + 1):
            for start in range(0, n - k * 2 + 1):
                subseq = seq[start : start + k]
                # check next chunk
                next_chunk = seq[start + k : start + k * 2]
                if subseq == next_chunk:
                    return True

        return False
