"""
Market benchmarking: given a posting's stats and a comparison pool
(filtered by industry / experience level), report where it stands relative
to similar real postings. Powers the toggle-driven part of the dashboard.
"""

import pandas as pd
from scipy.stats import percentileofscore

FEATURES_PATH = "../data/postings_features.csv"

BENCHMARK_COLS = ["salary_annual", "skill_count", "readability_grade", "description_length"]


def load_features():
    return pd.read_csv(FEATURES_PATH)


def filter_pool(df, industry=None, experience_level=None):
    pool = df
    if industry and industry != "All":
        pool = pool[pool["industry_name"] == industry]
    if experience_level and experience_level != "All":
        pool = pool[pool["formatted_experience_level"] == experience_level]
    return pool


def benchmark_posting(posting_stats, pool):
    """
    posting_stats: dict with the same keys as BENCHMARK_COLS, computed for
    the posting being analyzed.
    pool: the comparison DataFrame (already filtered by industry/experience).
    Returns per-metric percentile rank + group mean/std for context.
    """
    results = {}
    for col in BENCHMARK_COLS:
        values = pool[col].dropna()
        if len(values) < 5 or col not in posting_stats or posting_stats[col] is None:
            results[col] = None
            continue
        pct = percentileofscore(values, posting_stats[col])
        results[col] = {
            "value": posting_stats[col],
            "percentile": round(pct, 1),
            "group_mean": round(values.mean(), 2),
            "group_std": round(values.std(), 2),
            "group_n": len(values),
        }
    return results


if __name__ == "__main__":
    df = load_features()
    pool = filter_pool(df, industry="Software Development", experience_level="Entry level")
    print(f"Pool size: {len(pool)}")
    example = {
        "salary_annual": 65000,
        "skill_count": 3,
        "readability_grade": 12.0,
        "description_length": 250,
    }
    result = benchmark_posting(example, pool)
    for k, v in result.items():
        print(k, "->", v)
