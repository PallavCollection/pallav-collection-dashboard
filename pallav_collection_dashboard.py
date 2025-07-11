# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="📊 BPO Dashboard", layout="wide")

# --- Auto Header Mapping ---
HEADER_MAPPING = {
    "loanid": "Loan_ID",
    "loan_id": "Loan_ID",
    "allocatedamount": "Allocated_Amount",
    "allocated_amount": "Allocated_Amount",
    "paidamount": "Paid_Amount",
    "paid_amount": "Paid_Amount",
    "paymentdate": "Payment_Date",
    "payment_date": "Payment_Date",
    "bucket": "Bucket",
    "agency": "Agency",
    "agent name": "Agent_Name"
}

def clean_headers(df):
    df.columns = [HEADER_MAPPING.get(col.strip().lower().replace(" ", "_"), col.strip().title().replace(" ", "_")) for col in df.columns]
    return df

# --- Auth ---
def authenticate(email, password):
    return email == "jjagarbattiudyog@gmail.com" and password == "Sanu@1998"

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Login Required")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate(email, password):
            st.session_state.authenticated = True
            st.success("✅ Login successful")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")
else:
    st.title("📊 Collection Dashboard")
    st.sidebar.header("📁 Upload Section")

    # Agent File Upload
    st.sidebar.subheader("👤 Agent Performance")
    agent_file = st.sidebar.file_uploader("Upload Agent File", type=["xlsx"])
    df_agent = pd.DataFrame()
    if agent_file:
        df_agent = pd.read_excel(agent_file)
        df_agent = clean_headers(df_agent)
        st.subheader("👤 Agent Performance Data")
        st.dataframe(df_agent)

        if 'Agent_Name' in df_agent.columns and 'Score' in df_agent.columns:
            fig = px.bar(df_agent, x="Agent_Name", y="Score", color="Week", title="Agent Score by Week")
            st.plotly_chart(fig, use_container_width=True)

            fig_bytes = fig.to_image(format="png")
            st.download_button("📥 Download Chart as PNG", data=fig_bytes, file_name="agent_chart.png")

        cleaned_bytes = df_agent.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Cleaned Agent Data", data=cleaned_bytes, file_name="cleaned_agent_data.csv")

    # Allocation and Paid Files
    st.sidebar.subheader("📤 Allocation + Paid Files")
    alloc_file = st.sidebar.file_uploader("Allocation File", type=["xlsx"])
    paid_file = st.sidebar.file_uploader("Paid File", type=["xlsx"])

    df_alloc, df_paid = pd.DataFrame(), pd.DataFrame()
    if alloc_file:
        df_alloc = pd.read_excel(alloc_file)
        df_alloc = clean_headers(df_alloc)
    if paid_file:
        df_paid = pd.read_excel(paid_file)
        df_paid = clean_headers(df_paid)

    if not df_alloc.empty and not df_paid.empty:
        df = pd.merge(df_alloc, df_paid, on="Loan_ID", how="left")
        df['Paid_Amount'] = df['Paid_Amount'].fillna(0)
        df['Recovery_%'] = (df['Paid_Amount'] / df['Allocated_Amount'] * 100).round(2)
        df['Balance'] = df['Allocated_Amount'] - df['Paid_Amount']

        st.subheader("📊 Summary Table")
        st.dataframe(df)

        st.metric("Total Allocated", f"₹{df['Allocated_Amount'].sum():,.0f}")
        st.metric("Total Paid", f"₹{df['Paid_Amount'].sum():,.0f}")
        st.metric("Recovery %", f"{df['Recovery_%'].mean():.2f}%")

        if 'Bucket' in df.columns:
            bucket_df = df.groupby('Bucket').agg({
                'Allocated_Amount': 'sum',
                'Paid_Amount': 'sum'
            }).reset_index()
            bucket_df['Recovery_%'] = (bucket_df['Paid_Amount'] / bucket_df['Allocated_Amount'] * 100).round(2)
            st.subheader("📊 Recovery % by Bucket")
            st.plotly_chart(px.bar(bucket_df, x='Bucket', y='Recovery_%', color='Bucket', text='Recovery_%'))

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Final Merged Data", csv, file_name="recovery_summary.csv")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout"):
        st.session_state.authenticated = False
        st.rerun()
