import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from io import BytesIO
from datetime import datetime
import json
import plotly.express as px

st.set_page_config(layout="wide", page_title="Pallav Collection Dashboard")
st.title("📊 Pallav Collection Dashboard")
st.caption(f"Last refreshed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 📤 Sidebar: Upload Agent Performance File
st.sidebar.header("📤 Upload Agent Performance File")
agent_file = st.sidebar.file_uploader("Upload Excel", type=["xlsx"], key="agent_file_upload")

if agent_file:
    st.session_state["agent_file"] = agent_file
    st.toast("Agent file uploaded!", icon="✅")

# =============================================
# 👤 Agent Performance Pivot Table
# =============================================
st.header("👤 Agent Performance Pivot Table")

if "agent_file" not in st.session_state:
    st.info("📂 Please upload Agent Performance file from the sidebar to view pivot table.")
else:
    df_agent = pd.read_excel(st.session_state["agent_file"])

    # 🧮 Auto-calculated field if relevant columns exist
    if set(["paid", "allocation"]).issubset(df_agent.columns):
        df_agent["paid_percent"] = (df_agent["paid"] / df_agent["allocation"]) * 100

    # Detect column types
    numeric_cols = df_agent.select_dtypes(include='number').columns.tolist()
    cat_cols = df_agent.select_dtypes(exclude='number').columns.tolist()

    # Load saved pivot config from file if exists
    CONFIG_FILE = ".agent_pivot_config.json"
    try:
        with open(CONFIG_FILE, "r") as f:
            grid_options = json.load(f)
    except:
        gb = GridOptionsBuilder.from_dataframe(df_agent)
        gb.configure_default_column(enableValue=True, enableRowGroup=True, enablePivot=True, filter="agTextColumnFilter")
        gb.configure_side_bar()
        gb.configure_pagination()
        gb.configure_grid_options(domLayout='normal')
        gb.configure_selection(selection_mode="multiple")
        grid_options = gb.build()

    st.subheader("📋 Interactive Agent Pivot Table")
    grid_response = AgGrid(
        df_agent,
        gridOptions=grid_options,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        update_mode='MANUAL',
        height=400,
        fit_columns_on_grid_load=True,
        theme='balham'
    )

    # Save grid settings after any interaction
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(grid_response["gridOptions"], f)
    except: pass

    st.download_button(
        label="⬇ Download as Excel",
        data=BytesIO()
        if grid_response['data'].empty else BytesIO(grid_response['data'].to_excel(index=False, engine='openpyxl')),
        file_name="agent_pivot_export.xlsx"
    )

    # 📊 Basic Pivot Chart (if agent + recovery exist)
    if set(["agent", "recovery"]).issubset(df_agent.columns):
        st.subheader("📊 Total Recovery by Agent")
        chart = px.bar(df_agent, x="agent", y="recovery", color="agent", title="Agent-wise Recovery", text_auto=True)
        st.plotly_chart(chart, use_container_width=True)

# Keep existing dashboard logic below (not touched)
# =============================================
# YOUR EXISTING TABS AND FEATURES HERE
# =============================================
# Example:
# tab1, tab2, tab3 = st.tabs(["📁 Upload Files", "📊 Dashboard", "🧾 Reports"])
# ...
# Your logic goes here untouched
