"""Intent resolution and policy module.

This module contains functions to build a structured intent from the
original query and the user-provided answers.  It also includes a
simple rule-based policy stub, as well as a placeholder Q-learning
implementation that could be extended for reinforcement learning.
"""
from __future__ import annotations
from typing import Dict, Optional
import re

# Simple task inference

def infer_task(query: str) -> str:
    q = query.lower()
    if "translate" in q:
        return "translate"
    if re.search(r"\bsummar(ize|ise|y)\b", q):
        return "summarize"
    if any(k in q for k in ["best", "recommend", "suggest"]):
        return "recommend"
    return "general"

# Risk tier inference based on domain keywords
HIGH_RISK_KEYWORDS = {"medical", "finance", "legal"}

def risk_tier(query: str) -> str:
    q = query.lower()
    return "high" if any(k in q for k in HIGH_RISK_KEYWORDS) else "low"

# Build intent dict and final prompt

def build_intent(query: str, answers: Dict[str, str], defaults: Optional[Dict[str, str]] = None) -> Dict[str, object]:
    t = infer_task(query)
    prefs = defaults or {}
    merged = dict(prefs)
    merged.update(answers or {})
    # Normalise region codes
    region = merged.get("region") or merged.get("q2")
    if region:
        region = region.upper()
        region = {"IN": "IN", "INDIA": "IN", "US": "US", "USA": "US", "EU": "EU", "EUROPE": "EU"}.get(region, region)
    criteria = merged.get("criteria") or merged.get("q1")
    audience = merged.get("audience")
    length = merged.get("length")
    language = merged.get("language") or merged.get("q3")
    risk = risk_tier(query)
    intent = {
        "task_type": t,
        "criteria": criteria,
        "region": region,
        "audience": audience,
        "length": length,
        "language": language,
        "risk": risk,
    }
    # Compose prompt
    if t == "summarize":
        aud = audience or "simple"
        words = {"short": "~150", "medium": "~300", "long": "~600"}.get(length or "short", "~150")
        prompt = f"Summarize the provided content for a {aud} audience in {words} words with citations."
    elif t == "translate":
        lang = (language or "EN").upper()
        prompt = f"Translate the provided text into {lang} with natural tone and preserve formatting."
    elif t == "recommend":
        crit_label = {"fees": "lowest fees", "speed": "fast process", "trust": "high trust/brand"}.get(criteria or "fees", criteria or "fees")
        loc = region or "IN"
        prompt = f"Recommend suitable options in {loc} optimised for {crit_label}. Explain trade-offs and assumptions."
    else:
        prompt = query
    return {"intent": intent, "final_prompt": prompt}

# A placeholder for a reinforcement learning policy.  This could be replaced
# with a Q-learning implementation that trains on user feedback.
class ResolutionPolicy:
    def resolve_intent(self, query: str, answers: Dict[str, str], defaults: Optional[Dict[str, str]] = None) -> Dict[str, object]:
        return build_intent(query, answers, defaults=defaults)
