# Universal Intent Resolution Engine (UIRE)

The **Universal Intent Resolution Engine (UIRE)** is a middleware layer that transforms
underspecified user queries into clear, structured requests for large language models
or other AI agents.  It provides a complete pipeline: ambiguity detection,
clarification, intent resolution, and prompt construction, plus instrumentation,
data generation, privacy features and deployment artifacts.

This repository is a fully functional, self‑contained demonstration of the UIRE
concept.  It runs offline without external LLMs but is designed to be easily
extended with trained models, reinforcement learning policies and advanced
infrastructure.

## Features

### Ambiguity Detection

* Keyword‐based heuristics identify when a user query lacks critical details,
  such as criteria (e.g. “best”), region (“in which country?”), audience
  (“expert vs beginner”), length (“short vs long summary”) or target language.
* A lightweight `AmbiguityDetector` class exposes a `.detect(query: str)`
  method returning a boolean flag, a confidence score and a list of
  contributing factors.
* Designed to be replaced with a fine‑tuned transformer classifier; see
  `uire/models/ambiguity_detector.py` for interface.

### Clarification Micro‑Questions

* The `Clarifier` maps detected factors into concise, single‑choice
  questions with sensible defaults.  Only two micro‑questions are asked
  maximum to minimise friction.
* Each question has a unique ID, text, a list of option IDs and labels, and a
  default choice.  See `uire/models/clarifier.py`.

### Intent Resolution & Policy

* A rule‑based resolution policy infers the task type (summarise, translate,
  recommend, general) and merges user answers and stored preferences into a
  structured intent (task type, criteria, region, audience, length, language,
  risk).  See `uire/models/policy.py`.
* The same module builds a final, human‑readable prompt to feed into an LLM
  or downstream agent.
* A placeholder Q‑learning implementation in `uire/rl/q_learning.py` shows
  how reinforcement learning could be used to decide whether to ask or
  assume defaults based on user feedback.

### Privacy, Security & Preferences

* User identity is hashed with a configurable salt to avoid storing raw IP
  addresses or identifiers.  See `hashed_id()` in `uire/utils/storage.py`.
* Preferences are stored in SQLite with optional TTL (time‑to‑live), allowing
  per‑user defaults without permanent retention.  `PreferenceStore` and
  `ConsentStore` support opt‑in consent management.
* Rate limiting (token bucket) protects the API from abuse; an optional API
  key (`UIRE_API_KEY`) can be enforced via an HTTP header.

### Telemetry & Metrics

* All interactions are logged to a JSONL file (`UIRE_LOG`) with timestamps.
* In‑memory counters track the number of requests, ambiguous detections,
  clarifications asked, resolutions, answers and errors, along with
  aggregate latency.  Exposed via `/v1/stats`.
* A Prometheus‑style `/metrics` endpoint exports metrics for scraping,
  including average latency.
* Logs can be downloaded from `/v1/export`.

### Dataset & Benchmarking

* A synthetic dataset generator (`uire/data/generate_synthetic.py`) produces
  JSONL lines of random queries with domain labels.  The repository includes
  an example dataset in `uire/data/uire_bench.jsonl`.
* The `/v1/bench` endpoint runs the ambiguity detector over the bench file
  and reports the flagged ratio.

### API Endpoints

* `POST /v1/detect` → detect ambiguity in a query.
* `POST /v1/clarify` → generate micro‑questions based on detected factors.
* `POST /v1/resolve` → build a structured intent and final prompt.
* `POST /v1/answer` → shortcut that returns the final prompt and intent.
* `GET/POST/DELETE /v1/memory` → manage per‑user preferences.
* `GET/POST /v1/consent` → manage user consent.
* `GET /v1/stats` → view internal counters.
* `GET /metrics` → Prometheus metrics.
* `GET /v1/export` → download JSONL logs.
* `GET /v1/bench` → run benchmark over `uire_bench.jsonl`.
* `GET /app` → simple HTML UI demonstrating the flow (no JS frameworks).

### Deployment & Operations

* A `Dockerfile` and `docker-compose.yml` under `uire/ops` allow quick
  containerised deployment.  Environment variables configure the database
  path, log path, API key, rate limits and TLS secrets.
* A Helm chart is provided under `uire/helm` for Kubernetes deployment.
* A GitHub Actions workflow (`.github/workflows/ci.yml`) runs tests on push.
* Unit tests reside in `uire/tests` and can be run locally with
  `pytest -q`.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn pydantic pytest
   ```

2. **Run the server locally:**
   ```bash
   uvicorn uire.api.main:app --host 0.0.0.0 --port 8000
   ```
   Open `http://localhost:8000/app` in your browser to use the UI.

3. **Generate a synthetic dataset:**
   ```bash
   python uire/data/generate_synthetic.py 100 > uire/data/uire_bench.jsonl
   ```

4. **Run tests:**
   ```bash
   pytest -q
   ```

5. **Use Docker:**
   Build and run the container from the repository root:
   ```bash
   docker build -t uire .
   docker run -p 8000:8000 uire
   ```
   or use `docker-compose` in `uire/ops`:
   ```bash
   docker compose -f uire/ops/docker-compose.yml up --build
   ```

6. **Use Helm (optional):**
   The chart under `uire/helm` can be installed into a Kubernetes cluster:
   ```bash
   helm install uire ./uire/helm
   ```

## Extending UIRE

This demonstration intentionally avoids dependencies that cannot be installed in
offline environments.  To bring the system closer to production as described
in the 16‑section design, consider:

* **Replacing heuristics with ML models:** Train a small transformer on
  ambiguous vs clear prompts (e.g. using HuggingFace) and drop it into
  `AmbiguityDetector.detect()`.  Similarly, train a clarifier model or
  engineer few‑shot prompts.
* **Implementing a reinforcement learning policy:** The Q‑learning stub in
  `uire/rl/q_learning.py` can be integrated with a feedback loop to learn
  whether to ask or assume.  Collect user feedback via telemetry and
  update the Q‑table.
* **Adding Prometheus/Grafana dashboards:** Replace the in‑memory metrics
  with the official `prometheus_client` library and deploy Grafana.
* **Improving consent and privacy:** Store only hashed user IDs; allow users
  to opt in/out of memory; support per‑field TTL and anonymisation.
* **Enhancing the UI:** Build a richer frontend (e.g. Streamlit or React) and
  integrate the backend via WebSockets.

## License

This project is provided under the MIT License.