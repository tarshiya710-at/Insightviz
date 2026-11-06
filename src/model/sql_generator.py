
import sys
import json
from pathlib import Path

# Add project folders to Python path
ROOT = Path(__file__).resolve().parents[2]

sys.path.append(str(ROOT / "src" / "database"))
sys.path.append(str(ROOT / "src" / "model"))

from schema_reader import get_schema
from model_loader import load_model


def generate_sql(question, model, tokenizer):

    # Get actual database schema
    schema = get_schema()

    schema_text = json.dumps(schema, indent=2)

    # Create schema-aware prompt
    prompt = f"""
You are an expert MySQL query generator.

Database schema:
{schema_text}

User question:
{question}

Generate only a valid MySQL SELECT query.
Do not explain the query.

SQL:
"""

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    ).to("cuda")

    outputs = model.generate(
        **inputs,
        max_new_tokens=150,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id
    )

    # Extract only newly generated text
    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]

    sql = tokenizer.decode(
        new_tokens,
        skip_special_tokens=True
    )

    return sql.strip()


if __name__ == "__main__":

    model, tokenizer = load_model()

    question = "Show total sales for each product category."

    result = generate_sql(question, model, tokenizer)

    print("\nGenerated SQL:")
    print(result)
