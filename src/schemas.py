"""Pydantic request/response models for the FastAPI backend."""

from typing import Optional
from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    text: str
    # comparison pool for benchmarking (can be "All")
    benchmark_industry: str = "All"
    benchmark_experience: str = "All"
    # this posting's own attributes, used for the prediction model
    experience_level: str
    work_type: str
    remote_allowed: bool = False
    salary: Optional[float] = None
    pay_period: str = "Yearly"  # Yearly | Hourly | Monthly


class BiasResult(BaseModel):
    masculine_hits: list[str]
    feminine_hits: list[str]
    masculine_count: int
    feminine_count: int
    lean_score: float
    lean_label: str


class ShapContribution(BaseModel):
    feature: str
    impact: float


class PredictionResult(BaseModel):
    risk: float
    contributions: list[ShapContribution]


class BenchmarkMetric(BaseModel):
    value: float
    percentile: float
    group_mean: float
    group_std: float
    group_n: int


class AnalyzeResponse(BaseModel):
    skills: list[str]
    readability_grade: float
    readability_ease: float
    word_count: int
    bias: BiasResult
    prediction: PredictionResult
    benchmark: dict[str, Optional[BenchmarkMetric]]


class MetadataResponse(BaseModel):
    industries: list[str]
    experience_levels: list[str]
    work_types: list[str]
