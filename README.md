# ListingLens

A tool that helps recruiters write better job postings. Paste in a job
description and get:

- **Performance prediction** - is this posting likely to underperform (low
  application conversion rate) relative to similar postings, based on
  patterns learned from real data, with a SHAP explanation of *why*.
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

## A note on the model / target choice

The obvious first target was raw view count, but checking correlations
before modeling showed it was a poor choice: views happen when LinkedIn
surfaces a posting in a feed/search, *before* anyone has read the
description, so text-quality features (readability, bias language,
skill clarity) have no causal path to influence them - and the
correlations bore that out (all near zero).

Application **conversion rate** (applies / views) is better-motivated:
applying requires reading the posting first, so text quality can
plausibly drive it. Correlation checks confirmed real (if modest) signal
here - e.g. `description_length` correlates -0.18 with conversion rate,
and masculine-coded language correlates -0.10, directly validating the
bias-detection feature. The model predicts relative underperformance
(bottom 25% of conversion rate within a posting's industry + experience
peer group) with a modest but real AUC (~0.56-0.59) - consistent with the
underlying correlations, and reported honestly rather than tuned to look
stronger than the signal actually supports.

## Setup

```
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Running

Two ways to run this - pick one.

**Streamlit** (quick, self-contained, one process):
```
cd src
streamlit run app.py
```

**FastAPI + React** (the "proper" full-stack version - separate backend/frontend):
```
# terminal 1 - backend
cd src
uvicorn api:app --reload --port 8000

# terminal 2 - frontend
cd frontend
npm install
npm run dev
```
Then open `http://localhost:5173`. Interactive API docs at `http://localhost:8000/docs`.

Both versions share the same underlying logic (`features.py`, `benchmark.py`,
the trained model) - they're just two different UIs on top of it.
