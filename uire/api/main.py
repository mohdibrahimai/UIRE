"""FastAPI application for UIRE.

This module wires together the ambiguity detector, clarifier, intent
resolution policy, preference store, consent store and telemetry.  It
exposes endpoints for detection, clarification, resolution, answering,
user memory management, consent, metrics, dataset benchmarking and
log export.  It also serves a minimal static UI for demonstration.
"""
from __future__ import annotations
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import os
import time

from uire.models.ambiguity_detector import AmbiguityDetector
from uire.models.clarifier import Clarifier
from uire.models.policy import build_intent
from uire.utils.storage import PreferenceStore, ConsentStore, hashed_id
from uire.utils.telemetry import log_event, inc, add_latency, stats, export_jsonl, prometheus_text

# Configuration via environment
APP_VERSION = os.environ.get("UIRE_VERSION", "0.5.0")
API_KEY = os.environ.get("UIRE_API_KEY")  # optional
RATE_LIMIT = float(os.environ.get("UIRE_RATE_LIMIT", "10"))  # requests per second
SALT = os.environ.get("UIRE_SALT", "uire_salt")

# App setup
app = FastAPI(title="UIRE: Universal Intent Resolution Engine", version=APP_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Instantiate components
_detector = AmbiguityDetector()
_clarifier = Clarifier()
_store = PreferenceStore()
_consent = ConsentStore()

# Rate limiting: token bucket per client
_buckets: Dict[str, tuple[float, float]] = {}  # client_id -> (tokens, last_timestamp)

# Helper to get client ID

def client_id(request: Request, hdr_user_id: Optional[str]) -> str:
    raw = hdr_user_id or (request.client.host if request.client else "anon")
    return hashed_id(raw, salt=SALT)

# Simple token bucket

def check_rate(client: str):
    now = time.monotonic()
    tokens, last = _buckets.get(client, (RATE_LIMIT, now))
    elapsed = max(0.0, now - last)
    tokens = min(RATE_LIMIT, tokens + elapsed * RATE_LIMIT)
    if tokens < 1.0:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    tokens -= 1.0
    _buckets[client] = (tokens, now)

# API key check

def check_api_key(request: Request):
    if API_KEY and request.headers.get("x-api-key") != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

# Models

class DetectRequest(BaseModel):
    query: str = Field(..., min_length=1)

class DetectResponse(BaseModel):
    ambiguous: bool
    score: float
    factors: List[str]

class ClarifyRequest(BaseModel):
    query: str
    factors: List[str] = []

class QuestionOption(BaseModel):
    id: str
    label: str

class Question(BaseModel):
    id: str
    question: str
    type: str = "single_choice"
    options: List[QuestionOption]
    default: str

class ClarifyResponse(BaseModel):
    questions: List[Question]
    max_questions: int

class ResolveRequest(BaseModel):
    query: str
    answers: Dict[str, str] = {}

class IntentModel(BaseModel):
    task_type: str
    criteria: Optional[str] = None
    region: Optional[str] = None
    audience: Optional[str] = None
    length: Optional[str] = None
    language: Optional[str] = None
    risk: str

class ResolveResponse(BaseModel):
    intent: IntentModel
    final_prompt: str

class MemorySetRequest(BaseModel):
    prefs: Dict[str, str] = {}

class ConsentRequest(BaseModel):
    accepted: bool

# Health check
@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}

# Detect endpoint
@app.post("/v1/detect", response_model=DetectResponse)
async def detect(req: DetectRequest, request: Request, x_user_id: Optional[str] = Header(default=None)):
    check_api_key(request)
    client = client_id(request, x_user_id)
    check_rate(client)
    start = time.monotonic()
    inc("requests_total")
    res = _detector.detect(req.query)
    if res["ambiguous"]:
        inc("ambiguous_total")
    dt = (time.monotonic() - start) * 1000.0
    add_latency(dt)
    log_event({"type": "detect", "client": client, "query": req.query, "result": res, "latency_ms": round(dt, 2)})
    return res

# Clarify endpoint
@app.post("/v1/clarify", response_model=ClarifyResponse)
async def clarify(req: ClarifyRequest, request: Request, x_user_id: Optional[str] = Header(default=None)):
    check_api_key(request)
    client = client_id(request, x_user_id)
    check_rate(client)
    qs = _clarifier.generate(req.query, req.factors or [])
    if qs:
        inc("clarifications_total")
    log_event({"type": "clarify", "client": client, "query": req.query, "factors": req.factors, "questions": qs})
    # Convert to Pydantic
    q_models = []
    for q in qs:
        opts = [QuestionOption(id=o["id"], label=o["label"]) for o in q["options"]]
        q_models.append(Question(id=q["id"], question=q["question"], type=q["type"], options=opts, default=q["default"]))
    return {"questions": q_models, "max_questions": 2}

# Resolve endpoint
@app.post("/v1/resolve", response_model=ResolveResponse)
async def resolve(req: ResolveRequest, request: Request, x_user_id: Optional[str] = Header(default=None)):
    check_api_key(request)
    client = client_id(request, x_user_id)
    check_rate(client)
    prefs = _store.all_for_user(client)
    out = build_intent(req.query, req.answers, defaults=prefs)
    inc("resolved_total")
    log_event({"type": "resolve", "client": client, "query": req.query, "answers": req.answers, "result": out})
    return out

# Answer endpoint
@app.post("/v1/answer")
async def answer(req: ResolveRequest, request: Request, x_user_id: Optional[str] = Header(default=None)):
    check_api_key(request)
    client = client_id(request, x_user_id)
    check_rate(client)
    prefs = _store.all_for_user(client)
    out = build_intent(req.query, req.answers, defaults=prefs)
    inc("answer_total")
    log_event({"type": "answer", "client": client, "query": req.query, "answers": req.answers, "result": out})
    return out

# Memory endpoints
@app.get("/v1/memory")
async def get_memory(request: Request, x_user_id: Optional[str] = Header(default=None)):
    check_api_key(request)
    client = client_id(request, x_user_id)
    return {"prefs": _store.all_for_user(client)}

@app.post("/v1/memory")
async def set_memory(req: MemorySetRequest, request: Request, x_user_id: Optional[str] = Header(default=None)):
    check_api_key(request)
    client = client_id(request, x_user_id)
    for k, v in (req.prefs or {}).items():
        _store.set(client, k, v)
    return {"prefs": _store.all_for_user(client)}

@app.delete("/v1/memory")
async def clear_memory(request: Request, x_user_id: Optional[str] = Header(default=None)):
    check_api_key(request)
    client = client_id(request, x_user_id)
    _store.clear_user(client)
    return {"status": "cleared"}

# Consent endpoints
@app.get("/v1/consent")
async def get_consent(request: Request, x_user_id: Optional[str] = Header(default=None)):
    check_api_key(request)
    client = client_id(request, x_user_id)
    return {"accepted": _consent.get(client)}

@app.post("/v1/consent")
async def set_consent(req: ConsentRequest, request: Request, x_user_id: Optional[str] = Header(default=None)):
    check_api_key(request)
    client = client_id(request, x_user_id)
    _consent.set(client, req.accepted)
    return {"accepted": _consent.get(client)}

# Stats endpoint
@app.get("/v1/stats")
async def get_stats():
    return stats()

# Prometheus metrics
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return prometheus_text()

# Export logs
@app.get("/v1/export")
async def export():
    path = export_jsonl()
    return FileResponse(path, filename="events.jsonl", media_type="application/jsonl")

# Bench run
@app.get("/v1/bench")
async def bench():
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "uire_bench.jsonl")
    data_path = os.path.abspath(data_path)
    total = 0
    flagged = 0
    if os.path.exists(data_path):
        import json
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                total += 1
                rec = json.loads(line)
                q = rec.get("query", "")
                res = _detector.detect(q)
                if res.get("ambiguous"):
                    flagged += 1
    return {"total": total, "flagged": flagged, "flag_rate": round(flagged / (total or 1), 3)}

# Serve static UI
ui_dir = os.path.join(os.path.dirname(__file__), "..", "ui")
app.mount("/app", StaticFiles(directory=ui_dir, html=True), name="app")
