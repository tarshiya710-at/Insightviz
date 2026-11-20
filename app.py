
import streamlit as st
import sys
import re
import pandas as pd
from pathlib import Path

# ---------------- PATHS & IMPORTS ----------------

ROOT = Path(__file__).resolve().parent

sys.path.extend([
    str(ROOT / "src" / "database"),
    str(ROOT / "src" / "model"),
    str(ROOT / "src" / "visualization")
])

from db_connection import get_connection, get_available_databases
from schema_reader import get_schema
from sql_executor import execute_sql
from sql_generator import generate_sql
from model_loader import load_model
from chart_recommender import generate_chart_recommendation
try:
    from chart_recommender import validate_chart
except ImportError:
    validate_chart = None
from chart_generator import generate_chart


# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="InsightViz",
    page_icon="📊",
    layout="wide"
)

# Theme is stored in session state, so it survives Streamlit reruns.
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False

DARK = st.session_state["dark_mode"]
THEME = {
    "bg": "#090D18" if DARK else "#F4F6FC",
    "surface": "rgba(19, 25, 41, 0.92)" if DARK else "rgba(255,255,255,0.90)",
    "surface2": "#151D2E" if DARK else "#FFFFFF",
    "text": "#F1F5FF" if DARK else "#17213A",
    "muted": "#A5B1C8" if DARK else "#69758D",
    "border": "#29364D" if DARK else "#E5EAF4",
    "grid": "#29364D" if DARK else "#E9EDF5",
    "plot": "#111827" if DARK else "#FFFFFF",
    "sidebar": "#0D1423" if DARK else "#EAF0FC",
}



# ---------------- CUSTOM CSS ----------------

css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
:root {{ color-scheme: {'dark' if DARK else 'light'}; }}
html, body, [class*="css"], button, input, textarea {{ font-family: 'Plus Jakarta Sans', sans-serif !important; }}
.stApp {{ background: radial-gradient(ellipse at 78% 0%, {'rgba(50,105,220,.18)' if DARK else 'rgba(116,91,230,.12)'}, transparent 34%), radial-gradient(ellipse at 8% 75%, {'rgba(0,190,210,.09)' if DARK else 'rgba(45,190,210,.08)'}, transparent 30%), {THEME['bg']}; color: {THEME['text']}; }}
.block-container {{ max-width: 1540px; padding-top: 1.35rem; padding-bottom: 3rem; }}
/* Remove Streamlit's dark top chrome/header strip */
[data-testid="stHeader"] {{ background: transparent !important; height: 0 !important; }}
[data-testid="stToolbar"] {{ right: 1rem; }}
#MainMenu, footer {{ visibility: hidden; }}
header {{ background: transparent !important; }}
h1,h2,h3,h4 {{ color: {THEME['text']} !important; font-weight: 800 !important; letter-spacing: -.55px; }}
p,label, [data-testid="stCaptionContainer"] {{ color: {THEME['muted']}; }}
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, {THEME['sidebar']}, {THEME['bg']}); border-right: 1px solid {THEME['border']}; }}
[data-testid="stSidebar"] > div:first-child {{ padding-top: 1.35rem; }}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,[data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] span {{ color: {THEME['text']}; }}
[data-testid="stSidebar"] div.stButton > button {{ width:100%; min-height:46px; border-radius:13px; border:1px solid transparent; background:{'rgba(255,255,255,.045)' if DARK else 'rgba(255,255,255,.72)'}; color:{THEME['text']} !important; font-weight:650; text-align:left; transition:all .2s ease; }}
[data-testid="stSidebar"] div.stButton > button:hover {{ border-color:#7C6CF0; transform:translateX(3px); box-shadow:0 7px 22px rgba(93,90,220,.18); }}
[data-testid="stSidebar"] div.stButton > button[kind="primary"] {{ background:linear-gradient(105deg,#6557E8,#2E9FD0); color:#fff !important; box-shadow:0 8px 24px rgba(91,102,225,.28); }}
[data-testid="stSidebar"] div.stButton > button p {{ color:inherit !important; }}
[data-baseweb="select"] > div {{ background:{THEME['surface2']} !important; border-color:{THEME['border']} !important; border-radius:12px !important; }}
[data-baseweb="select"] * {{ color:{THEME['text']} !important; }}
div.stButton > button, div.stDownloadButton > button {{ min-height:43px; border-radius:12px; font-weight:700; transition:all .2s ease; }}
div.stButton > button[kind="primary"] {{ background:linear-gradient(105deg,#6557E8,#2E9FD0); color:#fff !important; border:0; box-shadow:0 7px 20px rgba(91,102,225,.25); }}
div.stButton > button[kind="primary"]:hover {{ transform:translateY(-2px); box-shadow:0 10px 26px rgba(91,102,225,.36); }}
div.stDownloadButton > button {{ background:{'rgba(255,255,255,.06)' if DARK else '#F0F3FC'}; color:{THEME['text']} !important; border:1px solid {THEME['border']}; }}
/* Glass KPI tiles */
div[data-testid="stMetric"] {{ position:relative; overflow:hidden; background:{THEME['surface']}; border:1px solid {THEME['border']}; border-radius:19px; padding:20px 20px 17px; box-shadow:0 9px 28px {'rgba(0,0,0,.22)' if DARK else 'rgba(45,65,110,.07)'}, inset 0 1px 0 rgba(255,255,255,.12); backdrop-filter:blur(16px); transition:transform .22s ease, box-shadow .22s ease; }}
div[data-testid="stMetric"]:before {{ content:""; position:absolute; top:0; left:0; right:0; height:4px; background:linear-gradient(90deg,#35D5D0,#7367F0,#B36AF5); }}
div[data-testid="stMetric"]:after {{ content:""; position:absolute; width:130px; height:90px; right:-30px; top:-42px; background:radial-gradient(circle,rgba(100,120,255,.19),transparent 70%); pointer-events:none; }}
div[data-testid="stMetric"]:hover {{ transform:translateY(-4px); box-shadow:0 15px 35px {'rgba(0,0,0,.34)' if DARK else 'rgba(77,91,180,.16)'},0 0 22px rgba(94,120,245,.10); }}
div[data-testid="stMetricLabel"] {{ color:{THEME['muted']} !important; font-size:.82rem; font-weight:650; }}
div[data-testid="stMetricValue"] {{ color:{THEME['text']} !important; font-weight:800; }}
/* Ask box: readable in both themes */
div[data-testid="stTextInput"] input {{ min-height:58px; border:1.5px solid {'#3B4B67' if DARK else '#D9E1F1'}; border-radius:15px; background:{'#151E30' if DARK else '#FFFFFF'} !important; color:{THEME['text']} !important; font-size:15px; padding:0 17px; box-shadow:0 7px 22px {'rgba(0,0,0,.16)' if DARK else 'rgba(45,65,110,.055)'}; }}
div[data-testid="stTextInput"] input::placeholder {{ color:{'#AAB6CC' if DARK else '#77839A'} !important; opacity:1 !important; }}
div[data-testid="stTextInput"] input:focus {{ border-color:#7C70F2 !important; box-shadow:0 0 0 3px rgba(124,112,242,.18),0 0 22px rgba(70,160,220,.12); }}
div[data-testid="stExpander"], div[data-testid="stDataFrame"], div[data-testid="stAlert"] {{ border-radius:15px; border-color:{THEME['border']}; }}
div[data-testid="stExpander"] {{ background:{THEME['surface']}; }}
div[data-testid="stDataFrame"] {{ overflow:hidden; border:1px solid {THEME['border']}; }}
hr {{ border-color:{THEME['border']}; }}
.iv-panel {{ background:{THEME['surface']}; border:1px solid {THEME['border']}; border-radius:20px; padding:20px 22px; box-shadow:0 10px 30px {'rgba(0,0,0,.20)' if DARK else 'rgba(45,65,110,.06)'}; backdrop-filter:blur(16px); }}
.iv-kpi {{ position:relative; overflow:hidden; min-height:145px; padding:18px 18px 12px; border:1px solid {THEME['border']}; border-radius:18px; background:{THEME['surface']}; box-shadow:0 9px 26px {'rgba(0,0,0,.23)' if DARK else 'rgba(45,65,110,.07)'}; transition:all .22s ease; }}
.iv-kpi:hover {{ transform:translateY(-5px); box-shadow:0 16px 34px rgba(89,105,220,.18); }}
.iv-kpi:before {{ content:""; position:absolute; top:0; left:0; right:0; height:4px; background:linear-gradient(90deg,#35D5D0,#7866F2); }}
.iv-kpi-label {{ color:{THEME['muted']}; font-size:11px; font-weight:700; letter-spacing:1px; text-transform:uppercase; }}
.iv-kpi-value {{ color:{THEME['text']}; font-size:26px; font-weight:800; margin-top:7px; }}
.iv-kpi-sub {{ color:{THEME['muted']}; font-size:11px; margin-top:2px; }}
.iv-spark {{ display:flex; align-items:end; gap:5px; height:31px; margin-top:10px; }}
.iv-spark i {{ flex:1; min-width:5px; border-radius:5px 5px 2px 2px; background:linear-gradient(180deg,#8B79FF,#35C8D2); opacity:.9; }}

/* High-contrast primary action: especially important in light mode */
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button[kind="primary"] {{
    background: linear-gradient(105deg, #6557E8 0%, #278FCB 100%) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,.22) !important;
    box-shadow: 0 8px 22px rgba(74,91,210,.28) !important;
}}
div[data-testid="stButton"] > button[kind="primary"] *,
div[data-testid="stFormSubmitButton"] > button[kind="primary"] * {{
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    opacity: 1 !important;
    font-weight: 750 !important;
}}
div[data-testid="stButton"] > button[kind="primary"]:hover {{
    filter: brightness(1.08);
    transform: translateY(-2px);
    box-shadow: 0 12px 28px rgba(74,91,210,.38) !important;
}}
/* Chart picker: a glass card grid, visually related to the KPI tiles */
.st-key-chart_switcher_panel {{
    background: {THEME['surface']};
    border: 1px solid {THEME['border']};
    border-radius: 20px;
    padding: 16px 17px 13px;
    margin: 10px 0 16px;
    box-shadow: 0 9px 26px {'rgba(0,0,0,.22)' if DARK else 'rgba(45,65,110,.07)'};
    backdrop-filter: blur(16px);
}}
.st-key-chart_switcher_panel div[data-testid="stButton"] > button {{
    min-height: 56px !important;
    border-radius: 13px !important;
    border: 1px solid {THEME['border']} !important;
    background: {'rgba(255,255,255,.055)' if DARK else 'rgba(246,248,255,.96)'} !important;
    color: {THEME['text']} !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    text-align: center !important;
    white-space: normal !important;
    padding: 8px 7px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.08);
    transition: all .18s ease;
}}
.st-key-chart_switcher_panel div[data-testid="stButton"] > button * {{
    color: inherit !important;
}}
.st-key-chart_switcher_panel div[data-testid="stButton"] > button:hover {{
    border-color: #8174F3 !important;
    background: {'rgba(103,91,232,.18)' if DARK else '#F0EDFF'} !important;
    transform: translateY(-2px);
    box-shadow: 0 7px 18px rgba(103,91,232,.16);
}}
.st-key-chart_switcher_panel div[data-testid="stButton"] > button[kind="primary"] {{
    background: linear-gradient(130deg, #6557E8, #278FCB) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,.3) !important;
    box-shadow: 0 7px 20px rgba(91,102,225,.30) !important;
}}
.st-key-chart_switcher_panel div[data-testid="stButton"] > button[kind="primary"] * {{
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}}

.insight-box {{ background:{'linear-gradient(110deg,#18263A,#151D2E)' if DARK else 'linear-gradient(110deg,#EDF3FF,#FFFFFF)'}; border:1px solid {'#344762' if DARK else '#DCE5F5'}; border-radius:18px; padding:22px; margin-top:18px; }}
div[data-testid="stSpinner"] > div {{ border-top-color:#6D65EB !important; }}
</style>
"""
st.markdown(css, unsafe_allow_html=True)


# ---------------- DATABASE STATUS ----------------

connected = False
database_error = None
schema = {}

try:
    available_databases = get_available_databases()

    if not available_databases:
        raise Exception("No user databases found.")

    if "selected_database" not in st.session_state:
        conn = get_connection()
        current_database = conn.database
        conn.close()

        if current_database in available_databases:
            st.session_state["selected_database"] = current_database
        else:
            st.session_state["selected_database"] = available_databases[0]

    database_name = st.session_state["selected_database"]

    if database_name not in available_databases:
        database_name = available_databases[0]
        st.session_state["selected_database"] = database_name

    conn = get_connection(database_name)
    connected = conn.is_connected()
    conn.close()

    if connected:
        schema = get_schema(database_name)

except Exception as e:
    database_error = str(e)
    database_name = "Not connected"
    connected = False



# ---------------- LOAD MODEL ----------------

@st.cache_resource
def get_ai_model():
    return load_model()





# ---------------- SIDEBAR ----------------

if "navigation" not in st.session_state:
    st.session_state["navigation"] = "Ask & Analyze"


def navigate_to(page):
    st.session_state["navigation"] = page


with st.sidebar:

    st.markdown("""
    <div style="padding:5px 0 12px 0;">
        <div style="font-size:27px;font-weight:800;color:#39216C;">
            📊 InsightViz
        </div>
        <div style="font-size:12px;color:#81749F;">
            AI-Powered Data Analytics
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### APPEARANCE")
    theme_choice = st.toggle("🌙 Dark mode", value=st.session_state["dark_mode"], key="dark_mode_toggle")
    if theme_choice != st.session_state["dark_mode"]:
        st.session_state["dark_mode"] = theme_choice
        st.rerun()

    st.divider()

    st.markdown("### 🗄️ DATABASE CONNECTION")

    if connected:

        selected_database = st.selectbox(
            "Select MySQL Database",
            options=available_databases,
            index=available_databases.index(database_name),
            key="selected_database"
        )

        st.success(f"Connected: {selected_database}")

    else:
        st.error("MySQL Disconnected")

    st.divider()

    st.markdown("### WORKSPACE")

    pages = [
        ("Ask & Analyze", "💬"),
        ("Saved Insights", "🔖"),
        ("Query History", "🕘"),
        ("Datasets", "🗄️"),
        ("Settings", "⚙️")
    ]

    for page, icon in pages:

        is_active = st.session_state["navigation"] == page

        if st.button(
            f"{icon}  {page}",
            key=f"nav_{page}",
            use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            navigate_to(page)
            st.rerun()

    st.divider()

    st.markdown("### DATA SOURCES")

    st.markdown("""
    <div style="
        background:rgba(255,255,255,0.72);
        border:1px solid #DED0F8;
        padding:14px;
        border-radius:13px;
        color:#39216C;">
        📁 <b>CSV / Excel Upload</b><br>
        <span style="font-size:12px;color:#81749F;">
            Coming Soon
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.caption("✨ Powered by Qwen 2.5 + LoRA")




# ---------------- PAGE NAVIGATION ----------------

selected_page = st.session_state["navigation"]

if selected_page != "Ask & Analyze":

    st.markdown(
        f"<h1>{selected_page}</h1>",
        unsafe_allow_html=True
    )

    upcoming_pages = {
        "Saved Insights": "Save and revisit your previous analyses.",
        "Query History": "View your previously executed queries.",
        "Datasets": "Manage and upload your datasets.",
        "Settings": "Manage your application preferences."
    }

    st.markdown(f"""
    <div style="
        background:rgba(255,255,255,0.85);
        border:1px solid #E2D7F5;
        border-radius:18px;
        padding:35px;
        margin-top:20px;
        text-align:center;
        box-shadow:0 8px 25px rgba(80,50,130,0.06);">
        <div style="font-size:42px;">🚀</div>
        <h2 style="color:#7041D9;">Coming Soon</h2>
        <p>{upcoming_pages.get(selected_page, "")}</p>
        <span style="
            background:#EEE5FF;
            color:#6330CE;
            padding:7px 15px;
            border-radius:20px;
            font-size:12px;">
            Under Development
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.stop()



# ---------------- TOP BAR ----------------

top1, top2 = st.columns([4, 1])

with top1:
    st.markdown(
        f"**🗄️ MySQL Database: `{database_name}`**"
    )

with top2:
    st.markdown("👤 Arshiya Tariq")



# ---------------- HEADER ----------------

st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin:8px 0 22px;">
 <div><div style="font-size:12px;letter-spacing:1.6px;font-weight:800;color:{'#8FA6C8' if DARK else '#77839A'};text-transform:uppercase;">WORKSPACE / DASHBOARD</div>
 <h1 style="margin:5px 0 3px;font-size:34px;">InsightViz <span style="color:#6D65EB;">Analytics</span></h1>
 <div style="color:{THEME['muted']};font-size:14px;">Ask in plain language. Explore results. Discover insights.</div></div>
 <div style="padding:10px 15px;border:1px solid {THEME['border']};border-radius:14px;background:{THEME['surface']};color:{THEME['text']};font-size:13px;">● &nbsp;{database_name}</div>
</div>
""", unsafe_allow_html=True)


# ---------------- DATABASE OVERVIEW ----------------

st.subheader("Database Overview")

if connected:

    db1, db2, db3 = st.columns(3)

    with db1:
        st.metric("Active Database", database_name)

    with db2:
        st.metric("Available Tables", len(schema))

    with db3:
        total_columns = sum(len(columns) for columns in schema.values())
        st.metric("Total Columns", total_columns)

    st.success(f"🟢 MySQL Database Connected: {database_name}")

else:
    st.error("MySQL Database Disconnected")

    if database_error:
        st.caption(f"Connection details: {database_error}")


# ---------------- SCHEMA DETAILS ----------------

with st.expander("🗄️ View Database Tables & Columns"):

    if schema:
        for table, columns in schema.items():
            st.markdown(f"**Table: {table}**")
            st.dataframe(
                columns,
                width="stretch",
                hide_index=True
            )
    else:
        st.info("No database tables found.")


st.divider()


# ---------------- QUESTION INPUT ----------------

st.markdown("### 💬 Ask Your Data")
st.caption("Describe what you want to learn from the selected MySQL database.")
question = st.text_input(
    "Natural language query",
    placeholder="Try: Show total sales by category, sorted from highest to lowest...",
    label_visibility="collapsed",
    key="natural_language_question"
)
generate = st.button(
    "✦  Generate & Analyze",
    type="primary",
    use_container_width=True
)




# ---------------- PIPELINE ----------------

if generate:

    if not question.strip():
        st.warning("Please enter a question.")

    elif not connected or not schema:
        st.error("Connect your MySQL database first.")

    else:
        try:

            # STEP 1: GENERATE SQL
            with st.spinner("Loading Qwen and generating SQL..."):

                model, tokenizer = get_ai_model()

                sql = generate_sql(
                    question,
                    model,
                    tokenizer,
                    database=database_name
                )

            sql = sql.replace("```sql", "").replace("```", "").strip()

            st.session_state["generated_sql"] = sql
            st.session_state["question"] = question
            st.session_state["active_database"] = database_name

            # STEP 2: EXECUTE SQL
            with st.spinner("Executing SQL on MySQL..."):

                df = execute_sql(
                    sql,
                    database=database_name
                )

            st.session_state["query_df"] = df

            # STEP 3: CHART RECOMMENDATION
            if df.empty:

                st.warning("No records found.")
                st.session_state.pop("chart_info", None)

            else:

                with st.spinner(
                    "Qwen is analysing data and recommending a chart..."
                ):

                    chart_info = generate_chart_recommendation(
                        df,
                        question,
                        model,
                        tokenizer
                    )

                st.session_state["chart_info"] = chart_info
                st.session_state["selected_chart_type"] = str(chart_info.get("chart", "bar")).lower()
                st.session_state.pop("insightviz_chart_switcher", None)

                st.success("Analysis completed successfully!")

        except Exception as e:

            st.error(f"Pipeline error: {e}")
            print("PIPELINE ERROR:", repr(e))






# ---------------- INTERACTIVE CHART SWITCHER HELPERS ----------------

def get_chart_switcher_options(dataframe, recommendation):
    """
    Build chart configurations from the returned DataFrame.
    Reuses the project's existing validate_chart() when available.
    """
    if dataframe is None or dataframe.empty:
        return {}

    numeric = dataframe.select_dtypes(include="number").columns.tolist()
    categorical = dataframe.select_dtypes(
        include=["object", "category", "bool"]
    ).columns.tolist()
    date_cols = dataframe.select_dtypes(
        include=["datetime", "datetimetz"]
    ).columns.tolist()
    all_cols = dataframe.columns.tolist()

    # Detect date-like text columns without changing the original result.
    for col in all_cols:
        if col not in date_cols and col not in numeric:
            try:
                parsed = pd.to_datetime(dataframe[col], errors="coerce")
                if len(parsed) and parsed.notna().mean() >= 0.8:
                    date_cols.append(col)
            except Exception:
                pass

    x_category = (categorical or date_cols or
                  [c for c in all_cols if c not in numeric])
    x_time = date_cols or x_category
    configs = {}

    def add(label, config):
        config = dict(config)
        config.setdefault("color", None)
        config.setdefault("size", None)
        config.setdefault("path", None)
        config.setdefault("reason", f"Alternative {label.lower()} view of the same query results.")
        valid = True
        if validate_chart is not None:
            try:
                valid = bool(validate_chart(dataframe, config))
            except Exception:
                valid = False
        else:
            # Safe compatibility fallback if this project version does not
            # expose validate_chart from chart_recommender.py.
            chart = config.get("chart")
            x, y = config.get("x_axis"), config.get("y_axis")
            if chart in {"bar", "line", "area"}:
                valid = x in all_cols and y in numeric and x != y
            elif chart in {"pie", "donut"}:
                valid = x in categorical and y in numeric
            elif chart == "histogram":
                valid = x in numeric
            elif chart in {"scatter", "grouping_scatter"}:
                valid = x in numeric and y in numeric and x != y
            elif chart == "bubble":
                valid = all(c in numeric for c in [x, y, config.get("size")])
            elif chart == "box":
                valid = y in numeric
            elif chart == "heatmap":
                valid = len(numeric) >= 2
            elif chart == "treemap":
                valid = bool(config.get("path")) and y in numeric
            elif chart in {"stacked_bar", "grouping_line"}:
                valid = x in all_cols and y in numeric and config.get("color") in all_cols
            else:
                valid = False
        if valid:
            configs[label] = config

    # Preserve the AI recommendation as the first/default choice.
    if recommendation and recommendation.get("chart"):
        recommended_name = str(recommendation["chart"]).lower().replace(" ", "_")
        label_map = {
            "stacked_bar": "Stacked Bar",
            "grouping_line": "Grouped Line",
            "grouping_scatter": "Grouped Scatter",
        }
        recommended_label = label_map.get(recommended_name, recommended_name.title())
        if recommended_name in {
            "bar", "line", "scatter", "pie", "stacked_bar",
            "grouping_line", "grouping_scatter", "histogram", "area",
            "donut", "box", "heatmap", "treemap", "bubble"
        }:
            configs[recommended_label] = dict(recommendation)

    if numeric and x_category:
        add("Bar", {"chart": "bar", "x_axis": x_category[0], "y_axis": numeric[0]})
        add("Pie", {"chart": "pie", "x_axis": x_category[0], "y_axis": numeric[0]})
        add("Donut", {"chart": "donut", "x_axis": x_category[0], "y_axis": numeric[0]})
        add("Stacked Bar", {
            "chart": "stacked_bar", "x_axis": x_category[0],
            "y_axis": numeric[0],
            "color": categorical[1] if len(categorical) > 1 else None
        })

    if numeric and x_time:
        add("Line", {"chart": "line", "x_axis": x_time[0], "y_axis": numeric[0]})
        add("Area", {"chart": "area", "x_axis": x_time[0], "y_axis": numeric[0]})
        if categorical:
            add("Grouped Line", {
                "chart": "grouping_line", "x_axis": x_time[0],
                "y_axis": numeric[0], "color": categorical[0]
            })

    if len(numeric) >= 2:
        add("Scatter", {"chart": "scatter", "x_axis": numeric[0], "y_axis": numeric[1]})
        add("Heatmap", {"chart": "heatmap", "x_axis": None, "y_axis": None})
        if len(numeric) >= 3:
            add("Bubble", {
                "chart": "bubble", "x_axis": numeric[0],
                "y_axis": numeric[1], "size": numeric[2]
            })
        if categorical:
            add("Grouped Scatter", {
                "chart": "grouping_scatter", "x_axis": numeric[0],
                "y_axis": numeric[1], "color": categorical[0]
            })

    if numeric:
        add("Histogram", {"chart": "histogram", "x_axis": numeric[0], "y_axis": None})
        add("Box", {
            "chart": "box", "x_axis": categorical[0] if categorical else None,
            "y_axis": numeric[0]
        })
        if categorical:
            add("Treemap", {
                "chart": "treemap", "x_axis": None, "y_axis": numeric[0],
                "path": [categorical[0]]
            })

    return configs


# ---------------- DISPLAY RESULTS ----------------

if "generated_sql" in st.session_state and st.session_state.get("active_database") == database_name:

    sql = st.session_state["generated_sql"]
    df = st.session_state.get("query_df")
    chart_info = st.session_state.get("chart_info", {})

    if df is not None and not df.empty:

        st.divider()

        # KPI CARDS — values and mini-bars are derived from the returned query data
        st.subheader("Analytics Overview")

        numeric_cols = [
            col for col in df.select_dtypes(include="number").columns
            if not re.search(r"(^|_)(id|code|index)($|_)", str(col).lower())
        ]
        x_axis = chart_info.get("x_axis")
        y_axis = chart_info.get("y_axis")

        def spark_bars(series):
            values = pd.to_numeric(series, errors="coerce").dropna().tail(8).tolist()
            if not values:
                values = [1]
            low, high = min(values), max(values)
            heights = [max(12, int(12 + 25 * ((v - low) / (high - low)))) if high != low else 22 for v in values]
            return "".join(f'<i style="height:{h}px"></i>' for h in heights)

        def kpi_card(label, value, sub, series=None):
            bars = spark_bars(series) if series is not None else "<i style='height:14px'></i><i style='height:21px'></i><i style='height:17px'></i><i style='height:27px'></i><i style='height:23px'></i><i style='height:30px'></i>"
            st.markdown(f"""<div class="iv-kpi"><div class="iv-kpi-label">{label}</div><div class="iv-kpi-value">{value}</div><div class="iv-kpi-sub">{sub}</div><div class="iv-spark">{bars}</div></div>""", unsafe_allow_html=True)

        metric_cols = st.columns(3)
        with metric_cols[0]:
            if x_axis in df.columns:
                kpi_card("Categories", f"{df[x_axis].nunique():,}", f"Unique values in {x_axis}")
            else:
                kpi_card("Records", f"{len(df):,}", "Rows returned by this query")
        with metric_cols[1]:
            if y_axis in numeric_cols:
                kpi_card(f"Total {y_axis}", f"{df[y_axis].sum():,.2f}", "Sum of returned values", df[y_axis])
            elif numeric_cols:
                col = numeric_cols[0]
                kpi_card(f"Total {col}", f"{df[col].sum():,.2f}", "Sum of returned values", df[col])
            else:
                kpi_card("Total Records", f"{len(df):,}", "Rows returned by this query")
        with metric_cols[2]:
            if y_axis in numeric_cols:
                kpi_card(f"Average {y_axis}", f"{df[y_axis].mean():,.2f}", "Average of returned values", df[y_axis])
            elif numeric_cols:
                col = numeric_cols[0]
                kpi_card(f"Average {col}", f"{df[col].mean():,.2f}", "Average of returned values", df[col])
            else:
                kpi_card("Columns", f"{len(df.columns):,}", "Fields in query result")

        # MAIN ANALYSIS: recommended chart + data intelligence panel
        chart_col, analytics_col = st.columns([1.55, 0.85], gap="large")

        with chart_col:
            st.markdown("### 📊 Recommended Visualization")
            chart_options = get_chart_switcher_options(df, chart_info)

            if chart_options:
                option_labels = list(chart_options.keys())
                current_type = st.session_state.get("selected_chart_type")
                recommended_type = str(chart_info.get("chart", "bar")).lower()

                selected_label = next(
                    (label for label, info in chart_options.items()
                     if str(info.get("chart", "")).lower() == current_type),
                    None
                )
                if selected_label not in option_labels:
                    selected_label = next(
                        (label for label, info in chart_options.items()
                         if str(info.get("chart", "")).lower() == recommended_type),
                        option_labels[0]
                    )

                recommended_label = next(
                    (label for label, info in chart_options.items()
                     if str(info.get("chart", "")).lower() == recommended_type),
                    selected_label
                )

                st.caption("Choose another view of the same results — SQL will not run again.")
                with st.container(key="chart_switcher_panel"):
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;"
                        f"align-items:center;gap:10px;margin:0 0 12px;'>"
                        f"<span style='font-weight:800;color:{THEME['text']};'>CHART STYLES</span>"
                        f"<span style='font-size:11px;font-weight:750;color:#FFFFFF;"
                        f"background:linear-gradient(100deg,#6557E8,#278FCB);"
                        f"padding:5px 10px;border-radius:20px;'>"
                        f"✦ AI recommended: {recommended_label}</span></div>",
                        unsafe_allow_html=True
                    )

                    # Three cards per row keep the choices readable and balanced.
                    cards_per_row = 3
                    for row_start in range(0, len(option_labels), cards_per_row):
                        row_labels = option_labels[row_start:row_start + cards_per_row]
                        card_cols = st.columns(cards_per_row, gap="small")
                        for col_index, label in enumerate(row_labels):
                            with card_cols[col_index]:
                                chart_type = str(chart_options[label].get("chart", "")).lower()
                                icon_map = {
                                    "bar": "▥", "line": "⌁", "scatter": "⠿",
                                    "pie": "◕", "donut": "◉", "stacked_bar": "▤",
                                    "grouping_line": "⌁", "grouping_scatter": "⠿",
                                    "histogram": "▥", "area": "◢", "box": "▣",
                                    "heatmap": "▦", "treemap": "▧", "bubble": "◉"
                                }
                                is_selected = label == selected_label
                                button_label = f"{'✓  ' if is_selected else ''}{icon_map.get(chart_type, '▦')}  {label}"
                                if st.button(
                                    button_label,
                                    key=f"chart_choice_{chart_type}",
                                    type="primary" if is_selected else "secondary",
                                    use_container_width=True
                                ):
                                    st.session_state["selected_chart_type"] = chart_type
                                    st.rerun()

                chart_info = chart_options[selected_label]
                st.session_state["selected_chart_type"] = str(chart_info.get("chart", "")).lower()
            else:
                st.info("No alternative chart types are suitable for this query result.")

            fig = generate_chart(df, chart_info)
            if fig is not None:
                chart_template = "plotly_dark" if DARK else "plotly_white"
                chart_bg = "#111827" if DARK else "#FFFFFF"
                chart_text = "#E8EEF9" if DARK else "#26334D"
                chart_grid = "#2B3950" if DARK else "#E9EDF5"
                palette = (
                    ["#42D6D0", "#8B78FF", "#F5B84B", "#FF6B8A", "#4F9DFF", "#50C99A", "#C17BFF"]
                    if DARK else
                    ["#6257E8", "#20B8C5", "#F0A83B", "#E66B83", "#4388E8", "#27A879", "#A66BE8"]
                )
                fig.update_layout(
                    template=chart_template, colorway=palette,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=chart_bg,
                    font=dict(family="Plus Jakarta Sans", color=chart_text, size=13),
                    title_font=dict(family="Plus Jakarta Sans", color=chart_text, size=19),
                    legend=dict(font=dict(color=chart_text, size=13),
                                bgcolor=("rgba(17,24,39,0.92)" if DARK else "rgba(255,255,255,0.97)"),
                                bordercolor=("#3B4B63" if DARK else "#DCE3EF"), borderwidth=1,
                                title_font=dict(color=chart_text)),
                    margin=dict(l=25, r=25, t=55, b=35),
                    transition=dict(duration=450),
                    hoverlabel=dict(bgcolor=("#1D293B" if DARK else "#FFFFFF"), font=dict(color=chart_text))
                )
                fig.update_xaxes(showgrid=True, gridcolor=chart_grid, zerolinecolor=chart_grid,
                                 tickfont=dict(color=chart_text), title_font=dict(color=chart_text))
                fig.update_yaxes(showgrid=True, gridcolor=chart_grid, zerolinecolor=chart_grid,
                                 tickfont=dict(color=chart_text), title_font=dict(color=chart_text))
                if str(chart_info.get("chart", "")).lower() in {"pie", "donut"}:
                    fig.update_traces(marker_line_width=1.5, marker_line_color=("#111827" if DARK else "#FFFFFF"))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": True, "displaylogo": False})
            else:
                st.info("No suitable chart found for this result.")

            st.caption(f"Chart: {chart_info.get('chart', 'Table').title()}  ·  X: {chart_info.get('x_axis', '—')}  ·  Y: {chart_info.get('y_axis', '—')}")

        with analytics_col:
            st.markdown("### ✨ Smart Analytics")
            st.markdown(f'<div class="iv-panel"><div style="font-size:12px;color:{THEME["muted"]};font-weight:700;letter-spacing:1px;">RESULT SNAPSHOT</div><div style="font-size:28px;font-weight:800;color:{THEME["text"]};margin-top:5px;">{len(df):,} <span style="font-size:14px;font-weight:600;">rows</span></div><div style="font-size:12px;color:{THEME["muted"]};">{len(df.columns)} columns in this query result</div></div>', unsafe_allow_html=True)
            missing_count = int(df.isna().sum().sum())
            duplicate_count = int(df.duplicated().sum())
            a1, a2 = st.columns(2)
            with a1:
                st.metric("Missing cells", f"{missing_count:,}")
            with a2:
                st.metric("Duplicate rows", f"{duplicate_count:,}")

            if numeric_cols:
                chosen_numeric = y_axis if y_axis in numeric_cols else numeric_cols[0]
                values = pd.to_numeric(df[chosen_numeric], errors="coerce").dropna()
                if not values.empty:
                    st.markdown(f"**{chosen_numeric} distribution**")
                    s1, s2 = st.columns(2)
                    s1.metric("Minimum", f"{values.min():,.2f}")
                    s2.metric("Maximum", f"{values.max():,.2f}")
                    st.caption(f"Mean: {values.mean():,.2f}  ·  Median: {values.median():,.2f}")
                    q1, q3 = values.quantile(.25), values.quantile(.75)
                    iqr = q3 - q1
                    outliers = int(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum()) if iqr > 0 else 0
                    st.caption(f"Potential outliers (IQR method): {outliers}")

            categorical_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
            if categorical_cols:
                chosen_category = x_axis if x_axis in categorical_cols else categorical_cols[0]
                top_value = df[chosen_category].astype(str).value_counts(dropna=False).head(1)
                if not top_value.empty:
                    st.markdown("**Most frequent category**")
                    st.write(f"{chosen_category}: **{top_value.index[0]}** ({int(top_value.iloc[0]):,} rows)")
            st.caption("These observations describe the returned query results, not the entire database.")

        # SQL and result table are kept accessible below the visualization.
        sql_tab, results_tab, details_tab = st.tabs(["💻 Generated SQL", "📋 Query Results", "ℹ️ Visualization Details"])
        with sql_tab:
            st.code(sql, language="sql")
            st.download_button("⬇ Download SQL", data=sql, file_name="generated_query.sql", mime="text/sql")
        with results_tab:
            st.caption(f"{len(df)} rows returned")
            st.dataframe(df, width="stretch", hide_index=True)
            st.download_button("⬇ Download Results", data=df.to_csv(index=False), file_name="query_results.csv", mime="text/csv")
        with details_tab:
            st.write("**Chart Type:**", chart_info.get("chart", "Table").title())
            st.write("**X-axis:**", chart_info.get("x_axis", "Not applicable"))
            st.write("**Y-axis:**", chart_info.get("y_axis", "Not applicable"))
            st.write("**Recommendation:**", chart_info.get("reason", "No explanation provided."))


        # INSIGHT

        st.markdown("""
        <div class="insight-box">
            <h3 style="color:#7135E8;">✨ Insight</h3>
            <p>
                Your query was successfully executed.
                The results and visualization above summarize
                the requested data.
            </p>
        </div>
        """, unsafe_allow_html=True)


else:
    st.info("Enter a question above to start analyzing your database. Results are shown here after a successful query.")
