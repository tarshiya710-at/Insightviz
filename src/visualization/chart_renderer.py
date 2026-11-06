
import plotly.express as px


def render_chart(df, chart_config):

    chart_type = chart_config["chart"]

    x = chart_config.get("x_axis")
    y = chart_config.get("y_axis")

    if chart_type == "bar":
        fig = px.bar(
            df,
            x=x,
            y=y,
            title=f"{y} by {x}"
        )

    elif chart_type == "line":
        fig = px.line(
            df,
            x=x,
            y=y,
            title=f"{y} over time",
            markers=True
        )

    elif chart_type == "pie":
        fig = px.pie(
            df,
            names=x,
            values=y,
            title=f"{y} distribution"
        )

    elif chart_type == "scatter":
        fig = px.scatter(
            df,
            x=x,
            y=y,
            title=f"{y} vs {x}"
        )

    elif chart_type == "histogram":
        fig = px.histogram(
            df,
            x=x,
            title=f"Distribution of {x}"
        )

    else:
        return None

    fig.update_layout(
        template="plotly_white",
        title_x=0.5,
        height=500
    )

    return fig
if __name__ == "__main__":

    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[2]

    sys.path.append(str(ROOT / "src" / "database"))
    sys.path.append(str(ROOT / "src" / "visualization"))

    from sql_executor import execute_sql
    from chart_selector import select_chart

    query = """
    SELECT category,
           SUM(quantity * price) AS total_sales
    FROM demo_sales
    GROUP BY category
    """

    df = execute_sql(query)

    chart_config = select_chart(
        df,
        "Compare total sales by product category"
    )

    fig = render_chart(df, chart_config)

    if fig:
        fig.show()