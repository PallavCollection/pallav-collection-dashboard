# 📊 BPO Collection Dashboard - Enhanced Version with Stylish Charts and Tables

import streamlit as st 
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from datetime import datetime, timedelta
from io import BytesIO
from fpdf import FPDF
import tempfile

st.set_page_config(page_title="📊 BPO Collection Dashboard", layout="wide")

CACHE_DIR = "cache"
UPLOAD_DIR = os.path.join(CACHE_DIR, "uploads")
SESSION_FILE = "session.json"
CONFIG_FILE = os.path.join(CACHE_DIR, "config.json")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

PAID_COLUMNS = ['paid_amt', 'payment', 'paid_amount', 'recovery', 'paid']
ALLOC_COLUMNS = ['allocation', 'target', 'total_due']
AGENT_COLUMNS = ['agent', 'agent_name']
DATE_COLUMNS = ['date', 'payment_date', 'paid_date']

def clean_headers(df):
    df.columns = [col.strip().lower().replace(" ", "_").replace("(", "").replace(")", "") for col in df.columns]
    return df

def find_column(df, options):
    for col in df.columns:
        if col.lower() in options:
            return col
    return None

def generate_agent_pdf(agent_data, process_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Agent Report - {agent_data['Agent']}", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Process: {process_name}", ln=True)
    for key, value in agent_data.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

def to_excel_download(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()

def stylish_bar_chart(df, title):
    return px.bar(
        df, x="Agent", y="% Recovery", color="% Recovery",
        color_continuous_scale=px.colors.sequential.Tealgrn,
        title=title,
        labels={"% Recovery": "% Recovery"},
        template="plotly_white"
    )

def stylish_line_chart(df, title):
    return px.line(
        df, x="Agent", y="Paid Amount", color="Month",
        markers=True, template="plotly_dark", title=title
    )

def stylish_table(df):
    fig = go.Figure(data=[go.Table(
        header=dict(values=list(df.columns),
                    fill_color='darkslategray',
                    font=dict(color='white', size=12),
                    align='left'),
        cells=dict(values=[df[col] for col in df.columns],
                   fill_color='lavender', align='left'))
    ])
    return fig

st.markdown("## 📈 Reports Section")
below_target_threshold = 75

for process_key, files in uploaded_files.items():
    alloc_file = files.get("alloc")
    paid_curr_file = files.get("paid_curr")
    paid_prev_file = files.get("paid_prev")
    process_name = files.get("name", process_key)

    if alloc_file and paid_curr_file:
        try:
            df_alloc = clean_headers(pd.read_excel(alloc_file))
            df_curr = clean_headers(pd.read_excel(paid_curr_file))
            df_prev = clean_headers(pd.read_excel(paid_prev_file)) if paid_prev_file else pd.DataFrame()

            alloc_col = find_column(df_alloc, ALLOC_COLUMNS)
            paid_col = find_column(df_curr, PAID_COLUMNS)
            agent_col = find_column(df_alloc, AGENT_COLUMNS)

            if not all([alloc_col, paid_col, agent_col]):
                st.warning(f"Missing required columns in uploaded files for {process_name}.")
                continue

            df_alloc = df_alloc[[agent_col, alloc_col]]
            df_curr = df_curr[[agent_col, paid_col]]
            df_prev = df_prev[[agent_col, paid_col]] if not df_prev.empty else pd.DataFrame()

            merged_df = df_alloc.merge(df_curr, on=agent_col, how="left").fillna(0)
            merged_df["% Recovery"] = (merged_df[paid_col] / merged_df[alloc_col]) * 100
            merged_df = merged_df.rename(columns={agent_col: "Agent", alloc_col: "Allocation", paid_col: "Paid"})

            st.subheader(f"📊 {process_name} Report")

            total_alloc = merged_df["Allocation"].sum()
            total_paid = merged_df["Paid"].sum()
            avg_recovery = (total_paid / total_alloc) * 100 if total_alloc else 0
            below_target_agents = merged_df[merged_df["% Recovery"] < below_target_threshold]["Agent"].nunique()

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("🧾 Total Allocation", f"₹ {total_alloc:,.0f}")
            kpi2.metric("💰 Total Paid", f"₹ {total_paid:,.0f}")
            kpi3.metric("📈 Avg. % Recovery", f"{avg_recovery:.2f}%")
            kpi4.metric("⚠️ Below Target Agents", below_target_agents)

            st.markdown("### 📋 Stylish Agent Table")
            st.plotly_chart(stylish_table(merged_df), use_container_width=True)

            st.markdown("### 📊 Recovery Rate Bar Chart")
            st.plotly_chart(stylish_bar_chart(merged_df, f"{process_name} - % Recovery by Agent"), use_container_width=True)

            if not df_prev.empty:
                df_prev = df_prev.rename(columns={paid_col: "Paid_Last_Month", agent_col: "Agent"})
                hist_df = df_curr.rename(columns={paid_col: "Paid_Current_Month", agent_col: "Agent"}).merge(
                    df_prev[["Agent", "Paid_Last_Month"]], on="Agent", how="outer"
                ).fillna(0)
                hist_df = hist_df.melt(id_vars=["Agent"], value_vars=["Paid_Current_Month", "Paid_Last_Month"],
                                       var_name="Month", value_name="Paid Amount")
                st.markdown("### 📈 Historical Paid Comparison")
                st.plotly_chart(stylish_line_chart(hist_df, f"{process_name} - Paid Trend Comparison"), use_container_width=True)

            excel_data = to_excel_download(merged_df)
            st.download_button("📥 Download Excel", excel_data, file_name=f"{process_name}_report.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            st.markdown("### 🧾 Download Agent PDFs")
            for i, row in merged_df.iterrows():
                with st.expander(f"📄 {row['Agent']}"):
                    pdf_path = generate_agent_pdf(row, process_name)
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_file,
                            file_name=f"{row['Agent']}_{process_name}.pdf",
                            mime="application/pdf"
                        )
            st.markdown("---")

        except Exception as e:
            st.error(f"Error generating report for {process_name}: {e}")
    else:
        st.info(f"Please upload both Allocation and Current Paid files for {process_name} to generate report.")
