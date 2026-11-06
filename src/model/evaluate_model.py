
import csv
from pathlib import Path

from model_loader import load_model
from test_questions import test_questions

print("Loading model...")
model, tokenizer = load_model()

results = []

for i, item in enumerate(test_questions, start=1):

    question = item["question"]

    prompt = f"""Generate only SQL for this question:
{question}
SQL:"""

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

    outputs = model.generate(
        **inputs,
        max_new_tokens=150,
        do_sample=False
    )

    generated_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    sql = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True
    ).strip()

    results.append({
        "scenario": item["scenario"],
        "concept": item["concept"],
        "question": question,
        "generated_sql": sql
    })

    print(f"Completed {i}/{len(test_questions)}")

# Save results
output_file = Path(__file__).resolve().parents[2] / "evaluation_results.csv"

with open(output_file, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print("\nEvaluation completed!")
print("Results saved to:", output_file)
