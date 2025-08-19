"""Heuristic ambiguity detector.

This module implements simple keyword-based heuristics to detect when a
natural language query is underspecified.  It can be replaced with a
trained model if desired.
"""
from __future__ import annotations
from typing import Dict, List
import re

# Some generic vague terms suggesting missing criteria
VAGUE_TERMS = {"best", "cheapest", "fastest", "quickest", "ideal", "perfect"}

# Pronouns that may require antecedent resolution
PRONOUNS = {"this", "that", "these", "those", "it", "they"}

# Regions that are commonly specified
REGIONS = {"india", "us", "usa", "europe", "eu", "uk", "canada"}

class AmbiguityDetector:
    def detect(self, query: str) -> Dict[str, object]:
        q = (query or "").strip().lower()
        factors: List[str] = []
        if not q:
            return {"ambiguous": True, "score": 1.0, "factors": ["empty_query"]}

        # Criteria missing if vague term present
        if any(term in q for term in VAGUE_TERMS):
            factors.append("criteria_missing")

        # Referent missing if pronoun appears without a file/text/object mention
        if any(re.search(rf"\b{p}\b", q) for p in PRONOUNS) and not re.search(r"\b(file|document|text|paragraph|image|content|paper)\b", q):
            factors.append("referent_missing")

        # Summarisation tasks often need audience and length
        if re.search(r"\bsummar(ize|ise|y)\b", q):
            if not re.search(r"for\s+(kids|children|adults|experts|beginners)", q):
                factors.append("audience_missing")
            if not re.search(r"\b(short|brief|medium|long|~?\d+ words?)\b", q):
                factors.append("length_missing")

        # Translation tasks need a target language
        if "translate" in q and not re.search(r"to\s+[a-z]+|into\s+[a-z]+", q):
            factors.append("language_missing")

        # Recommendations often need region
        if re.search(r"\b(recommend|best|suggest)\b", q) and not any(r in q for r in REGIONS):
            factors.append("region_missing")

        ambiguous = bool(factors)
        score = min(1.0, 0.3 + 0.2 * len(factors)) if ambiguous else 0.0
        return {"ambiguous": ambiguous, "score": round(score, 2), "factors": list(dict.fromkeys(factors))}
