# 📊 BPO Collection Dashboard - Enhanced Persistent Version with File Delete Buttons

import streamlit as st 
import pandas as pd
import plotly.express as px
import os
import json
from datetime import datetime, timedelta
from io import BytesIO

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
        st.success(f"Deleted {file_type.replace('_', ' ').title()} for {process_key}.")

def load_saved_file(file_path):
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    return None

# Load config and session
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
st.info("Continue uploading allocation, current and previous paid files per process below...")

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

    if st.button("🗑 Reset All Uploads"):
        st.session_state.clear()
        if os.path.exists(UPLOAD_DIR):
            for f in os.listdir(UPLOAD_DIR):
                os.remove(os.path.join(UPLOAD_DIR, f))
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        st.success("All uploaded files cleared. Please refresh.")

    st.markdown("---")
    st.subheader("👤 Upload Agent Performance")
    agent_file = st.file_uploader("Upload Agent Performance Excel", type=["xlsx"], key="agent_file")

    st.markdown("---")
    st.subheader("📂 Upload Files For All Processes")
    uploaded_files = {}
    for i in range(config["process_count"]):
        process_key = f"process_{i+1}"
        default_name = config["process_names"].get(process_key, f"Process_{i+1}")
        st.markdown(f"📁 {default_name}")

        col1, col2, col3, col4 = st.columns([4, 2, 2, 2])

        with col1:
            alloc = st.file_uploader(f"📄 Allocation File ({default_name})", type=["xlsx"], key=f"alloc_{i}")
        with col2:
            if st.button(f"❌ Delete Allocation {i+1}"):
                delete_uploaded_file(process_key, "alloc")
        with col3:
            if st.button(f"❌ Delete Paid Curr {i+1}"):
                delete_uploaded_file(process_key, "paid_curr")
        with col4:
            if st.button(f"❌ Delete Paid Prev {i+1}"):
                delete_uploaded_file(process_key, "paid_prev")

        paid_curr = st.file_uploader(f"📅 Current Month Paid ({default_name})", type=["xlsx"], key=f"curr_{i}")
        paid_prev = st.file_uploader(f"🔒 Previous Month Paid ({default_name})", type=["xlsx"], key=f"prev_{i}")

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

st.button("🔄 Refresh All")
