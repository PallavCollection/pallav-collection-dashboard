import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
from datetime import datetime, timedelta
from io import BytesIO

st.set_page_config(page_title="📊 BPO Collection Dashboard", layout="wide")

CACHE_DIR = "cache"
SESSION_FILE = "session.json"
CONFIG_FILE = os.path.join(CACHE_DIR, "config.json")
os.makedirs(CACHE_DIR, exist_ok=True)

PAID_COLUMNS = ['paid_amt', 'payment', 'paid_amount', 'recovery', 'paid']
ALLOC_COLUMNS = ['allocation', 'target', 'total_due']

# Utils
def clean_headers(df):
    df.columns = [col.strip().lower().replace(" ", "_").replace("(", "").replace(")", "") for col in df.columns]
    return df

def find_column(df, options):
    for col in df.columns:
        if col.lower() in options:
            return col
    return None

def load_config():
    if os.path.exists(CONFIG_FILE):
        return json.load(open(CONFIG_FILE))
    return {"process_count": 1, "process_names": {}}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)

def load_session():
    if os.path.exists(SESSION_FILE):
        return json.load(open(SESSION_FILE))
    return {}

def save_session(data):
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f)

def to_excel_download(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()

# Load
config = load_config()
session = load_session()
now = datetime.now()

if 'authenticated' not in st.session_state:
    if session.get("last_login"):
        last_login = datetime.strptime(session["last_login"], "%Y-%m-%d %H:%M:%S")
        if now - last_login < timedelta(hours=24):
            st.session_state.authenticated = True
            st.session_state.user_email = session.get("user_email", "")
        else:
            st.session_state.authenticated = False
    else:
        st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if email == "jjagarbattiudyog@gmail.com" and password == "Sanu@1998":
            st.session_state.authenticated = True
            st.session_state.user_email = email
            save_session({"user_email": email, "last_login": now.strftime("%Y-%m-%d %H:%M:%S")})
            st.success("Logged in. Reloading...")
            st.rerun()
        else:
            st.error("Invalid credentials.")
    st.stop()

st.title("📊 Collection BPO Dashboard")
st.info("Continue uploading allocation and paid files per process below...")

with st.sidebar:
    st.subheader("📁 Manage Processes")
    if st.button("➕ Add Process"):
        config["process_count"] += 1
        save_config(config)
        st.rerun()
    if config["process_count"] > 1 and st.button("➖ Remove Process"):
        config["process_count"] -= 1
        save_config(config)
        st.rerun()

    st.markdown("---")
    st.subheader("👤 Upload Agent Performance")
    agent_file = st.file_uploader("Upload Agent Performance Excel", type=["xlsx"], key="agent_file")

    st.markdown("---")
    st.subheader("📂 Upload Files For All Processes")
    uploaded_files = {}
    for i in range(config["process_count"]):
        process_key = f"process_{i+1}"
        default_name = config["process_names"].get(process_key, f"Process_{i+1}")
        st.markdown(f"**📁 {default_name}**")
        alloc = st.file_uploader(f"📤 Allocation File ({default_name})", type=["xlsx"], key=f"alloc_{i}")
        paid_curr = st.file_uploader(f"📅 Current Month Paid ({default_name})", type=["xlsx"], key=f"curr_{i}")
        uploaded_files[process_key] = {
            "name": default_name,
            "alloc": alloc,
            "paid_curr": paid_curr
        }

st.button("🔄 Refresh All")

# Agent Report
if agent_file:
    try:
        df = pd.read_excel(agent_file)
        df = clean_headers(df)
        st.subheader("👥 Agent Performance Report")
        st.dataframe(df)
        if 'agent_name' in df.columns and 'score' in df.columns:
            st.plotly_chart(px.bar(df, x='agent_name', y='score', color='week', title="Agent Score by Week"), use_container_width=True)
    except Exception as e:
        st.error(f"Agent report error: {e}")

# Summary collection
summary_data = []

for key, data in uploaded_files.items():
    st.markdown(f"### 📂 Reports for: {data['name']}")
    alloc_df, paid_df = None, None

    if data['alloc']:
        alloc_df = pd.read_excel(data['alloc'])
        alloc_df = clean_headers(alloc_df)
        st.subheader(f"📊 Allocation - {data['name']}")
        st.dataframe(alloc_df)

    if data['paid_curr']:
        paid_df = pd.read_excel(data['paid_curr'])
        paid_df = clean_headers(paid_df)
        st.subheader(f"💰 Paid - {data['name']}")
        st.dataframe(paid_df)

    if alloc_df is not None and paid_df is not None:
        alloc_col = find_column(alloc_df, ALLOC_COLUMNS)
        paid_col = find_column(paid_df, PAID_COLUMNS)

        if alloc_col and paid_col:
            total_target = alloc_df[alloc_col].sum()
            total_paid = paid_df[paid_col].sum()
            recovery_pct = (total_paid / total_target * 100) if total_target > 0 else 0
            shortfall = total_target - total_paid

            st.markdown(f"**🎯 Target:** ₹{total_target:,.0f}  |  **✅ Paid:** ₹{total_paid:,.0f}  |  **📉 Recovery:** {recovery_pct:.2f}%")

            summary_data.append({
                "Process": data['name'],
                "Target": total_target,
                "Paid": total_paid,
                "Recovery %": recovery_pct,
                "Shortfall": shortfall
            })

if summary_data:
    summary_df = pd.DataFrame(summary_data)
    st.subheader("📄 Summary Report")
    st.dataframe(summary_df)
    st.download_button("📥 Download Summary as Excel", data=to_excel_download(summary_df), file_name="bpo_summary_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
