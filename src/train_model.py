"""
Step 3: train a model that predicts whether a posting will underperform
its peers, then explain predictions with SHAP.

Target definition: raw view counts turned out to be a poor target - views
happen when LinkedIn surfaces a posting in a feed/search, *before* anyone
has read the description, so text-quality features (readability, bias
language, clarity) have no causal path to influence them. Checking
correlations confirmed this: skill_count/description_length/bias signals
were all near-zero correlated with views.

Application CONVERSION RATE (applies / views) is the better target -
applying requires actually reading the posting first, so text quality can
plausibly drive it. Correlation checks confirmed a real signal here (e.g.
description_length: -0.18, masculine-coded language: -0.10), so we predict
RELATIVE underperformance on conversion rate - bottom 25% of apply_rate
*within the posting's industry + experience-level peer group*, which
controls for baseline differences in how competitive different roles are.
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
    group_thresholds = df.groupby(["industry_name", "formatted_experience_level"])["apply_rate"].transform(
        lambda s: s.quantile(0.25)
    )
    return (df["apply_rate"] < group_thresholds).astype(int)


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
    # need real views AND applies to compute a conversion rate
    df = df.dropna(subset=["views", "applies"])
    df = df[df["views"] > 0]
    df["apply_rate"] = df["applies"] / df["views"]
    df["has_salary"] = df["has_salary"].astype(int)
    df["remote_allowed"] = df["remote_allowed"].fillna(0).astype(int)

    df, encoders = encode_categoricals(df)
    df["target"] = make_target(df)
    print(f"Training rows (have both views and applies): {len(df):,}")
    print(f"Target balance:\n{df['target'].value_counts(normalize=True)}\n")

    X = df[FEATURE_COLS]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # class imbalance (~75/25) plus modest feature signal means an
    # unweighted model just predicts the majority class every time -
    # scale_pos_weight makes it actually discriminate
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, eval_metric="auc",
        scale_pos_weight=scale_pos_weight, random_state=42,
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
