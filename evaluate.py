"""Run a transparent in-sample sanity check on the bundled dummy dataset.

Usage: python evaluate.py
Metrics are descriptive only; six examples are not an independent test set.
"""
from backend.app import load_incidents, analyze


def main():
    df = load_incidents()
    if df.empty:
        print("No dataset rows found.")
        return
    category_correct = severity_correct = 0
    print(f"Reference rows: {len(df)}")
    print("\nPer-row results")
    print("ID    category expected -> predicted     severity expected -> predicted")
    for _, row in df.iterrows():
        result = analyze(str(row["narrative"]))
        cat_ok = result["category"] == row["target_category"]
        sev_ok = result["severity"] == row["target_severity"]
        category_correct += cat_ok
        severity_correct += sev_ok
        print(f"{row['incident_id']:<5} {row['target_category']:<16} -> {result['category']:<16} "
              f"{row['target_severity']:<8} -> {result['severity']:<8}")
    n = len(df)
    print(f"\nIn-sample category accuracy: {category_correct}/{n} = {category_correct/n:.1%}")
    print(f"In-sample severity accuracy: {severity_correct}/{n} = {severity_correct/n:.1%}")
    print("WARNING: In-sample checks on six dummy records only; do not interpret as generalization performance.")

if __name__ == "__main__":
    main()
