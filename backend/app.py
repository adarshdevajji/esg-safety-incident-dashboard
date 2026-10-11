"""Explainable incident intelligence API for the ESG / Safety dashboard.

This starter implementation uses transparent phrase rules and a small local
retrieval baseline. It is a demonstration, not a certified safety system.
"""
from collections import Counter
from pathlib import Path
import re
from typing import List

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(
    title="ESG / Safety Incident Intelligence Dashboard",
    description="Explainable analysis of renewable-energy safety and ESG narratives.",
    version="1.0.0",
)
BASE = Path(__file__).resolve().parents[1]
DATA_FILE = BASE / "data" / "safety_esg_incidents.csv"
FRONTEND_FILE = BASE / "frontend" / "index.html"
CATEGORIES = ["safety", "environment", "esg_compliance"]
SEVERITIES = ["low", "medium", "high"]

CATEGORY_RULES = {
    "safety": [
        "injury", "slipped", "slip", "near miss", "ppe", "helmet", "worker",
        "vehicle movement", "cable trench", "unsafe", "fall", "electrical shock",
        "fire", "first aid", "protective equipment", "hazardous movement",
    ],
    "environment": [
        "oil seepage", "oil spill", "spill", "leakage", "leaking", "water usage",
        "water consumption", "water wastage", "wastewater", "pollution", "chemical",
        "contamination", "emission", "biodiversity", "soil", "environmental",
    ],
    "esg_compliance": [
        "compliance", "non-compliance", "non compliance", "deviation", "policy",
        "regulation", "audit", "reporting", "waste segregation", "segregation",
        "permit", "procedure", "governance", "documentation",
    ],
}
SEVERITY_RULES = {
    "high": ["fatality", "fatal", "life-threatening", "life threatening", "electrocution",
             "major injury", "serious injury", "fire", "explosion", "near miss", "oil spill",
             "uncontrolled release", "exposed live wire", "vehicle movement close", "critical", "oil seepage"],
    "medium": ["minor injury", "injury", "slipped", "ppe", "non-compliance", "non compliance",
               "leakage", "leaking", "water usage spike", "spill kit", "unsafe condition"],
    "low": ["documentation", "labeling", "labelling", "minor deviation", "waste segregation",
            "housekeeping observation", "no injury", "resolved", "corrected"],
}
ACTIONS = {
    "safety": [
        "Make the immediate area safe and notify the responsible site supervisor.",
        "Review the task-specific risk assessment, training, and required PPE or barriers.",
        "Record corrective actions and verify completion before closing the incident.",
    ],
    "environment": [
        "Contain the release or stop the leak if this can be done safely; follow the site emergency procedure.",
        "Inspect the source and assess potential impact to soil, water, and nearby equipment.",
        "Document cleanup, waste handling, and corrective maintenance; escalate reportable events per site policy.",
    ],
    "esg_compliance": [
        "Check the applicable site procedure and record the specific requirement that was not met.",
        "Correct the deviation and brief the relevant employees or contractors.",
        "Schedule a follow-up inspection or audit to verify sustained compliance.",
    ],
}

class Query(BaseModel):
    text: str = Field(..., min_length=3, max_length=5000, description="Incident narrative in plain English")


def load_incidents() -> pd.DataFrame:
    if not DATA_FILE.exists():
        return pd.DataFrame(columns=["incident_id", "narrative", "target_category", "target_severity"])
    df = pd.read_csv(DATA_FILE).fillna("")
    required = {"incident_id", "narrative", "target_category", "target_severity"}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"Dataset is missing required columns: {sorted(missing)}")
    return df


def phrase_score(text: str, phrases: List[str]) -> int:
    return sum(2 if " " in p and p in text else 1 for p in phrases if p in text)


def classify_category(text: str):
    normalized = re.sub(r"[^a-z0-9\s-]", " ", text.lower())
    scores = {category: phrase_score(normalized, phrases) for category, phrases in CATEGORY_RULES.items()}
    # Some domain phrases are more specific than individual generic words.
    if "waste segregation" in normalized:
        scores["esg_compliance"] += 3
    if "oil seepage" in normalized or "oil spill" in normalized:
        scores["environment"] += 3
    if "near miss" in normalized or "ppe" in normalized or "injury" in normalized:
        scores["safety"] += 2
    winner = max(scores, key=scores.get)
    if scores[winner] == 0:
        return "esg_compliance", 0.20, scores, "No strong category phrases found; defaulted to compliance review."
    total = sum(scores.values()) or 1
    confidence = min(0.95, 0.50 + scores[winner] / (2 * total))
    reason = f"Matched domain phrases for {winner.replace('_', ' ')}; rule scores: {scores}."
    return winner, round(confidence, 2), scores, reason


def classify_severity(text: str):
    normalized = re.sub(r"[^a-z0-9\s-]", " ", text.lower())
    scores = {level: phrase_score(normalized, phrases) for level, phrases in SEVERITY_RULES.items()}
    if scores["high"]:
        level = "high"
        reason = "Potentially serious hazard or high-risk event phrase detected; verify with the site safety lead."
    elif scores["medium"]:
        level = "medium"
        reason = "A reportable operational issue or moderate-risk indicator was detected."
    elif scores["low"]:
        level = "low"
        reason = "The narrative contains a lower-risk compliance/housekeeping indicator and no high-risk trigger."
    else:
        level = "medium"
        reason = "Insufficient detail for reliable severity; medium is a provisional triage value pending human review."
    return level, reason, scores


def make_summary(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "No incident narrative provided."
    # Extractive summary: preserve original facts rather than inventing new ones.
    first = re.split(r"(?<=[.!?])\s+", cleaned)[0]
    words = first.split()
    if len(words) > 28:
        first = " ".join(words[:28]) + "…"
    return first[0].upper() + first[1:] if first else cleaned


def related_examples(text: str, limit: int = 3):
    df = load_incidents()
    if df.empty:
        return []
    words = set(re.findall(r"[a-z]{3,}", text.lower()))
    stop = {"the", "and", "near", "with", "during", "area", "observed", "reported", "was", "were", "from", "into", "this", "that"}
    words -= stop
    ranked = []
    for _, row in df.iterrows():
        candidate_words = set(re.findall(r"[a-z]{3,}", str(row["narrative"]).lower())) - stop
        overlap = len(words & candidate_words)
        if overlap:
            ranked.append((overlap / max(1, len(words | candidate_words)), row))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [{"incident_id": str(row["incident_id"]), "narrative": str(row["narrative"]),
             "category": str(row["target_category"]), "severity": str(row["target_severity"]),
             "similarity": round(score, 2)} for score, row in ranked[:limit]]


def analyze(text: str):
    category, confidence, category_scores, category_reason = classify_category(text)
    severity, severity_reason, severity_scores = classify_severity(text)
    evidence = related_examples(text)
    return {
        "input": text,
        "category": category,
        "category_confidence": confidence,
        "category_scores": category_scores,
        "category_reason": category_reason,
        "severity": severity,
        "severity_reason": severity_reason,
        "severity_scores": severity_scores,
        "summary": make_summary(text),
        "recommended_actions": ACTIONS[category],
        "retrieved_examples": evidence,
        "method": "Explainable phrase rules + local lexical-overlap retrieval + extractive summarization",
        "limitations": [
            "The bundled dataset contains only six dummy examples; predictions are a prototype, not production-grade ML.",
            "Rule-based confidence is a heuristic, not a statistically calibrated probability.",
            "Severity is provisional and must be reviewed by qualified site personnel.",
            "Time-based and site-based trends cannot be calculated because dates and site IDs are absent.",
        ],
    }


def dashboard_data():
    df = load_incidents()
    total = len(df)
    cat_counts = df["target_category"].value_counts().to_dict() if total else {}
    sev_counts = df["target_severity"].value_counts().to_dict() if total else {}
    incidents = []
    for _, row in df.iterrows():
        result = analyze(str(row["narrative"]))
        incidents.append({
            "incident_id": str(row["incident_id"]), "narrative": str(row["narrative"]),
            "target_category": str(row["target_category"]), "predicted_category": result["category"],
            "target_severity": str(row["target_severity"]), "predicted_severity": result["severity"],
            "summary": result["summary"], "recommended_actions": result["recommended_actions"][:1],
        })
    high_count = sum(1 for x in incidents if x["predicted_severity"] == "high")
    predicted_severity_counts = dict(Counter(x["predicted_severity"] for x in incidents))
    return {"total_incidents": total, "category_counts": cat_counts, "severity_counts": predicted_severity_counts,
            "high_severity_count": high_count, "incidents": incidents,
            "data_note": "Counts describe the bundled dummy dataset, not live company operations."}


@app.get("/api/health")
def health():
    return {"status": "ok", "dataset_available": DATA_FILE.exists(), "version": app.version}

@app.get("/api/demo")
def demo():
    return {"case_study": "ESG / Safety Incident Intelligence Dashboard", "status": "running",
            "expected_outcome": "Analyze incident narratives, tag category/severity, summarize, retrieve similar examples, and surface recurring themes."}

@app.get("/api/dashboard")
def dashboard():
    return dashboard_data()

@app.get("/api/incidents")
def incidents():
    return dashboard_data()["incidents"]

@app.get("/api/trends")
def trends():
    df = load_incidents()
    if df.empty:
        return {"category_counts": {}, "severity_counts": {}, "themes": [], "note": "No records found."}
    all_text = " ".join(df["narrative"].astype(str).str.lower().tolist())
    theme_phrases = ["PPE", "near miss", "leakage", "oil seepage", "water usage", "waste segregation", "housekeeping", "vehicle movement"]
    themes = []
    for phrase in theme_phrases:
        count = sum(1 for narrative in df["narrative"].astype(str) if phrase.lower() in narrative.lower())
        if count:
            themes.append({"theme": phrase, "count": count})
    themes.sort(key=lambda x: x["count"], reverse=True)
    return {"category_counts": df["target_category"].value_counts().to_dict(),
            "severity_counts": df["target_severity"].value_counts().to_dict(), "themes": themes,
            "note": "Theme counts use exact phrase matches in six dummy records. No dates or site identifiers are available, so these are not time-series trends."}

@app.get("/api/evaluation")
def evaluation():
    df = load_incidents()
    if df.empty:
        return {"sample_size": 0, "category_accuracy": None, "severity_accuracy": None, "note": "No labeled rows available."}
    cat_correct, sev_correct = 0, 0
    details = []
    for _, row in df.iterrows():
        result = analyze(str(row["narrative"]))
        cat_ok = result["category"] == row["target_category"]
        sev_ok = result["severity"] == row["target_severity"]
        cat_correct += int(cat_ok); sev_correct += int(sev_ok)
        details.append({"incident_id": row["incident_id"], "category_expected": row["target_category"],
                        "category_predicted": result["category"], "category_correct": cat_ok,
                        "severity_expected": row["target_severity"], "severity_predicted": result["severity"],
                        "severity_correct": sev_ok})
    return {"sample_size": len(df), "category_accuracy_on_reference_examples": round(cat_correct / len(df), 3),
            "severity_accuracy_on_reference_examples": round(sev_correct / len(df), 3),
            "warning": "These are in-sample checks on six supplied dummy examples, not an independent test set and not evidence of real-world generalization.",
            "details": details}

@app.post("/api/run")
def run_case(query: Query):
    text = query.text.strip()
    if len(text) < 3:
        raise HTTPException(status_code=422, detail="Please provide an incident description of at least 3 characters.")
    return analyze(text)

@app.get("/", include_in_schema=False)
def home():
    if not FRONTEND_FILE.exists():
        raise HTTPException(status_code=404, detail="Frontend file not found")
    return FileResponse(FRONTEND_FILE)

@app.get("/case-study", include_in_schema=False)
def case_study():
    path = BASE / "case_study.html"
    return FileResponse(path) if path.exists() else {"detail": "Case study page not found"}
