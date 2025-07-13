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

# ✅ Title updated here
st.title(":bar_chart: Pallav Collection Dashboard")
st.caption(f"Last refreshed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ✅ All other logic continues unmodified (managing processes, upload, charts, etc.)
# (Keep using the same full logic from your working version)
