import re
import pandas as pd


def prepare_dataframe(df):
    """Copy the result and convert reliable numeric/date columns."""
    df = df.copy()
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
            converted = pd.to_numeric(s, errors="coerce")
            count = s.notna().sum()
            if count and converted.notna().sum() / count >= 0.95:
                df[col] = converted
                continue

        date_name = any(w in str(col).lower() for w in ("date", "time", "month", "year", "timestamp"))
        if date_name and not pd.api.types.is_datetime64_any_dtype(df[col]):
            converted = pd.to_datetime(df[col], errors="coerce")
            count = s.notna().sum()
            if count and converted.notna().sum() / count >= 0.70:
                df[col] = converted
    return df


def profile_data(df):
    df = prepare_dataframe(df)
    numeric, categorical, dates = [], [], []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            dates.append(col)
        elif pd.api.types.is_numeric_dtype(df[col]):
            numeric.append(col)
        else:
            categorical.append(col)
    return {"numerical": numeric, "categorical": categorical, "dates": dates}


def match_columns(question, columns):
    q = str(question).lower()
    return [c for c in columns if str(c).lower() in q]


def make_chart(chart, x=None, y=None, color=None, size=None, path=None, reason=""):
    return {
        "chart": chart, "x_axis": x, "y_axis": y, "color": color,
        "size": size, "path": path, "reason": reason
    }


def _useful_numeric(columns):
    # IDs/codes are usually identifiers, not measures.
    useful = [
        c for c in columns
        if not re.search(r"(^|[_\s])(id|code|index)([_\s]|$)", str(c).lower())
        and "customerid" not in str(c).lower()
        and "invoiceno" not in str(c).lower()
    ]
    return useful or list(columns)


def _mentioned(question, columns):
    q = str(question).lower()
    for col in sorted(columns, key=lambda c: len(str(c)), reverse=True):
        if str(col).lower() in q:
            return col
    return None


def select_chart(df, question):
    """Intent-first chart fallback. Returns the same config format as Qwen."""
    df = prepare_dataframe(df)
    if df.empty or not len(df.columns):
        return make_chart("table", reason="There is no data to visualize.")

    p = profile_data(df)
    nums = _useful_numeric(p["numerical"])
    cats, dates = p["categorical"], p["dates"]
    q = str(question).lower()

    measure = _mentioned(q, nums) or (nums[0] if nums else None)
    category = _mentioned(q, cats) or (cats[0] if cats else None)
    date_col = _mentioned(q, dates) or (dates[0] if dates else None)

    # Explicit chart requests.
    if any(t in q for t in ("heatmap", "correlation matrix")) and len(nums) >= 2:
        return make_chart("heatmap", reason="Shows correlations between numeric measures.")
    if any(t in q for t in ("treemap", "tree map")) and category and measure:
        return make_chart("treemap", y=measure, path=cats[:2],
                          reason="Shows hierarchical category contributions.")
    if "bubble" in q and len(nums) >= 3:
        x = _mentioned(q, nums) or nums[0]
        rest = [c for c in nums if c != x]
        return make_chart("bubble", x=x, y=rest[0], size=rest[1],
                          reason="Represents three numeric dimensions.")
    if any(t in q for t in ("box plot", "boxplot", "box chart")) and measure:
        return make_chart("box", x=category, y=measure,
                          reason="Shows spread, median and potential outliers.")
    if "histogram" in q and measure:
        return make_chart("histogram", x=measure,
                          reason="Shows the distribution of a numeric variable.")
    if any(t in q for t in ("donut", "doughnut")) and category and measure:
        return make_chart("donut", x=category, y=measure,
                          reason="Shows each category's share of the total.")
    if "pie chart" in q and category and measure:
        return make_chart("pie", x=category, y=measure,
                          reason="Shows category contributions to a whole.")
    if any(t in q for t in ("stacked bar", "stacked column")) and len(cats) >= 2 and measure:
        x = _mentioned(q, cats) or cats[0]
        group = next((c for c in cats if c != x), None)
        if group:
            return make_chart("stacked_bar", x=x, y=measure, color=group,
                              reason="Compares category totals split by subgroup.")

    if any(t in q for t in ("grouped line", "grouping line")) and date_col and measure and category:
        return make_chart("grouping_line", x=date_col, y=measure, color=category,
                          reason="Compares trends across groups.")
    if any(t in q for t in ("grouped scatter", "grouping scatter")) and len(nums) >= 2 and category:
        x = _mentioned(q, nums) or nums[0]
        y = next((c for c in nums if c != x), None)
        if y:
            return make_chart("grouping_scatter", x=x, y=y, color=category,
                              reason="Compares numeric relationships across groups.")

    # Relationship intent must be detected before generic category comparison.
    relation_terms = (
        "relationship", "correlation", "versus", " vs ", "against",
        "related to", "association"
    )
    if any(t in q for t in relation_terms) and len(nums) >= 2:
        x = _mentioned(q, nums) or nums[0]
        y = next((c for c in nums if c != x), None)
        if y:
            return make_chart("scatter", x=x, y=y,
                              reason="Examines the relationship between two numeric measures.")

    trend_terms = (
        "trend", "over time", "month by month", "monthly", "daily",
        "weekly", "yearly", "each month", "by month", "by date",
        "changes over", "changed over"
    )
    if any(t in q for t in trend_terms) and measure:
        x = date_col or category
        if x:
            chart = "area" if "area chart" in q or "area graph" in q else "line"
            return make_chart(chart, x=x, y=measure,
                              reason="Shows how a measure changes over time or ordered periods.")

    if any(t in q for t in ("distribution", "frequency distribution", "spread of")) and measure:
        if any(t in q for t in ("outlier", "spread", "variation")) and category:
            return make_chart("box", x=category, y=measure,
                              reason="Summarizes spread and potential outliers.")
        return make_chart("histogram", x=measure,
                          reason="Shows the frequency distribution of numeric values.")

    composition_terms = (
        "percentage contribution", "percentage share", "contribution",
        "proportion", "part-to-whole", "part to whole", "share of",
        "portion of", "as a percentage"
    )
    if any(t in q for t in composition_terms) and category and measure:
        n = df[category].nunique(dropna=True)
        chart = "donut" if 1 < n <= 8 else "bar"
        return make_chart(chart, x=category, y=measure,
                          reason="Shows category contribution to the total.")

    group_terms = ("by ", "across ", "for each ", "per ")
    if len(cats) >= 2 and measure and any(t in q for t in group_terms):
        x = _mentioned(q, cats) or cats[0]
        group = next((c for c in cats if c != x), None)
        if group:
            return make_chart("stacked_bar", x=x, y=measure, color=group,
                              reason="Compares a measure across categories and subgroups.")

    # Generic fallback: date trend first, then category comparison, then numeric relationship.
    if date_col and measure:
        return make_chart("line", x=date_col, y=measure,
                          reason="A line chart is suitable for a measure over time.")
    if category and measure:
        return make_chart("bar", x=category, y=measure,
                          reason="Compares a numeric measure across categories.")
    if len(nums) >= 2:
        return make_chart("scatter", x=nums[0], y=nums[1],
                          reason="Compares two numeric variables.")
    if measure:
        return make_chart("histogram", x=measure,
                          reason="Shows the distribution of the available numeric measure.")
    return make_chart("table", reason="No compatible chart could be identified.")
