"""
Step 2: run feature extraction (skills, readability, bias language) over
every posting in the cleaned sample, and derive the columns the model and
benchmarking dashboard both need. Writes data/postings_features.csv.
"""

import sys
import time
import pandas as pd
from features import extract_skills_batch, readability_grade, readability_ease, bias_language_score

IN_PATH = "../data/postings_clean.csv"
OUT_PATH = "../data/postings_features.csv"

# Bound worst-case per-row cost - readability/bias/skill signal is dominated
# by the first chunk of a posting anyway, and a handful of outlier postings
# ran past 15k characters.
MAX_CHARS = 4000


def salary_midpoint(row):
    if pd.notna(row["med_salary"]):
        val = row["med_salary"]
    elif pd.notna(row["max_salary"]) and pd.notna(row["min_salary"]):
        val = (row["max_salary"] + row["min_salary"]) / 2
    elif pd.notna(row["max_salary"]):
        val = row["max_salary"]
    else:
        return None
    period = row.get("pay_period")
    if period == "HOURLY":
        return val * 2080
    if period == "MONTHLY":
        return val * 12
    return val


def main():
    df = pd.read_csv(IN_PATH)
    n = len(df)
    print(f"Extracting features for {n:,} postings...", flush=True)

    texts = df["description"].astype(str).str.slice(0, MAX_CHARS).tolist()

    t0 = time.time()
    skills_list = extract_skills_batch(texts)
    print(f"  skill extraction done in {time.time()-t0:.1f}s", flush=True)

    t0 = time.time()
    grades, eases, bias_scores = [], [], []
    for i, text in enumerate(texts):
        grades.append(readability_grade(text))
        eases.append(readability_ease(text))
        bias_scores.append(bias_language_score(text))
        if (i + 1) % 5000 == 0:
            print(f"  readability/bias: {i+1:,}/{n:,} ({time.time()-t0:.1f}s elapsed)", flush=True)
    print(f"  readability/bias done in {time.time()-t0:.1f}s", flush=True)

    df["skill_count"] = [len(s) for s in skills_list]
    df["skills_found"] = [",".join(s) for s in skills_list]
    df["readability_grade"] = grades
    df["readability_ease"] = eases
    df["bias_lean_score"] = [b["lean_score"] for b in bias_scores]
    df["masculine_count"] = [b["masculine_count"] for b in bias_scores]
    df["feminine_count"] = [b["feminine_count"] for b in bias_scores]
    df["description_length"] = [len(t.split()) for t in texts]
    df["salary_annual"] = df.apply(salary_midpoint, axis=1)
    df["has_salary"] = df["med_salary"].notna() | df["max_salary"].notna()

    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df):,} rows to {OUT_PATH}", flush=True)
    print(df[["title", "industry_name", "skill_count", "readability_grade",
               "bias_lean_score", "salary_annual", "views"]].head(10))


if __name__ == "__main__":
    main()
