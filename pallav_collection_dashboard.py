import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="📊 BPO Collection Dashboard", layout="wide")

def clean_headers(df):
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    return df

CACHE_DIR = "cache"
SESSION_FILE = "session.json"
CONFIG_FILE = os.path.join(CACHE_DIR, "config.json")
os.makedirs(CACHE_DIR, exist_ok=True)

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
    agent_file = st.file_uploader("Upload Agent Performance Excel", type=["xlsx"])
    if agent_file:
        agent_df = pd.read_excel(agent_file)
        agent_df = clean_headers(agent_df)
        st.dataframe(agent_df)

        if 'agent_name' in agent_df.columns and 'score' in agent_df.columns:
            fig = px.bar(agent_df, x='agent_name', y='score', color='week', title="Agent Score by Week")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Columns 'agent_name' and 'score' not found in uploaded agent file.")

    st.markdown("---")
    st.subheader("📂 Upload Files For All Processes")
    for i in range(config["process_count"]):
        process_key = f"process_{i+1}"
        default_name = config["process_names"].get(process_key, f"Process_{i+1}")
        st.markdown(f"**📁 {default_name}**")
        alloc = st.file_uploader(f"📤 Allocation File ({default_name})", type=["xlsx"], key=f"alloc_{i}_sidebar")
        paid_curr = st.file_uploader(f"📅 Current Month Paid ({default_name})", type=["xlsx"], key=f"curr_{i}_sidebar")
        paid_prev = st.file_uploader(f"🗓 Previous Month Paid ({default_name})", type=["xlsx"], key=f"prev_{i}_sidebar")

# Optional: Main section can show a welcome message or analysis
st.success("Use the left sidebar to manage processes and upload files.")
