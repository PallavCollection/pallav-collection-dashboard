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

st.set_page_config(page_title="📊 Pallav Collection Dashboard", layout="wide")

# 🧹 Removed dashboard title and caption here

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

# -- Utility Functions --
def clean_headers(df):
    df.columns = [col.strip().lower().replace(" ", "_").replace("(", "").replace(")", "") for col in df.columns]
    return df

def correct_column(df, desired_names):
    df = clean_headers(df)
    for name in desired_names:
        for col in df.columns:
            if col.strip().lower() == name:
                return col
    return None

def extract_required_columns(df, primary_options):
    df = clean_headers(df)
    selected_cols = {}
    for options in primary_options:
        match = correct_column(df, options)
        if match:
            selected_cols[options[0]] = match
    return df, selected_cols

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

def save_uploaded_file(uploaded_file, process_key, file_type):
    file_path = os.path.join(UPLOAD_DIR, f"{process_key}_{file_type}.xlsx")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())
    session.setdefault("uploads", {}).setdefault(process_key, {})[file_type] = file_path
    save_session(session)

def delete_uploaded_file(process_key, file_type):
    uploads = session.get("uploads", {}).get(process_key, {})
    file_path = uploads.get(file_type)
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
        del uploads[file_type]
        save_session(session)
        st.toast(f"Deleted {file_type.replace('_', ' ').title()} for {process_key}.", icon="🗑")

def delete_agent_file():
    if "agent_file" in st.session_state:
        del st.session_state["agent_file"]
        st.toast("Deleted agent performance file.", icon="🗑")

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

# -- Load config and session
config = load_config()
session = load_session()
now = datetime.now()

# -- Authentication
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
            session["user_email"] = email
            session["last_login"] = now.strftime("%Y-%m-%d %H:%M:%S")
            save_session(session)
            st.success("Logged in. Reloading...")
            st.rerun()
        else:
            st.error("Invalid credentials.")
    st.stop()

# -- Auto Refresh Dashboard Section
last_refresh = st.session_state.get("last_refresh")
if not last_refresh or datetime.now() - datetime.fromisoformat(last_refresh) > timedelta(minutes=15):
    st.session_state.last_refresh = datetime.now().isoformat()
    st.rerun()

# ✅ Removed this block:
# st.title(":bar_chart: Collection BPO Dashboard")
# st.caption(f"Last refreshed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# -- SIDEBAR UI
with st.sidebar:
    st.subheader(":file_folder: Manage Processes")
    for i in range(config["process_count"]):
        process_key = f"process_{i+1}"
        process_name = config["process_names"].get(process_key, f"Process_{i+1}")
        new_name = st.text_input(f"Rename {process_name}", value=process_name, key=f"name_{process_key}")
        config["process_names"][process_key] = new_name
    save_config(config)

    if st.button("➕ Add Process"):
        config["process_count"] += 1
        save_config(config)
        st.rerun()
    if config["process_count"] > 1 and st.button("➖ Remove Process"):
        config["process_count"] -= 1
        save_config(config)
        st.rerun()

    if st.button("🗑 Reset All Uploads"):
        st.session_state.clear()
        if os.path.exists(UPLOAD_DIR):
            for f in os.listdir(UPLOAD_DIR):
                os.remove(os.path.join(UPLOAD_DIR, f))
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        st.success("All uploaded files cleared. Please refresh.")

    if st.button("Logout"):
        session["last_login"] = None
        save_session(session)
        st.session_state.clear()
        st.rerun()

    st.markdown("---")
    st.subheader(":bust_in_silhouette: Upload Agent Performance")
    agent_cols = st.columns([5, 1])
    with agent_cols[0]:
        agent_file = st.file_uploader("Upload Agent Performance Excel", type=["xlsx"], key="agent_file")
    with agent_cols[1]:
        if st.button("🗑", key="delete_agent_file", help="Delete Agent File"):
            delete_agent_file()

    if agent_file:
        df_agent = pd.read_excel(agent_file)
        df_agent = clean_headers(df_agent)
        st.markdown("### 📟 Agent Performance Preview")
        st.dataframe(df_agent.head())

    st.markdown("---")
    st.subheader(":open_file_folder: Upload Files For All Processes")
    uploaded_files = {}
    for i in range(config["process_count"]):
        process_key = f"process_{i+1}"
        default_name = config["process_names"].get(process_key, f"Process_{i+1}")
        st.markdown(f"📁 *{default_name}*")

        alloc = st.file_uploader(f"📄 Allocation File ({default_name})", type=["xlsx"], key=f"alloc_{i}")
        paid_curr = st.file_uploader(f"🗕 Current Month Paid ({default_name})", type=["xlsx"], key=f"curr_{i}")
        paid_prev = st.file_uploader(f"🔒 Previous Month Paid ({default_name})", type=["xlsx"], key=f"prev_{i}")

        delete_col = st.columns(3)
        with delete_col[0]:
            if st.button("🗑", key=f"del_alloc_{i}", help=f"Delete Allocation File {i+1}"):
                delete_uploaded_file(process_key, "alloc")
        with delete_col[1]:
            if st.button("🗑", key=f"del_curr_{i}", help=f"Delete Paid Current File {i+1}"):
                delete_uploaded_file(process_key, "paid_curr")
        with delete_col[2]:
            if st.button("🗑", key=f"del_prev_{i}", help=f"Delete Paid Previous File {i+1}"):
                delete_uploaded_file(process_key, "paid_prev")

        if alloc: save_uploaded_file(alloc, process_key, "alloc")
        if paid_curr: save_uploaded_file(paid_curr, process_key, "paid_curr")
        if paid_prev: save_uploaded_file(paid_prev, process_key, "paid_prev")

        uploads = session.get("uploads", {}).get(process_key, {})
        if not alloc and uploads.get("alloc"): alloc = uploads["alloc"]
        if not paid_curr and uploads.get("paid_curr"): paid_curr = uploads["paid_curr"]
        if not paid_prev and uploads.get("paid_prev"): paid_prev = uploads["paid_prev"]

        uploaded_files[process_key] = {
            "name": default_name,
            "alloc": alloc,
            "paid_curr": paid_curr,
            "paid_prev": paid_prev
        }

# 📈 Reports Section
st.markdown("## 📈 Reports Section")
below_target_threshold = 75

# (report generation logic continues unchanged...)
