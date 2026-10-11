# ESG / Safety Incident Intelligence Dashboard

A small, self-contained decision-support prototype for analyzing incident narratives in renewable-energy operations. It includes a FastAPI backend, a responsive HTML/CSS/JavaScript dashboard, a bundled dummy dataset, API endpoints, and a basic evaluation/test workflow.

## Features

- Explainable phrase-based classification into `safety`, `environment`, and `esg_compliance`.
- Provisional severity triage into `low`, `medium`, and `high`, with a reason for the decision.
- Extractive summary that preserves reported facts.
- Preventive action suggestions mapped to the predicted category.
- Local lexical-overlap retrieval of similar example narratives from the bundled CSV.
- Overview cards, category/severity distributions, recurring phrase counts, incident register, filters, and a live analysis form.
- API endpoints for health, dashboard, incidents, trends, evaluation, and incident analysis.

## Project structure

```text
backend/app.py                 FastAPI API and explainable analysis logic
data/safety_esg_incidents.csv  Six labeled dummy incident examples
frontend/index.html            Responsive dashboard UI
tests/test_app.py              Unit tests
evaluate.py                    In-sample sanity-check script
requirements.txt                Python dependencies
Procfile                        Railway start command
```

## Run locally (Windows PowerShell)

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --reload
```

Open `http://127.0.0.1:8000` for the dashboard and `http://127.0.0.1:8000/docs` for interactive API documentation.

If PowerShell blocks environment activation, use `\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload` instead.

## API endpoints

- `GET /api/health` — health check and dataset presence.
- `GET /api/demo` — application status.
- `GET /api/dashboard` — summary cards and incident rows.
- `GET /api/incidents` — incident register.
- `GET /api/trends` — category/severity counts and exact-phrase themes.
- `GET /api/evaluation` — comparison against the supplied reference labels.
- `POST /api/run` — analyze a narrative. JSON body: `{"text":"Oil seepage near a turbine gearbox"}`.

## Evaluation and validation

Run the unit tests:

```powershell
python -m unittest discover -s tests -v
```

Run the reference-row sanity check:

```powershell
python evaluate.py
```

The API computes the metrics from the included CSV. They are **in-sample checks on only six dummy examples**, not an independent test set. The rule-based confidence value is heuristic and is not a calibrated probability. Do not report these values as production performance.

## Method and design choices

1. **Preprocessing:** normalize case and punctuation for phrase matching; validate the required dataset columns; validate API input length.
2. **Classification:** transparent domain phrase scores with specific-phrase overrides. The score breakdown and explanation are returned to the caller.
3. **Severity:** high-risk trigger phrases take precedence; otherwise medium/low indicators are used. Unknown descriptions default to provisional medium triage and explicitly call for human review.
4. **Summarization:** a simple extractive summary keeps the original report wording and avoids generative hallucinations.
5. **Retrieval:** lexical overlap retrieves related example narratives from the local CSV. This is a lightweight retrieval baseline, not vector-search RAG and not a substitute for approved safety procedures.
6. **Trends:** category/severity distributions and exact phrase counts are shown. There are no dates or site IDs in the dataset, so time-based or site-based trends cannot be calculated.

## Limitations and production next steps

- Six synthetic rows are far too few for reliable generalization or model training.
- Phrase rules can miss synonyms, context, negation, and multi-issue reports.
- Severity requires review by qualified safety/environment personnel; this app must not be used as the sole basis for operational decisions.
- Preventive actions are generic examples and must be checked against approved site procedures.
- Retrieval currently uses lexical overlap over example incidents; production RAG should retrieve from authorized SOPs, emergency plans, regulations, and verified historical cases with source citations.
- A production release should add real validated data, timestamps/site/asset identifiers, access controls, audit logs, monitoring, feedback review, privacy controls, and independent evaluation.

## Railway deployment

1. Push this project folder to a GitHub repository.
2. In Railway, create a project and deploy from the GitHub repository.
3. Railway should install dependencies from `requirements.txt`; the included `Procfile` specifies the start command:
   `web: uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
4. Generate a public domain in the Railway service settings.
5. Open the public domain and verify `/`, `/api/health`, `/api/dashboard`, and `/docs`.
6. Include the real deployment URL in your submission. A local URL is not a deployment link.

No API keys or external services are required for this prototype.
