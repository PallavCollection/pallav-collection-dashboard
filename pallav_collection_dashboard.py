import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
import json
from datetime import datetime, timedelta

# --- Auto Header Fixer ---
HEADER_MAPPING = {
    "loanid": "Loan_ID", "loan_id": "Loan_ID",
    "allocatedamount": "Allocated_Amount", "allocated_amount": "Allocated_Amount",
    "paidamount": "Paid_Amount", "paid_amount": "Paid_Amount",
    "paymentdate": "Payment_Date", "payment_date": "Payment_Date",
    "bucket": "Bucket", "agency": "Agency",
    "username": "Username", "score": "Score"
}

def clean_headers(df):
    df.columns = [HEADER_MAPPING.get(col.strip().lower().replace(" ", "_"), col.strip()) for col in df.columns]
    return df

# --- Paths and Config ---
CACHE_DIR = "cache"
SESSION_FILE = "session_data.json"
CONFIG_FILE = os.path.join(CACHE_DIR, "config.json")
AGENT_FILE_PATH = os.path.join(CACHE_DIR, "agent_data.csv")
os.makedirs(CACHE_DIR, exist_ok=True)

# --- Load / Save Config ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"process_count": 1, "process_names": {}}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# --- Session Handling ---
def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_session(data):
    with open(SESSION_FILE, 'w') as f:
        json.dump(data, f)

# --- Auth ---
def authenticate_user(email, password):
    return email == "jjagarbattiudyog@gmail.com" and password == "Sanu@1998"

# --- Streamlit Config ---
st.set_page_config(page_title="📊 Collection BPO Dashboard", layout="wide")

now = datetime.now()
config = load_config()
session_data = load_session()

# --- Authentication ---
if 'authenticated' not in st.session_state:
    last_login_str = session_data.get('last_login')
    if last_login_str:
        last_login = datetime.strptime(last_login_str, "%Y-%m-%d %H:%M:%S")
        if now - last_login < timedelta(hours=24):
            st.session_state.authenticated = True
            st.session_state.user_email = session_data.get('user_email', '')
        else:
            st.session_state.authenticated = False
    else:
        st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Secure Access")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate_user(email, password):
            st.session_state.authenticated = True
            st.session_state.user_email = email
            session_data = {'last_login': now.strftime("%Y-%m-%d %H:%M:%S"), 'user_email': email}
            save_session(session_data)
            st.success("✅ Logged in successfully!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials.")
    st.stop()

# --- UI Main ---
st.markdown("<h1 style='text-align: center; color: navy;'>📊 Collection BPO Dashboard</h1>", unsafe_allow_html=True)
is_editor = st.session_state.user_email == "jjagarbattiudyog@gmail.com"

# --- Sidebar Controls ---
with st.sidebar:
    if is_editor:
        if st.button("➕ Add Process"):
            config['process_count'] += 1
            save_config(config)
        if config['process_count'] > 1 and st.button("➖ Remove Process"):
            config['process_count'] -= 1
            save_config(config)

    st.markdown("---")
    st.subheader("👤 Upload Agent Performance")
    agent_file = st.file_uploader("Upload Excel", type=["xlsx"])

    if agent_file:
        agent_df = clean_headers(pd.read_excel(agent_file))
        agent_df.to_csv(AGENT_FILE_PATH, index=False)
        st.success("✅ Agent file uploaded successfully.")
        st.rerun()

    if os.path.exists(AGENT_FILE_PATH):
        with st.expander("⚙ Manage Agent File"):
            if st.radio("Delete Agent File?", ["No", "Yes"], key="del_agent") == "Yes":
                os.remove(AGENT_FILE_PATH)
                st.success("✅ Agent file deleted.")
                st.rerun()

# --- Agent Performance Viewer ---
if os.path.exists(AGENT_FILE_PATH):
    agent_df = pd.read_csv(AGENT_FILE_PATH)
    st.subheader("👤 Agent Performance")
    st.dataframe(agent_df, use_container_width=True)

    if "Username" in agent_df.columns and "Score" in agent_df.columns:
        fig = px.bar(agent_df, x="Username", y="Score", title="Agent Scores")
        st.plotly_chart(fig, use_container_width=True)

        csv = agent_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Agent Report", csv, file_name="agent_report.csv")

# --- Process Loop ---
process_data = {}

for i in range(config["process_count"]):
    st.markdown("---")
    st.subheader(f"📂 Process {i+1}")
    process_key = f"process_{i+1}"
    default_name = config["process_names"].get(process_key, f"Process_{i+1}")

    if is_editor:
        new_name = st.text_input(f"Name for Process {i+1}", value=default_name, key=f"name_input_{i}")
        config["process_names"][process_key] = new_name
        save_config(config)
    else:
        st.text(f"Name: {default_name}")

    process_name = config["process_names"][process_key]
    alloc_path = f"{CACHE_DIR}/alloc_{process_name}.csv"
    paid_curr_path = f"{CACHE_DIR}/paid_current_{process_name}.csv"
    paid_prev_path = f"{CACHE_DIR}/paid_prev_{process_name}.csv"

    # Upload
    alloc_files = st.file_uploader("📁 Allocation Files", type=["xlsx"], accept_multiple_files=True, key=f"alloc_{i}")
    paid_curr_files = st.file_uploader("📅 Current Month Paid", type=["xlsx"], accept_multiple_files=True, key=f"paid_curr_{i}")
    paid_prev_files = st.file_uploader("🗓 Previous Months Paid", type=["xlsx"], accept_multiple_files=True, key=f"paid_prev_{i}")

    # Save Files
    if is_editor and alloc_files:
        df_alloc = pd.concat([clean_headers(pd.read_excel(f)) for f in alloc_files])
        df_alloc.to_csv(alloc_path, index=False)
    elif os.path.exists(alloc_path):
        df_alloc = pd.read_csv(alloc_path)
    else:
        df_alloc = pd.DataFrame()

    if is_editor and paid_curr_files:
        df_curr = pd.concat([clean_headers(pd.read_excel(f)) for f in paid_curr_files])
        df_curr.to_csv(paid_curr_path, index=False)
    elif os.path.exists(paid_curr_path):
        df_curr = pd.read_csv(paid_curr_path)
    else:
        df_curr = pd.DataFrame()

    if is_editor and paid_prev_files:
        df_prev = pd.concat([clean_headers(pd.read_excel(f)) for f in paid_prev_files])
        df_prev.to_csv(paid_prev_path, index=False)
    elif os.path.exists(paid_prev_path):
        df_prev = pd.read_csv(paid_prev_path)
    else:
        df_prev = pd.DataFrame()

    if not df_alloc.empty and (not df_curr.empty or not df_prev.empty):
        df_paid_all = pd.concat([df_curr, df_prev], ignore_index=True)
        df_all = pd.merge(df_alloc, df_paid_all, on='Loan_ID', how='left')
        df_all['Paid_Amount'] = df_all['Paid_Amount'].fillna(0)
        df_all['Recovery %'] = (df_all['Paid_Amount'] / df_all['Allocated_Amount'] * 100).round(2)
        df_all['Balance'] = df_all['Allocated_Amount'] - df_all['Paid_Amount']

        st.markdown("### 📌 Merged Data")
        st.dataframe(df_all)

        st.markdown(f"### 📊 Summary for {process_name}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Allocated", f"₹{df_all['Allocated_Amount'].sum():,.0f}")
            st.metric("Total Paid", f"₹{df_all['Paid_Amount'].sum():,.0f}")
        with col2:
            st.metric("Recovery %", f"{df_all['Recovery %'].mean():.2f}%")
            st.metric("Total Balance", f"₹{df_all['Balance'].sum():,.0f}")

        if 'Bucket' in df_all.columns:
            st.markdown("### 📊 Recovery % by Bucket")
            bucket_df = df_all.groupby('Bucket').agg({
                'Allocated_Amount': 'sum',
                'Paid_Amount': 'sum'
            }).reset_index()
            bucket_df['Recovery %'] = (bucket_df['Paid_Amount'] / bucket_df['Allocated_Amount'] * 100).round(2)
            fig = px.bar(bucket_df, x='Bucket', y='Recovery %', color='Bucket', text='Recovery %')
            st.plotly_chart(fig, use_container_width=True)

        csv_report = df_all.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Merged Report", csv_report, file_name=f"{process_name}_report.csv")
    else:
        st.info("Upload allocation and paid files to see the summary.")
