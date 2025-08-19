"""Clarification question generator.

Maps detected ambiguity factors into concise micro-questions with a
finite set of options and sensible defaults.  This implementation
relies on static mappings; a trainable model could be dropped in with
the same interface.
"""
from __future__ import annotations
from typing import List, Dict
import uuid

class Clarifier:
    def _qid(self) -> str:
        return "q" + uuid.uuid4().hex[:8]

    def generate(self, query: str, factors: List[str]) -> List[Dict[str, object]]:
        qs: List[Dict[str, object]] = []
        for f in factors:
            if f == "criteria_missing":
                qs.append({
                    "id": self._qid(),
                    "question": "What matters most?",
                    "type": "single_choice",
                    "options": [
                        {"id": "fees", "label": "Lowest fees"},
                        {"id": "speed", "label": "Fast process"},
                        {"id": "trust", "label": "High trust/brand"},
                    ],
                    "default": "fees",
                })
            elif f == "region_missing":
                qs.append({
                    "id": self._qid(),
                    "question": "Which region?",
                    "type": "single_choice",
                    "options": [
                        {"id": "IN", "label": "India"},
                        {"id": "US", "label": "United States"},
                        {"id": "EU", "label": "Europe"},
                    ],
                    "default": "IN",
                })
            elif f == "audience_missing":
                qs.append({
                    "id": self._qid(),
                    "question": "Who is the audience?",
                    "type": "single_choice",
                    "options": [
                        {"id": "simple", "label": "Layperson"},
                        {"id": "expert", "label": "Expert"},
                        {"id": "kids", "label": "Kids"},
                    ],
                    "default": "simple",
                })
            elif f == "length_missing":
                qs.append({
                    "id": self._qid(),
                    "question": "Preferred length?",
                    "type": "single_choice",
                    "options": [
                        {"id": "short", "label": "~150 words"},
                        {"id": "medium", "label": "~300 words"},
                        {"id": "long", "label": "~600 words"},
                    ],
                    "default": "short",
                })
            elif f == "language_missing":
                qs.append({
                    "id": self._qid(),
                    "question": "Target language?",
                    "type": "single_choice",
                    "options": [
                        {"id": "EN", "label": "English"},
                        {"id": "HI", "label": "Hindi"},
                        {"id": "ES", "label": "Spanish"},
                        {"id": "UR", "label": "Urdu"},
                    ],
                    "default": "EN",
                })
            # referent_missing, empty_query or unknown factors are ignored
        return qs[:2]  # limit to 2 questions
