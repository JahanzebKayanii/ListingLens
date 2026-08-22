# ListingLens

A tool that helps recruiters write better job postings. Paste in a job
description and get:

- **Performance prediction** - is this posting likely to underperform (few
  views/applicants) based on patterns learned from real postings, with a
  SHAP explanation of *why*.
- **Bias language detection** - flags masculine/feminine-coded language
  known (via published research) to skew applicant pools.
- **Readability score** - Flesch-Kincaid grade level, so postings aren't
  needlessly dense.
- **Market benchmarking** - how this posting's salary, requirements, and
  skill list compare to similar real postings, filterable by industry and
  experience level.

## Data

Built on the [LinkedIn Job Postings dataset](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings)
(Kaggle, CC-BY-SA-4.0). The raw dump isn't checked into this repo (too
large, and datasets don't belong in git history) - to regenerate:

```
kaggle datasets download -d arshkon/linkedin-job-postings -p data --unzip
python src/prepare_data.py
```

## Setup

```
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Running

```
streamlit run src/app.py
```
