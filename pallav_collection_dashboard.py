import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
from datetime import datetime, timedelta

# --- Auto Header Fixer ---
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
    "agentname": "Agent_Name",
    "agent_name": "Agent_Name"
}

def clean_headers(df):
    df.columns = [HEADER_MAPPING.get(col.strip().lower().replace(" ", "_"), col.strip().replace(" ", "_")) for col in df.columns]
    return df

# --- Paths and Files ---
SESSION_FILE = "session_data.json"
CACHE_DIR = "cache"
CONFIG_FILE = os.path.join(CACHE_DIR, "config.json")
os.makedirs(CACHE_DIR, exist_ok=True)

# --- Persistent Config ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"process_count": 1, "process_names": {}}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

config = load_config()

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

session_data = load_session()
now = datetime.now()

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
    login_btn = st.button("Login")

    if login_btn:
        if authenticate_user(email, password):
            st.session_state.authenticated = True
            st.session_state.user_email = email
            session_data = {'last_login': now.strftime("%Y-%m-%d %H:%M:%S"), 'user_email': email}
            save_session(session_data)
            st.success("✅ Logged in successfully!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials. View-only mode enabled.")
else:
    st.set_page_config(page_title="✨ Beautiful Collection Dashboard", layout="wide")
    st.markdown("<h1 style='text-align: center; color: navy;'>📊 Collection BPO Dashboard</h1>", unsafe_allow_html=True)

    is_editor = st.session_state.user_email == "jjagarbattiudyog@gmail.com"

    if is_editor:
        with st.sidebar:
            if st.button("➕ Add Process"):
                config['process_count'] += 1
                save_config(config)
            if config['process_count'] > 1 and st.button("➖ Remove Process"):
                config['process_count'] -= 1
                save_config(config)

    st.sidebar.markdown("---")
    st.sidebar.subheader("👤 Upload Agent Performance")
    agent_file = st.sidebar.file_uploader("Upload Agent Performance Excel", type=["xlsx"])
    if agent_file:
        agent_df = pd.read_excel(agent_file)
        agent_df = clean_headers(agent_df)

        st.subheader("👤 Agent Performance")
        st.dataframe(agent_df, use_container_width=True)

        if "Agent_Name" in agent_df.columns and "Score" in agent_df.columns:
            fig = px.bar(agent_df, x="Agent_Name", y="Score", color="Rank", title="Agent Scores")
            st.plotly_chart(fig, use_container_width=True)
            csv = agent_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Agent Report", csv, file_name="agent_report.csv")
        else:
            st.warning("⚠️ Required columns missing: 'Agent_Name' and 'Score'")

    st.sidebar.markdown("---")
    st.info("Continue uploading allocation and paid files per process below...")
