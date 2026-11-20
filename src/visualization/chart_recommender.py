import json
import re

import pandas as pd
import torch

from chart_selector import prepare_dataframe, select_chart


SUPPORTED_CHARTS = {
    "bar", "line", "scatter", "pie", "stacked_bar",
    "grouping_line", "grouping_scatter", "histogram", "area",
    "donut", "box", "heatmap", "treemap", "bubble"
}

# These are few-shot prompt examples, not additional model training.
CHART_EXAMPLES = [
    {"question": "Compare sales across product categories", "chart": "bar",
     "x_axis": "category", "y_axis": "sales", "color": None, "size": None, "path": None},
    {"question": "How has revenue changed month by month?", "chart": "line",
     "x_axis": "month", "y_axis": "revenue", "color": None, "size": None, "path": None},
    {"question": "Is advertising spend related to sales?", "chart": "scatter",
     "x_axis": "ad_spend", "y_axis": "sales", "color": None, "size": None, "path": None},
    {"question": "What share of sales comes from each category?", "chart": "donut",
     "x_axis": "category", "y_axis": "sales", "color": None, "size": None, "path": None},
    {"question": "Break down each category's sales by region", "chart": "stacked_bar",
     "x_axis": "category", "y_axis": "sales", "color": "region", "size": None, "path": None},
    {"question": "Compare monthly revenue trends across regions", "chart": "grouping_line",
     "x_axis": "month", "y_axis": "revenue", "color": "region", "size": None, "path": None},
    {"question": "Compare price and demand in each category", "chart": "grouping_scatter",
     "x_axis": "price", "y_axis": "demand", "color": "category", "size": None, "path": None},
    {"question": "What is the distribution of customer ages?", "chart": "histogram",
     "x_axis": "age", "y_axis": None, "color": None, "size": None, "path": None},
    {"question": "Compare salary spread and outliers across departments", "chart": "box",
     "x_axis": "department", "y_axis": "salary", "color": None, "size": None, "path": None},
    {"question": "Which numeric measures are correlated?", "chart": "heatmap",
     "x_axis": None, "y_axis": None, "color": None, "size": None, "path": None},
    {"question": "Show sales hierarchy from department to product", "chart": "treemap",
     "x_axis": None, "y_axis": "sales", "color": None, "size": None,
     "path": ["department", "product"]},
    {"question": "Explore price versus quantity using revenue as magnitude", "chart": "bubble",
     "x_axis": "price", "y_axis": "quantity", "color": None, "size": "revenue", "path": None}
]


def _normalise_dataframe(df):
    try:
        result = prepare_dataframe(df.copy())
    except Exception:
        result = df.copy()

    for col in result.columns:
        if pd.api.types.is_object_dtype(result[col]) or pd.api.types.is_string_dtype(result[col]):
            converted = pd.to_numeric(result[col], errors="coerce")
            count = result[col].notna().sum()
            if count and converted.notna().sum() / count >= 0.95:
                result[col] = converted
    return result


def _safe_number(value):
    try:
        if pd.isna(value):
            return None
        number = float(value)
        if number == float("inf") or number == float("-inf"):
            return None
        return number
    except (TypeError, ValueError):
        return None


def _data_profile(df):
    profile = {}
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            profile[col] = {
                "type": "numeric",
                "non_null": int(series.notna().sum()),
                "unique": int(series.nunique()),
                "min": _safe_number(series.min()),
                "max": _safe_number(series.max())
            }
        elif pd.api.types.is_datetime64_any_dtype(series):
            profile[col] = {
                "type": "datetime",
                "non_null": int(series.notna().sum()),
                "unique": int(series.nunique())
            }
        else:
            profile[col] = {
                "type": "categorical/text",
                "non_null": int(series.notna().sum()),
                "unique": int(series.nunique()),
                "examples": [str(v)[:50] for v in series.dropna().unique()[:5]]
            }
    return profile


def _extract_json(response):
    if not response:
        return None
    cleaned = str(response).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    decoder = json.JSONDecoder()

    for i, char in enumerate(cleaned):
        if char == "{":
            try:
                obj, _ = decoder.raw_decode(cleaned[i:])
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
    return None


def validate_chart(df, info):
    """Return True only when the chart and its required columns are compatible."""
    if not isinstance(info, dict):
        return False

    chart = str(info.get("chart", "")).strip().lower()
    if chart not in SUPPORTED_CHARTS:
        return False

    x, y = info.get("x_axis"), info.get("y_axis")
    color, size, path = info.get("color"), info.get("size"), info.get("path")
    columns = set(df.columns)

    for col in (x, y, color, size):
        if col is not None and col not in columns:
            return False

    numeric = {c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    dates = {c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])}
    categorical = columns - numeric - dates

    if chart == "heatmap":
        return len(numeric) >= 2

    if chart == "histogram":
        return x in numeric and y is None

    if chart == "treemap":
        return (
            isinstance(path, list) and len(path) > 0
            and all(c in categorical for c in path)
            and y in numeric
        )

    if chart == "bubble":
        return x in numeric and y in numeric and size in numeric and len({x, y, size}) == 3

    if chart == "scatter":
        return x in numeric and y in numeric and x != y

    if chart == "grouping_scatter":
        return x in numeric and y in numeric and x != y and color in categorical

    if chart == "box":
        return y in numeric and (x is None or x in categorical or x in dates)

    if chart in {"pie", "donut"}:
        return x in categorical and y in numeric

    if chart == "stacked_bar":
        return x in categorical and y in numeric and color in categorical and color != x

    if chart == "grouping_line":
        return x in (dates | categorical | numeric) and y in numeric and color in categorical

    if chart == "bar":
        return x in (categorical | dates | numeric) and y in numeric and x != y

    if chart in {"line", "area"}:
        return x in (dates | categorical | numeric) and y in numeric and x != y

    return False


def _build_prompt(df, question):
    profile = _data_profile(df)
    examples = json.dumps(CHART_EXAMPLES, ensure_ascii=False)
    sample_rows = df.head(4).astype(str).to_dict(orient="records")

    return f"""
You are InsightViz, an expert data visualization analyst.

TASK:
Choose the single best chart for the user's analytical question and returned data.

IMPORTANT:
- You recommend a visualization. You do NOT generate SQL or code.
- Identify analytical intent before considering column types.
- Use only exact column names from DATA PROFILE. Never invent columns.
- Choose a chart only when the required columns and data types exist.
- Do not choose bar merely because a categorical column exists.

FEW-SHOT EXAMPLES:
{examples}

DATA PROFILE:
{json.dumps(profile, ensure_ascii=False)}

SAMPLE ROWS:
{json.dumps(sample_rows, ensure_ascii=False)}

USER QUESTION:
{question}

CHART DECISION RULES:
1. Category comparison, ranking, highest/lowest or top values: bar.
2. Change over dates, months or years: line. Use area when magnitude over time is emphasized.
3. Relationship, association, versus or correlation between two numeric measures: scatter.
4. Distribution/frequency of one numeric measure: histogram.
5. Spread, median, variation or outliers across groups: box.
6. Part-to-whole, percentage or share for a small number of categories: pie or donut.
7. Comparison split by a second category: stacked_bar.
8. Trends compared across groups: grouping_line.
9. Numeric relationships compared across groups: grouping_scatter.
10. Correlation matrix across numeric columns: heatmap.
11. Hierarchical categories: treemap.
12. Three numeric dimensions: bubble.
13. A categorical column alone is NOT a reason to choose bar.
14. Do not choose scatter unless numeric relationship analysis is intended.
15. Do not choose line/area without a meaningful ordered or time axis.
16. For histogram, x_axis is numeric and y_axis is null.
17. For heatmap, x_axis and y_axis are null.
18. For treemap, path is a list of categorical columns and y_axis is numeric.
19. For stacked_bar/grouping_line/grouping_scatter, color is a categorical column.

OUTPUT:
Return only one valid JSON object. No markdown or extra text.

FORMAT:
{{
  "chart": "bar",
  "x_axis": null,
  "y_axis": null,
  "color": null,
  "size": null,
  "path": null,
  "reason": "Short explanation"
}}

SUPPORTED CHARTS:
{", ".join(sorted(SUPPORTED_CHARTS))}
"""


def _model_device(model):
    try:
        return next(model.parameters()).device
    except (StopIteration, AttributeError):
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def generate_chart_recommendation(df, question, model, tokenizer):
    """
    Qwen recommendation with schema/data-type validation.
    The improved Python selector is used if Qwen fails or returns invalid JSON.
    """
    prepared = _normalise_dataframe(df)

    if prepared.empty or len(prepared.columns) == 0:
        return select_chart(prepared, question)

    fallback = select_chart(prepared, question)

    if model is None or tokenizer is None:
        print("Chart model/tokenizer unavailable; using Python fallback.")
        return fallback

    prompt = _build_prompt(prepared, question)

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are InsightViz chart recommendation assistant. "
                    "Return one valid JSON object only. Never generate SQL."
                )
            },
            {"role": "user", "content": prompt}
        ]

        try:
            formatted = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            formatted = (
                "SYSTEM:\n" + messages[0]["content"]
                + "\n\nUSER:\n" + prompt + "\n\nASSISTANT:\n"
            )

        inputs = tokenizer(formatted, return_tensors="pt")
        device = _model_device(model)
        inputs = {key: value.to(device) for key, value in inputs.items()}

        print("\n========== CHART MODEL DEBUG ==========")
        print("Question:", question)
        print("Columns:", list(prepared.columns))
        print("Python fallback:", fallback)
        print("=======================================")

        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=220,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        print("Qwen raw chart response:", response)

        info = _extract_json(response)
        if info is None:
            print("Qwen returned invalid JSON. Using Python fallback.")
            return fallback

        info["chart"] = str(info.get("chart", "")).strip().lower()
        for key in ("x_axis", "y_axis", "color", "size", "path"):
            info.setdefault(key, None)

        if not validate_chart(prepared, info):
            print("Qwen recommendation failed validation:", info)
            print("Using Python fallback:", fallback)
            return fallback

        info.setdefault(
            "reason",
            "Selected based on analytical intent and available data."
        )
        print("Validated Qwen chart recommendation:", info)
        return info

    except Exception as exc:
        print("Chart recommendation error:", repr(exc))
        print("Using Python fallback:", fallback)
        return fallback
