from scripts.chatbot import (
    search_structured,
    rerank_results,
    deduplicate_results
)

from sklearn.metrics import precision_score, recall_score, f1_score
import pandas as pd

test_cases = [
    {
        "query": "punishment for murder",
        "expected_act": "BNS",
        "expected_section": "109"
    },
    {
        "query": "punishment for theft",
        "expected_act": "BNS",
        "expected_section": "303"
    },
    {
        "query": "punishment for rape",
        "expected_act": "BNS",
        "expected_section": "65"
    },
    {
        "query": "drunk driving punishment",
        "expected_act": "MVD", 
        "expected_section": "185"
    },

    {
        "query": "punishment for robbery",
        "expected_act": "BNS",
        "expected_section": "309"
    },
    {
        "query": "punishment for kidnapping",
        "expected_act": "BNS",
        "expected_section": "137"
    },
    {
        "query": "punishment for grievous hurt",
        "expected_act": "BNS",
        "expected_section": "117"
    }
]

results = []

y_true = []
y_pred = []

top1_correct = 0
top3_correct = 0
top5_correct = 0


for case in test_cases:
    query = case["query"]
    expected_act = case["expected_act"]
    expected_section = case["expected_section"]

    structured_results = search_structured(query, top_k=20)
    ranked_results = rerank_results(query, structured_results)
    ranked_results = deduplicate_results(ranked_results)

    predicted_act = None
    predicted_section = None

    if ranked_results:
        top_result = ranked_results[0]
        predicted_act = str(top_result.get("act", "")).strip()
        predicted_section = str(top_result.get("section", "")).strip()

    is_top1_correct = (
        predicted_act == expected_act
        and predicted_section == expected_section
    )

    if is_top1_correct:
        top1_correct += 1

    top3_results = ranked_results[:3]
    found_in_top3 = any(
        str(r.get("act", "")).strip() == expected_act
        and str(r.get("section", "")).strip() == expected_section
        for r in top3_results
    )

    if found_in_top3:
        top3_correct += 1

    top5_results = ranked_results[:5]
    found_in_top5 = any(
        str(r.get("act", "")).strip() == expected_act
        and str(r.get("section", "")).strip() == expected_section
        for r in top5_results
    )

    if found_in_top5:
        top5_correct += 1

    y_true.append(1)
    y_pred.append(1 if is_top1_correct else 0)

    results.append({
        "Query": query,
        "Expected Act": expected_act,
        "Expected Section": expected_section,
        "Predicted Act": predicted_act,
        "Predicted Section": predicted_section,
        "Top1 Correct": is_top1_correct,
        "Found in Top3": found_in_top3,
        "Found in Top5": found_in_top5
    })

top1_accuracy = top1_correct / len(test_cases)
top3_accuracy = top3_correct / len(test_cases)
top5_accuracy = top5_correct / len(test_cases)

precision = precision_score(y_true, y_pred, zero_division=0)
recall = recall_score(y_true, y_pred, zero_division=0)
f1 = f1_score(y_true, y_pred, zero_division=0)

results_df = pd.DataFrame(results)

print("=" * 100)
print("LAWBOT EVALUATION RESULTS")
print("=" * 100)

print(results_df.to_string(index=False))

print("\n" + "=" * 100)
print("METRICS")
print("=" * 100)

print(f"Top-1 Accuracy : {top1_accuracy:.2%}")
print(f"Top-3 Accuracy : {top3_accuracy:.2%}")
print(f"Top-5 Accuracy : {top5_accuracy:.2%}")
print(f"Precision      : {precision:.2f}")
print(f"Recall         : {recall:.2f}")
print(f"F1 Score       : {f1:.2f}")