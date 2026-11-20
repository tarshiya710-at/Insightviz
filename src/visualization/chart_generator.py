"""InsightViz chart rendering with readable hover details and theme-aware styling."""

import pandas as pd
import plotly.express as px


DARK_PALETTE = [
    "#42D6D0", "#8B78FF", "#F5B84B", "#FF6B8A",
    "#4F9DFF", "#50C99A", "#C17BFF", "#F28E2B",
]
LIGHT_PALETTE = [
    "#6257E8", "#20B8C5", "#F0A83B", "#E66B83",
    "#4388E8", "#27A879", "#A66BE8", "#D56B35",
]


def _prepare_dataframe(df):
    """Convert numeric-looking SQL/Decimal columns so Plotly treats them as measures."""
    result = df.copy()
    for column in result.columns:
        if (
            pd.api.types.is_object_dtype(result[column])
            or pd.api.types.is_string_dtype(result[column])
        ):
            converted = pd.to_numeric(result[column], errors="coerce")
            original_count = int(result[column].notna().sum())
            if original_count and converted.notna().sum() / original_count >= 0.85:
                result[column] = converted
    return result


def _valid_column(df, column):
    return column is not None and column in df.columns


def _hover_fields(df, x=None, y=None, color=None, size=None):
    """Keep tooltips useful without dumping every column into the hover card."""
    fields = {}
    for column in (color, size):
        if _valid_column(df, column) and column not in (x, y):
            fields[column] = True
    return fields


def generate_chart(df, chart_info, dark_mode=False):
    """Build one of the project's supported Plotly charts.

    chart_info schema remains compatible with chart_recommender.py:
    chart, x_axis, y_axis, color, size, path, reason.
    """
    if df is None or df.empty or not isinstance(chart_info, dict):
        return None

    data = _prepare_dataframe(df)
    chart_type = str(chart_info.get("chart", "")).strip().lower()
    x = chart_info.get("x_axis")
    y = chart_info.get("y_axis")
    color = chart_info.get("color")
    size = chart_info.get("size")
    path = chart_info.get("path")

    palette = DARK_PALETTE if dark_mode else LIGHT_PALETTE
    hover_fields = _hover_fields(data, x, y, color, size)
    title_map = {
        "bar": "Category Comparison", "line": "Trend Analysis",
        "scatter": "Relationship Analysis", "pie": "Category Contribution",
        "stacked_bar": "Category Composition", "grouping_line": "Trend by Group",
        "grouping_scatter": "Relationship by Group", "histogram": "Frequency Distribution",
        "area": "Trend Magnitude", "donut": "Contribution Breakdown",
        "box": "Distribution and Outliers", "heatmap": "Correlation Heatmap",
        "treemap": "Hierarchical Breakdown", "bubble": "Multi-variable Analysis",
    }

    try:
        if chart_type == "bar":
            if not (_valid_column(data, x) and _valid_column(data, y)):
                return None
            # Color each category distinctly, but don't create a redundant legend.
            fig = px.bar(
                data, x=x, y=y, color=x, title=title_map[chart_type],
                color_discrete_sequence=palette, hover_data=hover_fields,
                text_auto=".3s" if len(data) <= 25 else False,
            )
            fig.update_layout(showlegend=False)
            if len(data) <= 25:
                fig.update_traces(textposition="outside", cliponaxis=False)

        elif chart_type == "line":
            fig = px.line(data, x=x, y=y, title=title_map[chart_type], markers=True,
                          color_discrete_sequence=palette, hover_data=hover_fields)
            fig.update_traces(line=dict(width=3), marker=dict(size=8))

        elif chart_type == "scatter":
            fig = px.scatter(data, x=x, y=y, title=title_map[chart_type],
                             color=color if _valid_column(data, color) else None,
                             color_discrete_sequence=palette, hover_data=hover_fields)
            fig.update_traces(marker=dict(size=11, opacity=0.86, line=dict(width=1, color="#FFFFFF")))

        elif chart_type in {"pie", "donut"}:
            if not (_valid_column(data, x) and _valid_column(data, y)):
                return None
            fig = px.pie(data, names=x, values=y, title=title_map[chart_type],
                         hole=0.52 if chart_type == "donut" else 0,
                         color_discrete_sequence=palette,
                         hover_data=hover_fields)
            fig.update_traces(
                textinfo="label+percent+value" if len(data) <= 12 else "percent",
                textposition="inside",
                insidetextorientation="auto",
                marker=dict(line=dict(color="#111827" if dark_mode else "#FFFFFF", width=2)),
                hovertemplate="<b>%{label}</b><br>Value: %{value:,.2f}<br>Share: %{percent}<extra></extra>",
            )
            fig.update_layout(legend=dict(orientation="v", y=0.5, x=1.02))

        elif chart_type == "stacked_bar":
            if not all(_valid_column(data, c) for c in (x, y, color)):
                return None
            fig = px.bar(data, x=x, y=y, color=color, title=title_map[chart_type],
                         barmode="stack", color_discrete_sequence=palette,
                         hover_data=hover_fields)
            fig.update_traces(hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:,.2f}<extra></extra>")

        elif chart_type == "grouping_line":
            if not all(_valid_column(data, c) for c in (x, y, color)):
                return None
            fig = px.line(data, x=x, y=y, color=color, title=title_map[chart_type],
                          markers=True, color_discrete_sequence=palette,
                          hover_data=hover_fields)
            fig.update_traces(line=dict(width=3), marker=dict(size=7))

        elif chart_type == "grouping_scatter":
            if not all(_valid_column(data, c) for c in (x, y, color)):
                return None
            fig = px.scatter(data, x=x, y=y, color=color, title=title_map[chart_type],
                             color_discrete_sequence=palette, hover_data=hover_fields)
            fig.update_traces(marker=dict(size=10, opacity=0.85))

        elif chart_type == "histogram":
            if not _valid_column(data, x):
                return None
            fig = px.histogram(data, x=x, title=title_map[chart_type],
                               color_discrete_sequence=palette, hover_data=hover_fields,
                               nbins=min(40, max(10, int(len(data) ** 0.5))))
            fig.update_traces(marker_line_width=1, marker_line_color="#FFFFFF")

        elif chart_type == "area":
            if not all(_valid_column(data, c) for c in (x, y)):
                return None
            fig = px.area(data, x=x, y=y, title=title_map[chart_type], markers=True,
                          color_discrete_sequence=palette, hover_data=hover_fields)
            fig.update_traces(line=dict(width=2.5), opacity=0.78)

        elif chart_type == "box":
            if not _valid_column(data, y):
                return None
            fig = px.box(data, x=x if _valid_column(data, x) else None, y=y,
                         color=color if _valid_column(data, color) else None,
                         title=title_map[chart_type], points="outliers",
                         color_discrete_sequence=palette, hover_data=hover_fields)

        elif chart_type == "heatmap":
            numeric = data.select_dtypes(include="number")
            if numeric.shape[1] < 2:
                return None
            corr = numeric.corr(numeric_only=True)
            scale = [[0, "#E85D75"], [0.5, "#111827" if dark_mode else "#F5F7FC"], [1, "#39C6D2"]] if dark_mode else "RdBu"
            fig = px.imshow(corr, text_auto=".2f", title=title_map[chart_type],
                            color_continuous_scale=scale, zmin=-1, zmax=1, aspect="auto")

        elif chart_type == "treemap":
            if not path:
                path = [x] if _valid_column(data, x) else []
            if not path or not _valid_column(data, y) or any(not _valid_column(data, c) for c in path):
                return None
            fig = px.treemap(data, path=path, values=y, title=title_map[chart_type],
                             color_discrete_sequence=palette)
            fig.update_traces(textinfo="label+percent parent", hovertemplate="<b>%{label}</b><br>Value: %{value:,.2f}<br>%{percentRoot:.1%} of total<extra></extra>")

        elif chart_type == "bubble":
            if not all(_valid_column(data, c) for c in (x, y, size)):
                return None
            fig = px.scatter(data, x=x, y=y, size=size,
                             color=color if _valid_column(data, color) else None,
                             title=title_map[chart_type], color_discrete_sequence=palette,
                             hover_data=hover_fields, size_max=48)
            fig.update_traces(marker=dict(opacity=0.78, line=dict(width=1, color="#FFFFFF")))

        else:
            return None

    except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        print(f"Chart rendering issue ({chart_type}): {exc}")
        return None

    text_color = "#E8EEF9" if dark_mode else "#26334D"
    grid_color = "#2B3950" if dark_mode else "#E9EDF5"
    plot_bg = "#111827" if dark_mode else "#FFFFFF"
    hover_bg = "#1D293B" if dark_mode else "#FFFFFF"

    fig.update_layout(
        template="plotly_dark" if dark_mode else "plotly_white",
        colorway=palette,
        title=dict(text=title_map.get(chart_type, "InsightViz Visualization"), x=0.02,
                   xanchor="left", font=dict(family="Plus Jakarta Sans", size=20, color=text_color)),
        font=dict(family="Plus Jakarta Sans", size=13, color=text_color),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=plot_bg,
        margin=dict(l=55, r=45, t=70, b=55),
        legend_title_text="",
        hoverlabel=dict(bgcolor=hover_bg, bordercolor="#66758F",
                        font=dict(family="Plus Jakarta Sans", size=13, color=text_color)),
        transition=dict(duration=400, easing="cubic-in-out"),
    )
    fig.update_xaxes(showgrid=True, gridcolor=grid_color, zerolinecolor=grid_color,
                     tickfont=dict(color=text_color), title_font=dict(color=text_color),
                     automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor=grid_color, zerolinecolor=grid_color,
                     tickfont=dict(color=text_color), title_font=dict(color=text_color),
                     automargin=True)

    # Useful chart-specific annotation: mark the highest value on simple bar comparisons.
    if chart_type == "bar" and _valid_column(data, x) and _valid_column(data, y) and len(data) <= 30:
        numeric_values = pd.to_numeric(data[y], errors="coerce")
        if numeric_values.notna().any():
            max_index = numeric_values.idxmax()
            max_row = data.loc[max_index]
            fig.add_annotation(
                x=max_row[x], y=float(numeric_values.loc[max_index]),
                text="Highest", showarrow=True, arrowhead=2, ax=0, ay=-35,
                font=dict(size=11, color="#F5B84B" if dark_mode else "#7654D6"),
                bgcolor="rgba(245,184,75,.14)", bordercolor="#F5B84B" if dark_mode else "#B9A6F2",
                borderwidth=1, borderpad=4,
            )

    return fig
