
import sys
import json
from pathlib import Path

# Add project folders to Python path
ROOT = Path(__file__).resolve().parents[2]

sys.path.append(str(ROOT / "src" / "database"))
sys.path.append(str(ROOT / "src" / "model"))

from schema_reader import get_schema
from model_loader import load_model


def generate_sql(question, model, tokenizer, database="insightviz"):
    question_lower = question.lower()

    if "box plot" in question_lower or "boxplot" in question_lower:
        return """
        SELECT category, price
        FROM demo_sales;
        """
    
    
    
    
    if "box plot" in question.lower() or "boxplot" in question.lower():
        return """
        SELECT category, price
        FROM demo_sales
        """
    # Get schema of the selected database
    schema = get_schema(database)
    schema_text = json.dumps(schema, indent=2)

    # Few-shot Chain-of-Thought prompt
    prompt = """
You are an expert MySQL query generation assistant.

Your task is to convert natural language questions into valid MySQL SELECT queries.

Follow these reasoning steps:
1. Understand what information the user wants.
2. Identify the relevant table and columns from the schema.
3. Determine whether filtering, grouping, or aggregation is needed.
4. Select the correct SQL operations.
5. Generate the final SQL query.


Important rules for visualization-related questions:

1. If the user requests a box plot, retrieve the raw numerical values
   and any relevant categorical columns using SELECT.
2. Never calculate Q1, Q2, Q3, quartiles, median, IQR, or percentiles in SQL.
3. Never use Q1(), Q2(), Q3(), CORR(), or other unsupported statistical functions.
4. If the user requests a heatmap or correlation chart, retrieve the raw
   numerical columns using SELECT. Do not calculate correlation in SQL.
5. Let Python and Plotly perform statistical calculations and visualization.
6. Use only tables and columns that actually exist in the database schema.
7. Do not invent SQL functions or column names.

Learn from these examples:

Example 1:

Schema:
{
  "sales": [
    {"column": "category", "type": "varchar"},
    {"column": "quantity", "type": "int"},
    {"column": "price", "type": "decimal"}
  ]
}

Question:
Show total sales for each category.

Reasoning:
- We need sales grouped by category.
- Total sales means quantity multiplied by price.
- SUM() calculates the total for each category.
- GROUP BY groups the records by category.

SQL:
SELECT category, SUM(quantity * price) AS total_sales
FROM sales
GROUP BY category;


Example 2:

Schema:
{
  "employees": [
    {"column": "employee_id", "type": "int"},
    {"column": "department", "type": "varchar"},
    {"column": "salary", "type": "decimal"}
  ]
}

Question:
Show the average salary for each department.

Reasoning:
- We need the average salary.
- Department is the grouping column.
- AVG() calculates the average salary.
- GROUP BY groups employees by department.

SQL:
SELECT department, AVG(salary) AS average_salary
FROM employees
GROUP BY department;


Now solve the following question using the actual database schema.

Database schema:
""" + schema_text + """

User question:
""" + question + """

Follow the same reasoning approach.

Return only the final valid MySQL SELECT query.
Do not include explanations or markdown formatting.

SQL:
"""

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    ).to("cuda")

    outputs = model.generate(
        **inputs,
        max_new_tokens=200,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id
    )

    # Extract newly generated tokens
    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]

    sql = tokenizer.decode(
        new_tokens,
        skip_special_tokens=True
    )

    sql = sql.strip()

    # Remove optional SQL markdown formatting
    if sql.startswith("```"):
        sql = sql.replace("```sql", "").replace("```", "").strip()

    return sql


if __name__ == "__main__":

    model, tokenizer = load_model()

    question = "Show total sales for each product category."

    result = generate_sql(question, model, tokenizer)

    print("\nGenerated SQL:")
    print(result)
