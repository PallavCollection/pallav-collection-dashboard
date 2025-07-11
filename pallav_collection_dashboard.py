import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="📊 BPO Collection Dashboard", layout="wide")

# --- Header cleaning ---
def clean_headers(df):
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    return df

# --- Paths ---
CACHE_DIR = "cache"
SESSION_FILE = "session.json"
CONFIG_FILE = os.path.join(CACHE_DIR, "config.json")
os.makedirs(CACHE_DIR, exist_ok=True)

# --- Config & Session Load/Save ---
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

# --- Auth ---
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

# --- UI ---
st.title("📊 Collection BPO Dashboard")
st.info("Continue uploading allocation and paid files per process below...")

# Agent Performance Upload
with st.sidebar:
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

# Process Management
with st.sidebar:
    st.markdown("---")
    if st.button("➕ Add Process"):
        config["process_count"] += 1
        save_config(config)
        st.rerun()
    if config["process_count"] > 1 and st.button("➖ Remove Process"):
        config["process_count"] -= 1
        save_config(config)
        st.rerun()

# Main Panel
for i in range(config["process_count"]):
    process_key = f"process_{i+1}"
    name_key = f"name_input_{i}"
    default_name = config["process_names"].get(process_key, f"Process_{i+1}")
    st.subheader(f"📂 {default_name}")
    new_name = st.text_input("Name", value=default_name, key=name_key)
    config["process_names"][process_key] = new_name
    save_config(config)

    alloc_path = f"{CACHE_DIR}/alloc_{new_name}.csv"
    paid_curr_path = f"{CACHE_DIR}/paid_curr_{new_name}.csv"
    paid_prev_path = f"{CACHE_DIR}/paid_prev_{new_name}.csv"

    alloc_file = st.file_uploader("📤 Allocation File", type="xlsx", key=f"alloc_{i}")
    if alloc_file:
        df_alloc = clean_headers(pd.read_excel(alloc_file))
        df_alloc.to_csv(alloc_path, index=False)
        st.success("✅ Allocation uploaded.")

    paid_curr_file = st.file_uploader("📅 Current Month Paid", type="xlsx", key=f"curr_{i}")
    if paid_curr_file:
        df_curr = clean_headers(pd.read_excel(paid_curr_file))
        df_curr.to_csv(paid_curr_path, index=False)
        st.success("✅ Current paid uploaded.")

    paid_prev_file = st.file_uploader("🗓 Previous Month Paid", type="xlsx", key=f"prev_{i}")
    if paid_prev_file:
        df_prev = clean_headers(pd.read_excel(paid_prev_file))
        df_prev.to_csv(paid_prev_path, index=False)
        st.success("✅ Previous paid uploaded.")

    with st.expander("🧹 Delete Uploaded Files"):
        if os.path.exists(alloc_path) and st.button("🗑 Delete Allocation", key=f"del_alloc_{i}"):
            os.remove(alloc_path)
            st.rerun()
        if os.path.exists(paid_curr_path) and st.button("🗑 Delete Current Paid", key=f"del_curr_{i}"):
            os.remove(paid_curr_path)
            st.rerun()
        if os.path.exists(paid_prev_path) and st.button("🗑 Delete Previous Paid", key=f"del_prev_{i}"):
            os.remove(paid_prev_path)
            st.rerun()

    # Data Processing
    if all([os.path.exists(p) for p in [alloc_path, paid_curr_path, paid_prev_path]]):
        df_alloc = pd.read_csv(alloc_path)
        df_curr = pd.read_csv(paid_curr_path)
        df_prev = pd.read_csv(paid_prev_path)

        df_all_paid = pd.concat([df_curr, df_prev], ignore_index=True)
        df_merge = pd.merge(df_alloc, df_all_paid, on="loan_id", how="left")

        df_merge["paid_amount"] = df_merge["paid_amount"].fillna(0)
        df_merge["recovery_pct"] = (df_merge["paid_amount"] / df_merge["allocated_amount"] * 100).round(2)
        df_merge["balance"] = df_merge["allocated_amount"] - df_merge["paid_amount"]

        st.dataframe(df_merge.head())

        st.metric("Total Allocated", f"₹{df_merge['allocated_amount'].sum():,.0f}")
        st.metric("Total Paid", f"₹{df_merge['paid_amount'].sum():,.0f}")
        st.metric("Recovery %", f"{df_merge['recovery_pct'].mean():.2f}%")

        if "bucket" in df_merge.columns:
            bucket_df = df_merge.groupby("bucket")[["allocated_amount", "paid_amount"]].sum().reset_index()
            bucket_df["recovery_pct"] = (bucket_df["paid_amount"] / bucket_df["allocated_amount"] * 100).round(2)
            fig = px.bar(bucket_df, x="bucket", y="recovery_pct", title="Recovery % by Bucket", color="bucket", text="recovery_pct")
            st.plotly_chart(fig, use_container_width=True)
