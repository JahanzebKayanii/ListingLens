"""
Step 1: build a clean, manageable working dataset from the raw Kaggle
LinkedIn Job Postings dump (postings.csv is 3.38M rows / 516MB - way more
than we need for a benchmarking + modeling project).

What this does:
  1. Streams postings.csv in chunks (too big to load at once) and keeps
     only rows with a real description and either a salary or a view count
     (rows missing both aren't useful for our features).
  2. Randomly samples down to SAMPLE_SIZE rows.
  3. Joins in the primary industry per job (job_industries.csv -> industries.csv)
     so we have a real industry_name column for benchmarking.
  4. Writes the result to data/postings_clean.csv.
"""

import pandas as pd

DATA_DIR = "../data"
RAW_POSTINGS = f"{DATA_DIR}/postings.csv"
JOB_INDUSTRIES = f"{DATA_DIR}/jobs/job_industries.csv"
INDUSTRIES = f"{DATA_DIR}/mappings/industries.csv"
OUT_PATH = f"{DATA_DIR}/postings_clean.csv"

SAMPLE_SIZE = 25_000
RANDOM_SEED = 42

KEEP_COLS = [
    "job_id", "title", "description", "company_name", "location",
    "formatted_experience_level", "formatted_work_type", "remote_allowed",
    "views", "applies", "max_salary", "med_salary", "min_salary",
    "pay_period", "listed_time",
]


def load_filtered_postings():
    chunks = []
    reader = pd.read_csv(RAW_POSTINGS, usecols=KEEP_COLS, chunksize=100_000)
    for chunk in reader:
        chunk = chunk.dropna(subset=["description"])
        has_salary = chunk["max_salary"].notna() | chunk["med_salary"].notna()
        has_views = chunk["views"].notna() & (chunk["views"] > 0)
        chunk = chunk[has_salary | has_views]
        if len(chunk):
            chunks.append(chunk)
    return pd.concat(chunks, ignore_index=True)


def attach_primary_industry(df):
    job_ind = pd.read_csv(JOB_INDUSTRIES)
    industries = pd.read_csv(INDUSTRIES)
    job_ind = job_ind.merge(industries, on="industry_id", how="left")
    # a job can map to multiple industries; keep the first listed as "primary"
    primary = job_ind.drop_duplicates(subset="job_id", keep="first")[["job_id", "industry_name"]]
    return df.merge(primary, on="job_id", how="left")


def main():
    print("Streaming and filtering postings.csv (this may take a minute)...")
    df = load_filtered_postings()
    print(f"Rows after filtering (has description + salary/views): {len(df):,}")

    if len(df) > SAMPLE_SIZE:
        df = df.sample(n=SAMPLE_SIZE, random_state=RANDOM_SEED)
    print(f"Rows after sampling: {len(df):,}")

    print("Attaching primary industry per job...")
    df = attach_primary_industry(df)
    df["industry_name"] = df["industry_name"].fillna("Unknown")

    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df):,} rows to {OUT_PATH}")
    print(df[["title", "industry_name", "formatted_experience_level", "max_salary", "views"]].head())


if __name__ == "__main__":
    main()
