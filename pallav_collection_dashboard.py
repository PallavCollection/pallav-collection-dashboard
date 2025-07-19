import streamlit as st
import pandas as pd
import plotly.express as px
import os
import io
from datetime import datetime
from utils import clean_headers, correct_column, to_excel_download

# Constants
AGENT_COLUMNS = ["Agent", "Agent Name", "Agent_Name"]

# Title & Timestamp
now = datetime.now()
st.set_page_config(page_title="Pallav Collection Dashboard", layout="wide")

# Sidebar File Uploads
st.sidebar.header("📁 Upload Files")
st.session_state["allocation_files"] = st.sidebar.file_uploader("Allocation Files", type="xlsx", accept_multiple_files=True)
st.session_state["paid_files"] = st.sidebar.file_uploader("Current Paid Files", type="xlsx", accept_multiple_files=True)
st.session_state["previous_paid_files"] = st.sidebar.file_uploader("Previous Paid Files", type="xlsx", accept_multiple_files=True)
st.session_state["agent_file"] = st.sidebar.file_uploader("Agent Performance File", type="xlsx")

# Sidebar Tabs
selected_tab = st.sidebar.radio("📂 Select Tab", ["Dashboard", "Agent Performance"])

if selected_tab == "Dashboard":
    st.title("📊 Pallav Collection Dashboard")
    st.caption(f"Last refreshed at {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # ... your entire existing dashboard logic goes here (not altered) ...

elif selected_tab == "Agent Performance":
    st.title("📋 Agent Performance Report")
    if "agent_file" not in st.session_state or st.session_state["agent_file"] is None:
        st.info("Please upload an agent performance file from the sidebar.")
    else:
        try:
            df_agent = pd.read_excel(st.session_state["agent_file"])
            df_agent = clean_headers(df_agent)

            # Identify agent column
            agent_col = correct_column(df_agent, AGENT_COLUMNS)
            if not agent_col:
                st.error("Agent column not found.")
            else:
                numeric_cols = df_agent.select_dtypes(include='number').columns.tolist()
                pivot_df = df_agent.groupby(agent_col)[numeric_cols].sum().reset_index()

                st.markdown("### 🧾 Pivot Report by Agent")
                st.dataframe(pivot_df, use_container_width=True)

                # 📊 Chart for multiple metrics
                if numeric_cols:
                    fig = px.bar(
                        pivot_df.melt(id_vars=agent_col, value_vars=numeric_cols),
                        x=agent_col,
                        y='value',
                        color='variable',
                        barmode='group',
                        title="📊 Agent Performance Comparison (Multiple Metrics)"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # 📥 Download Excel
                st.markdown("### 📥 Download Report")
                excel_data = to_excel_download(pivot_df)
                st.download_button(
                    label="⬇️ Download Agent Summary (Excel)",
                    data=excel_data,
                    file_name="agent_performance_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"Error loading agent performance file: {e}")
