
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.append(str(ROOT / "src" / "database"))

def select_chart(df, question=""):

    question = question.lower()

    # Identify column types
    numerical = df.select_dtypes(include="number").columns.tolist()

    categorical = df.select_dtypes(
        include=["object", "category", "bool"]
    ).columns.tolist()

    date_columns = [
        col for col in df.columns
        if pd.api.types.is_datetime64_any_dtype(df[col])
        or any(word in col.lower() for word in ["date", "time", "year", "month"])
    ]

    # 1. Trend analysis
    if date_columns and numerical:
        return {
            "chart": "line",
            "x_axis": date_columns[0],
            "y_axis": numerical[0],
            "reason": "Time-based trend analysis"
        }

    # 2. Distribution analysis
    if any(word in question for word in ["distribution", "frequency"]):
        if numerical:
            return {
                "chart": "histogram",
                "x_axis": numerical[0],
                "reason": "Numerical data distribution"
            }

    # 3. Relationship analysis
    if any(word in question for word in ["relationship", "correlation", "relationship between"]):
        if len(numerical) >= 2:
            return {
                "chart": "scatter",
                "x_axis": numerical[0],
                "y_axis": numerical[1],
                "reason": "Relationship between numerical variables"
            }

    # 4. Proportion analysis
    if any(word in question for word in ["percentage", "proportion", "share", "contribution"]):
        if categorical and numerical and df[categorical[0]].nunique() <= 6:
            return {
                "chart": "pie",
                "x_axis": categorical[0],
                "y_axis": numerical[0],
                "reason": "Proportion of total"
            }

    # 5. Comparison analysis
    if categorical and numerical:
        return {
            "chart": "bar",
            "x_axis": categorical[0],
            "y_axis": numerical[0],
            "reason": "Comparison across categories"
        }

    # 6. Numerical relationship by category
    if len(numerical) >= 2:
        return {
            "chart": "scatter",
            "x_axis": numerical[0],
            "y_axis": numerical[1],
            "reason": "Relationship between numerical variables"
        }

    # 7. Single numerical column
    if numerical:
        return {
            "chart": "histogram",
            "x_axis": numerical[0],
            "reason": "Numerical distribution"
        }

    return {
        "chart": "table",
        "reason": "No suitable chart found"
    }
if __name__ == "__main__":

    from sql_executor import execute_sql
    query = """
    SELECT category,
           SUM(quantity * price) AS total_sales
    FROM demo_sales
    GROUP BY category
    """

    df = execute_sql(query)

    result = select_chart(
        df,
        "Compare total sales by product category"
    )

    print(result)