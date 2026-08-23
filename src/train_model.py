"""
Step 3: train a model that predicts whether a posting will underperform
its peers, then explain predictions with SHAP.

Target definition: rather than predicting raw view counts (noisy - depends
heavily on how long a posting has been live, how popular the industry is,
etc.), we predict RELATIVE underperformance - is this posting in the bottom
25% of views *within its own industry + experience-level peer group*. That
controls for the biggest confounders and keeps the target meaningful across
very different kinds of roles.
"""

import json
import pandas as pd
import xgboost as xgb
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.preprocessing import LabelEncoder

FEATURES_PATH = "../data/postings_features.csv"
MODEL_PATH = "../models/underperform_model.json"
ENCODERS_PATH = "../models/encoders.json"

FEATURE_COLS = [
    "skill_count", "readability_grade", "readability_ease", "bias_lean_score",
    "masculine_count", "feminine_count", "description_length", "has_salary",
    "remote_allowed", "experience_level_enc", "work_type_enc", "industry_enc",
]


def make_target(df):
    group_medians = df.groupby(["industry_name", "formatted_experience_level"])["views"].transform(
        lambda s: s.quantile(0.25)
    )
    return (df["views"] < group_medians).astype(int)


def encode_categoricals(df):
    encoders = {}
    for col, out_col in [
        ("formatted_experience_level", "experience_level_enc"),
        ("formatted_work_type", "work_type_enc"),
        ("industry_name", "industry_enc"),
    ]:
        df[col] = df[col].fillna("Unknown")
        le = LabelEncoder()
        df[out_col] = le.fit_transform(df[col])
        encoders[col] = {cls: int(i) for i, cls in enumerate(le.classes_)}
    return df, encoders


def main():
    df = pd.read_csv(FEATURES_PATH)
    df = df.dropna(subset=["views"])
    df["has_salary"] = df["has_salary"].astype(int)
    df["remote_allowed"] = df["remote_allowed"].fillna(0).astype(int)

    df, encoders = encode_categoricals(df)
    df["target"] = make_target(df)

    X = df[FEATURE_COLS]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, eval_metric="auc",
        random_state=42,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    print(f"Test AUC: {roc_auc_score(y_test, probs):.3f}")
    print(classification_report(y_test, preds))

    model.save_model(MODEL_PATH)
    with open(ENCODERS_PATH, "w") as f:
        json.dump(encoders, f, indent=2)
    print(f"Saved model to {MODEL_PATH} and encoders to {ENCODERS_PATH}")

    # sanity-check SHAP explains a single prediction end to end
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test.iloc[[0]])
    print("\nSHAP values for one example prediction:")
    for feat, val in zip(FEATURE_COLS, shap_values[0]):
        print(f"  {feat}: {val:+.4f}")


if __name__ == "__main__":
    main()
