"""
ListingLens API - FastAPI backend for the React frontend. Same analysis
logic as app.py (Streamlit), just exposed over HTTP instead of rendered
directly. features.py/benchmark.py/the trained model are shared by both.
"""

import json
import pandas as pd
import xgboost as xgb
import shap
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from features import extract_skills, readability_grade, readability_ease, bias_language_score
from benchmark import load_features, filter_pool, benchmark_posting
from schemas import AnalyzeRequest, AnalyzeResponse, MetadataResponse, BiasResult, PredictionResult, ShapContribution, BenchmarkMetric

MODEL_PATH = "../models/underperform_model.json"
ENCODERS_PATH = "../models/encoders.json"

FEATURE_COLS = [
    "skill_count", "readability_grade", "readability_ease", "bias_lean_score",
    "masculine_count", "feminine_count", "description_length", "has_salary",
    "remote_allowed", "experience_level_enc", "work_type_enc", "industry_enc",
]

app = FastAPI(title="ListingLens API")

# local dev only - tighten this before ever deploying publicly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_model = xgb.XGBClassifier()
_model.load_model(MODEL_PATH)
with open(ENCODERS_PATH) as f:
    _encoders = json.load(f)
_explainer = shap.TreeExplainer(_model)
_df = load_features()


def _encode(value, mapping):
    return mapping.get(value, mapping.get("Unknown", 0))


def _annualize(salary, period):
    if salary is None or salary == 0:
        return None
    if period == "Hourly":
        return salary * 2080
    if period == "Monthly":
        return salary * 12
    return salary


@app.get("/metadata", response_model=MetadataResponse)
def get_metadata():
    return MetadataResponse(
        industries=["All"] + sorted(_df["industry_name"].dropna().unique().tolist()),
        experience_levels=["All"] + sorted(_df["formatted_experience_level"].dropna().unique().tolist()),
        work_types=sorted(_df["formatted_work_type"].dropna().unique().tolist()),
    )


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    skills = extract_skills(req.text)
    grade = readability_grade(req.text)
    ease = readability_ease(req.text)
    bias = bias_language_score(req.text)
    word_count = len(req.text.split())
    salary_annual = _annualize(req.salary, req.pay_period)
    has_salary = salary_annual is not None

    lean_label = "Masculine-leaning" if bias["lean_score"] > 0.15 else (
        "Feminine-leaning" if bias["lean_score"] < -0.15 else "Balanced")

    row = {
        "skill_count": len(skills),
        "readability_grade": grade,
        "readability_ease": ease,
        "bias_lean_score": bias["lean_score"],
        "masculine_count": bias["masculine_count"],
        "feminine_count": bias["feminine_count"],
        "description_length": word_count,
        "has_salary": int(has_salary),
        "remote_allowed": int(req.remote_allowed),
        "experience_level_enc": _encode(req.experience_level, _encoders["formatted_experience_level"]),
        "work_type_enc": _encode(req.work_type, _encoders["formatted_work_type"]),
        "industry_enc": _encode(req.benchmark_industry, _encoders["industry_name"]),
    }
    X = pd.DataFrame([row])[FEATURE_COLS]
    risk = float(_model.predict_proba(X)[0, 1])
    shap_vals = _explainer.shap_values(X)[0]
    contributions = [
        ShapContribution(feature=feat, impact=float(val))
        for feat, val in sorted(zip(FEATURE_COLS, shap_vals), key=lambda t: t[1])
    ]

    pool = filter_pool(_df, industry=req.benchmark_industry, experience_level=req.benchmark_experience)
    posting_stats = {
        "salary_annual": salary_annual,
        "skill_count": len(skills),
        "readability_grade": grade,
        "description_length": word_count,
    }
    raw_bench = benchmark_posting(posting_stats, pool)
    benchmark = {
        k: (BenchmarkMetric(**v) if v is not None else None)
        for k, v in raw_bench.items()
    }

    return AnalyzeResponse(
        skills=skills,
        readability_grade=grade,
        readability_ease=ease,
        word_count=word_count,
        bias=BiasResult(
            masculine_hits=bias["masculine_hits"],
            feminine_hits=bias["feminine_hits"],
            masculine_count=bias["masculine_count"],
            feminine_count=bias["feminine_count"],
            lean_score=bias["lean_score"],
            lean_label=lean_label,
        ),
        prediction=PredictionResult(risk=risk, contributions=contributions),
        benchmark=benchmark,
    )
