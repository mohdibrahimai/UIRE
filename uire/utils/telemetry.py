"""Telemetry and metrics utilities.

Provides a simple JSONL event logger and in-memory counters, plus
exposure of Prometheus-style metrics.
"""
from __future__ import annotations
import os
import json
import time
from threading import Lock
from typing import Dict, Any

LOG_PATH = os.environ.get("UIRE_LOG", "logs/events.jsonl")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

_counters = {
    "requests_total": 0,
    "ambiguous_total": 0,
    "clarifications_total": 0,
    "resolved_total": 0,
    "answer_total": 0,
    "errors_total": 0,
    "latency_ms_sum": 0.0,
}
_lock = Lock()

# Log event to JSONL

def log_event(event: Dict[str, Any]) -> None:
    event["ts"] = int(time.time() * 1000)
    with _lock:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

# Increment counter

def inc(key: str, amt: int = 1) -> None:
    with _lock:
        _counters[key] = _counters.get(key, 0) + amt

# Add latency

def add_latency(ms: float) -> None:
    with _lock:
        _counters["latency_ms_sum"] += ms

# Stats summary

def stats() -> Dict[str, Any]:
    with _lock:
        counters = dict(_counters)
    total = counters.get("requests_total", 0) or 1
    counters["avg_latency_ms"] = round(counters.get("latency_ms_sum", 0.0) / total, 2)
    return counters

# Export path

def export_jsonl() -> str:
    return LOG_PATH

# Prometheus text exposition

def prometheus_text() -> str:
    s = stats()
    lines = []
    lines.append(f"uire_requests_total {s.get('requests_total',0)}")
    lines.append(f"uire_ambiguous_total {s.get('ambiguous_total',0)}")
    lines.append(f"uire_clarifications_total {s.get('clarifications_total',0)}")
    lines.append(f"uire_resolved_total {s.get('resolved_total',0)}")
    lines.append(f"uire_answer_total {s.get('answer_total',0)}")
    lines.append(f"uire_errors_total {s.get('errors_total',0)}")
    lines.append(f"uire_latency_ms_sum {s.get('latency_ms_sum',0.0)}")
    lines.append(f"uire_avg_latency_ms {s.get('avg_latency_ms',0.0)}")
    return "\n".join(lines) + "\n"
