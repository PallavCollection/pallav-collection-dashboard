import streamlit as st
import pandas as pd
import plotly.express as px
import os
import io
from datetime import datetime

st.set_page_config(page_title="📊 BPO Collection Dashboard", layout="wide")

st.title("📊 Collection BPO Dashboard")
st.info("Continue uploading allocation and paid files per process below...")

# --- Helper Functions ---
def clean_headers(df):
    df.columns = [col.strip().replace(" ", "_").title() for col in df.columns]
    return df

def combine_files(file_list):
    df_list = []
    for file in file_list:
        df = pd.read_excel(file)
        df = clean_headers(df)
        df_list.append(df)
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

# --- Sidebar Controls ---
st.sidebar.subheader("👤 Upload Agent Performance")
agent_file = st.sidebar.file_uploader("Upload Agent Performance Excel", type=["xlsx"], key="agent")

st.sidebar.subheader("📁 Upload Allocation Files")
alloc_files = st.sidebar.file_uploader("Upload Allocation Files", type=["xlsx"], accept_multiple_files=True, key="alloc")

st.sidebar.subheader("📅 Upload Current Month Paid")
paid_current_files = st.sidebar.file_uploader("Upload Current Paid Files", type=["xlsx"], accept_multiple_files=True, key="paid_current")

st.sidebar.subheader("🗓 Upload Previous Months Paid")
paid_prev_files = st.sidebar.file_uploader("Upload Previous Paid Files", type=["xlsx"], accept_multiple_files=True, key="paid_prev")

# --- Agent Performance Logic ---
if agent_file:
    df_agent = pd.read_excel(agent_file)
    df_agent = clean_headers(df_agent)
    st.subheader("📋 Agent Performance Data")
    st.dataframe(df_agent, use_container_width=True)

    if 'Agent_Name' in df_agent.columns and 'Score' in df_agent.columns:
        fig = px.bar(df_agent, x="Agent_Name", y="Score", color="Week", title="Agent Score by Week")
        st.plotly_chart(fig, use_container_width=True)

        fig_bytes = fig.to_image(format="png")
        st.download_button("📥 Download Chart as PNG", data=fig_bytes, file_name="agent_chart.png")

        excel_out = io.BytesIO()
        df_agent.to_excel(excel_out, index=False)
        st.download_button("📥 Download Cleaned Agent Data", data=excel_out.getvalue(), file_name="cleaned_agent_data.xlsx")

# --- Allocation and Paid Logic ---
df_alloc = combine_files(alloc_files)
df_paid_current = combine_files(paid_current_files)
df_paid_prev = combine_files(paid_prev_files)

if not df_alloc.empty:
    st.subheader("📄 Allocation File")
    st.dataframe(df_alloc)

if not df_paid_current.empty:
    st.subheader("📄 Current Paid File")
    st.dataframe(df_paid_current)

if not df_paid_prev.empty:
    st.subheader("📄 Previous Paid File")
    st.dataframe(df_paid_prev)

if not df_alloc.empty and (not df_paid_current.empty or not df_paid_prev.empty):
    df_paid_all = pd.concat([df_paid_current, df_paid_prev], ignore_index=True)
    df_merged = pd.merge(df_alloc, df_paid_all, on='Loan_Id', how='left')
    df_merged['Paid_Amount'] = df_merged['Paid_Amount'].fillna(0)
    df_merged['Recovery_%'] = (df_merged['Paid_Amount'] / df_merged['Allocated_Amount'] * 100).round(2)
    df_merged['Balance'] = df_merged['Allocated_Amount'] - df_merged['Paid_Amount']

    st.subheader("📊 Merged Data")
    st.dataframe(df_merged)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Allocated", f"₹{df_merged['Allocated_Amount'].sum():,.0f}")
        st.metric("Total Paid", f"₹{df_merged['Paid_Amount'].sum():,.0f}")
    with col2:
        st.metric("Recovery %", f"{df_merged['Recovery_%'].mean():.2f}%")
        st.metric("Total Balance", f"₹{df_merged['Balance'].sum():,.0f}")

    if 'Bucket' in df_merged.columns:
        bucket_df = df_merged.groupby('Bucket')[['Allocated_Amount','Paid_Amount']].sum().reset_index()
        bucket_df['Recovery_%'] = (bucket_df['Paid_Amount'] / bucket_df['Allocated_Amount'] * 100).round(2)
        fig_bucket = px.bar(bucket_df, x='Bucket', y='Recovery_%', color='Bucket', text='Recovery_%')
        st.plotly_chart(fig_bucket, use_container_width=True)

        fig_bytes = fig_bucket.to_image(format="png")
        st.download_button("📥 Download Bucket Chart", data=fig_bytes, file_name="bucket_chart.png")

    merged_out = io.BytesIO()
    df_merged.to_excel(merged_out, index=False)
    st.download_button("📥 Download Merged File", data=merged_out.getvalue(), file_name="merged_collection.xlsx")
