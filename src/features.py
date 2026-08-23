"""
Turns raw job posting text into the numeric/structured features the rest
of the app relies on: skills mentioned, readability, and gendered-language
signal. Nothing here needs the trained model - it's pure feature extraction,
reusable by both the training pipeline and the live app.
"""

import re
import spacy
import textstat
from spacy.matcher import PhraseMatcher

nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer", "tagger"])

# A curated skills taxonomy covering common technical + business/soft skills
# seen across tech, data, and business-function job postings. Not exhaustive -
# a real product would pull from a maintained taxonomy (e.g. ESCO, O*NET),
# but this is enough breadth to demonstrate the extraction approach.
SKILLS = [
    # programming / data
    "python", "sql", "r", "java", "javascript", "typescript", "c++", "c#",
    "scala", "go", "rust", "excel", "tableau", "power bi", "looker",
    "spark", "hadoop", "airflow", "dbt", "snowflake", "redshift", "bigquery",
    "postgresql", "mysql", "mongodb", "pandas", "numpy", "scikit-learn",
    "tensorflow", "pytorch", "machine learning", "deep learning", "nlp",
    "computer vision", "statistics", "a/b testing", "etl", "data pipeline",
    "data visualization", "git", "docker", "kubernetes", "aws", "azure",
    "gcp", "rest api", "ci/cd",
    # business / soft skills
    "project management", "stakeholder management", "communication",
    "leadership", "problem solving", "critical thinking", "teamwork",
    "collaboration", "time management", "presentation", "negotiation",
    "customer service", "sales", "marketing", "budgeting", "forecasting",
    "strategic planning", "cross-functional", "agile", "scrum",
    "public speaking", "mentoring", "adaptability", "attention to detail",
]

_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
_matcher.add("SKILL", [nlp.make_doc(s) for s in SKILLS])


def extract_skills(text):
    """Return the set of taxonomy skills mentioned in the posting text."""
    doc = nlp(text)
    matches = _matcher(doc)
    found = {doc[start:end].text.lower() for _, start, end in matches}
    return sorted(found)


def extract_skills_batch(texts, batch_size=200):
    """
    Same as extract_skills but processes many texts through spaCy's
    pipe() batching instead of one nlp() call per text - much faster for
    bulk jobs (building the training set) than calling extract_skills in
    a loop.
    """
    results = []
    for doc in nlp.pipe(texts, batch_size=batch_size):
        matches = _matcher(doc)
        found = {doc[start:end].text.lower() for _, start, end in matches}
        results.append(sorted(found))
    return results


def readability_grade(text):
    """Flesch-Kincaid grade level - lower is easier to read."""
    return textstat.flesch_kincaid_grade(text)


def readability_ease(text):
    """Flesch Reading Ease, 0-100 - higher is easier to read."""
    return textstat.flesch_reading_ease(text)


# Word lists reflecting the kind of agentic ("masculine-coded") vs communal
# ("feminine-coded") language studied in Gaucher, Friesen & Kay (2011),
# "Evidence That Gendered Wording in Job Advertisements Exists and Sustains
# Gender Inequality" - agentic-coded postings correlate with fewer women
# applying, independent of the actual job content. This is a representative
# lexicon in that spirit, not a verbatim reproduction of their exact list.
MASCULINE_CODED = [
    "active", "adventurous", "aggressive", "ambitious", "analytical",
    "assertive", "autonomous", "challenging", "competitive", "confident",
    "courageous", "decisive", "determined", "dominant", "driven",
    "fearless", "independent", "individualistic", "leader", "logic",
    "objective", "outspoken", "persistent", "self-reliant", "stubborn",
    "superior", "rockstar", "ninja", "guru", "hustle", "grind",
]

FEMININE_CODED = [
    "affectionate", "collaborative", "committed", "compassionate",
    "considerate", "cooperative", "dependable", "empathetic", "gentle",
    "honest", "interpersonal", "kind", "loyal", "nurturing", "pleasant",
    "polite", "supportive", "sympathetic", "trustworthy", "understanding",
    "warm", "inclusive", "team-oriented", "flexible", "patient",
]

_masc_pattern = re.compile(r"\b(" + "|".join(re.escape(w) for w in MASCULINE_CODED) + r")\w*\b", re.IGNORECASE)
_fem_pattern = re.compile(r"\b(" + "|".join(re.escape(w) for w in FEMININE_CODED) + r")\w*\b", re.IGNORECASE)


def bias_language_score(text):
    """
    Counts masculine- and feminine-coded word hits and returns a simple
    lean score: positive = skews masculine-coded, negative = skews
    feminine-coded, near zero = balanced. Also returns the matched words
    so the UI can show *why*, not just a number.
    """
    masc_hits = _masc_pattern.findall(text)
    fem_hits = _fem_pattern.findall(text)
    total = len(masc_hits) + len(fem_hits)
    lean = 0.0 if total == 0 else (len(masc_hits) - len(fem_hits)) / total
    return {
        "masculine_hits": sorted(set(w.lower() for w in masc_hits)),
        "feminine_hits": sorted(set(w.lower() for w in fem_hits)),
        "masculine_count": len(masc_hits),
        "feminine_count": len(fem_hits),
        "lean_score": round(lean, 3),
    }


if __name__ == "__main__":
    sample = """
    We're looking for a driven, competitive rockstar Data Analyst who can
    dominate ambiguous problems independently. You'll need Python, SQL,
    and strong stakeholder management skills. Must be a collaborative
    team player who is also aggressive about deadlines.
    """
    print("Skills found:", extract_skills(sample))
    print("Grade level:", readability_grade(sample))
    print("Reading ease:", readability_ease(sample))
    print("Bias score:", bias_language_score(sample))
