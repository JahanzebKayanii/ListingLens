"""
ListingLens - Streamlit dashboard. Recruiter pastes a job posting, picks
a few context toggles (industry, experience level, work type, remote,
salary), and gets: predicted underperformance risk (with SHAP explanation),
bias-language flags, a readability score, and market benchmarking against
similar real postings.
"""

import json
import pandas as pd
import streamlit as st
import xgboost as xgb
import shap
import plotly.graph_objects as go

from features import extract_skills, readability_grade, readability_ease, bias_language_score
from benchmark import load_features, filter_pool, benchmark_posting

MODEL_PATH = "../models/underperform_model.json"
ENCODERS_PATH = "../models/encoders.json"

FEATURE_COLS = [
    "skill_count", "readability_grade", "readability_ease", "bias_lean_score",
    "masculine_count", "feminine_count", "description_length", "has_salary",
    "remote_allowed", "experience_level_enc", "work_type_enc", "industry_enc",
]

st.set_page_config(page_title="ListingLens", page_icon="🔍", layout="wide")


@st.cache_resource
def load_model_and_encoders():
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    with open(ENCODERS_PATH) as f:
        encoders = json.load(f)
    return model, encoders


@st.cache_data
def load_data():
    return load_features()


def encode(value, mapping):
    return mapping.get(value, mapping.get("Unknown", 0))


def annualize(salary, period):
    if salary is None or salary == 0:
        return None
    if period == "Hourly":
        return salary * 2080
    if period == "Monthly":
        return salary * 12
    return salary


st.title("🔍 ListingLens")
st.caption("Paste a job posting and see how it will actually land with candidates.")

df = load_data()
model, encoders = load_model_and_encoders()

industries = ["All"] + sorted(df["industry_name"].dropna().unique().tolist())
experience_levels = ["All"] + sorted(df["formatted_experience_level"].dropna().unique().tolist())
work_types = sorted(df["formatted_work_type"].dropna().unique().tolist())

col_left, col_right = st.columns([2, 1])

with col_left:
    posting_text = st.text_area("Job posting text", height=300,
                                 placeholder="Paste the full job description here...")

with col_right:
    st.subheader("Context")
    industry_filter = st.selectbox("Compare against industry", industries)
    experience_filter = st.selectbox("Compare against experience level", experience_levels)
    st.divider()
    st.caption("For the prediction model (not just benchmarking):")
    experience_level_input = st.selectbox("This posting's experience level", experience_levels[1:])
    work_type_input = st.selectbox("Work type", work_types)
    remote_input = st.checkbox("Remote allowed")
    salary_input = st.number_input("Salary (0 if not listing one)", min_value=0, value=0, step=1000)
    pay_period_input = st.selectbox("Pay period", ["Yearly", "Hourly", "Monthly"])

analyze = st.button("Analyze posting", type="primary", use_container_width=True)

if analyze and posting_text.strip():
    skills = extract_skills(posting_text)
    grade = readability_grade(posting_text)
    ease = readability_ease(posting_text)
    bias = bias_language_score(posting_text)
    desc_len = len(posting_text.split())
    salary_annual = annualize(salary_input, pay_period_input) if salary_input else None
    has_salary = salary_annual is not None

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Skills detected", len(skills))
    m2.metric("Readability grade", f"{grade:.1f}", help="US grade level - lower reads easier")
    m3.metric("Word count", desc_len)
    lean_label = "Masculine-leaning" if bias["lean_score"] > 0.15 else (
        "Feminine-leaning" if bias["lean_score"] < -0.15 else "Balanced")
    m4.metric("Language lean", lean_label)

    tab_predict, tab_bias, tab_bench, tab_skills = st.tabs(
        ["Performance prediction", "Bias language", "Market benchmark", "Skills found"]
    )

    with tab_predict:
        row = {
            "skill_count": len(skills),
            "readability_grade": grade,
            "readability_ease": ease,
            "bias_lean_score": bias["lean_score"],
            "masculine_count": bias["masculine_count"],
            "feminine_count": bias["feminine_count"],
            "description_length": desc_len,
            "has_salary": int(has_salary),
            "remote_allowed": int(remote_input),
            "experience_level_enc": encode(experience_level_input, encoders["formatted_experience_level"]),
            "work_type_enc": encode(work_type_input, encoders["formatted_work_type"]),
            "industry_enc": encode(industry_filter, encoders["industry_name"]),
        }
        X = pd.DataFrame([row])[FEATURE_COLS]
        risk = model.predict_proba(X)[0, 1]

        st.metric("Underperformance risk", f"{risk*100:.0f}%",
                  help="Modeled probability this posting lands in the bottom 25% of "
                       "views for its industry/experience peer group")

        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X)[0]
        contrib = pd.DataFrame({"feature": FEATURE_COLS, "impact": shap_vals}).sort_values("impact")

        fig = go.Figure(go.Bar(
            x=contrib["impact"], y=contrib["feature"], orientation="h",
            marker_color=["#d62728" if v > 0 else "#2ca02c" for v in contrib["impact"]],
        ))
        fig.update_layout(title="What's driving this prediction (red = raises risk, green = lowers it)",
                           height=400)
        st.plotly_chart(fig, use_container_width=True)

    with tab_bias:
        b1, b2 = st.columns(2)
        with b1:
            st.markdown("**Masculine-coded words found**")
            st.write(", ".join(bias["masculine_hits"]) or "None")
        with b2:
            st.markdown("**Feminine-coded words found**")
            st.write(", ".join(bias["feminine_hits"]) or "None")
        st.caption("Based on research showing agentic/masculine-coded language in job posts "
                   "correlates with fewer women applying, independent of the actual role.")

    with tab_bench:
        pool = filter_pool(df, industry=industry_filter, experience_level=experience_filter)
        st.caption(f"Comparing against {len(pool):,} similar postings")
        posting_stats = {
            "salary_annual": salary_annual,
            "skill_count": len(skills),
            "readability_grade": grade,
            "description_length": desc_len,
        }
        results = benchmark_posting(posting_stats, pool)
        for metric, res in results.items():
            if res is None:
                st.write(f"**{metric}**: not enough comparison data")
                continue
            st.write(f"**{metric}**: {res['value']} — {res['percentile']:.0f}th percentile "
                      f"(peer average: {res['group_mean']}, n={res['group_n']})")

    with tab_skills:
        st.write(", ".join(skills) or "No taxonomy skills detected")

elif analyze:
    st.warning("Paste a job posting first.")
