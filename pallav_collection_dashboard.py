# 📊 Pallav Collection Dashboard - Full Final Version

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

# Paths
CACHE_DIR = "cache"
UPLOAD_DIR = os.path.join(CACHE_DIR, "uploads")
SESSION_FILE = "session.json"
CONFIG_FILE = os.path.join(CACHE_DIR, "config.json")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Column options
PAID_COLUMNS = ['paid_amt', 'payment', 'paid_amount', 'recovery', 'paid']
ALLOC_COLUMNS = ['allocation', 'target', 'total_due']
AGENT_COLUMNS = ['agent', 'agent_name']
DATE_COLUMNS = ['date', 'payment_date', 'paid_date']

# Functions
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

# Load state
config = load_config()
session = load_session()
now = datetime.now()

# Authentication
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

# ✅ Show Logo
try:
    st.image("pallav_logo.png", width=80)
except:
    st.warning("⚠️ Could not load logo from local path.")

# Title
st.title(":bar_chart: Pallav Collection Dashboard")
st.caption(f"Last refreshed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Sidebar
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

# Upload and Reports
uploaded_files = {}
below_target_threshold = 75

st.markdown("## 📈 Reports Section")

for i in range(config["process_count"]):
    process_key = f"process_{i+1}"
    process_name = config["process_names"].get(process_key, f"Process_{i+1}")
    st.markdown(f"📁 *{process_name}*")

    alloc = st.file_uploader(f"📄 Allocation File", type=["xlsx"], key=f"alloc_{i}")
    paid_curr = st.file_uploader(f"🗕 Current Paid File", type=["xlsx"], key=f"curr_{i}")
    paid_prev = st.file_uploader(f"🔒 Previous Paid File", type=["xlsx"], key=f"prev_{i}")

    if st.button("🗑", key=f"del_alloc_{i}", help="Delete Allocation File"):
        delete_uploaded_file(process_key, "alloc")
    if st.button("🗑", key=f"del_curr_{i}", help="Delete Current Paid File"):
        delete_uploaded_file(process_key, "paid_curr")
    if st.button("🗑", key=f"del_prev_{i}", help="Delete Previous Paid File"):
        delete_uploaded_file(process_key, "paid_prev")

    if alloc: save_uploaded_file(alloc, process_key, "alloc")
    if paid_curr: save_uploaded_file(paid_curr, process_key, "paid_curr")
    if paid_prev: save_uploaded_file(paid_prev, process_key, "paid_prev")

    uploads = session.get("uploads", {}).get(process_key, {})
    alloc_file = uploads.get("alloc")
    paid_curr_file = uploads.get("paid_curr")
    paid_prev_file = uploads.get("paid_prev")

    if alloc_file and paid_curr_file:
        try:
            df_alloc = clean_headers(pd.read_excel(alloc_file))
            df_curr = clean_headers(pd.read_excel(paid_curr_file))
            df_prev = clean_headers(pd.read_excel(paid_prev_file)) if paid_prev_file else pd.DataFrame()

            alloc_col = correct_column(df_alloc, ALLOC_COLUMNS)
            paid_col = correct_column(df_curr, PAID_COLUMNS)
            agent_col = correct_column(df_alloc, AGENT_COLUMNS)

            if not all([alloc_col, paid_col, agent_col]):
                st.warning(f"Missing required columns in uploaded files for {process_name}.")
                continue

            df_alloc = df_alloc[[agent_col, alloc_col]]
            df_curr = df_curr[[agent_col, paid_col]]
            df_prev = df_prev[[agent_col, paid_col]] if not df_prev.empty else pd.DataFrame()

            merged_df = df_alloc.merge(df_curr, on=agent_col, how="left").fillna(0)
            merged_df["% Recovery"] = (merged_df[paid_col] / merged_df[alloc_col]) * 100
            merged_df = merged_df.rename(columns={agent_col: "Agent", alloc_col: "Allocation", paid_col: "Paid"})

            st.subheader(f"📊 {process_name} Report")

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("🧾 Allocation", f"₹ {merged_df['Allocation'].sum():,.0f}")
            k2.metric("💰 Paid", f"₹ {merged_df['Paid'].sum():,.0f}")
            k3.metric("📈 Avg % Recovery", f"{merged_df['% Recovery'].mean():.2f}%")
            k4.metric("⚠ Below Target Agents", merged_df[merged_df["% Recovery"] < below_target_threshold].shape[0])

            st.dataframe(merged_df)

            st.plotly_chart(px.bar(merged_df, x="Agent", y="% Recovery", color="% Recovery", color_continuous_scale="Blues"))

            if not df_prev.empty:
                df_prev = df_prev.rename(columns={paid_col: "Paid_Last_Month", agent_col: "Agent"})
                hist_df = df_curr.rename(columns={paid_col: "Paid_Current_Month", agent_col: "Agent"}).merge(
                    df_prev[["Agent", "Paid_Last_Month"]], on="Agent", how="outer"
                ).fillna(0)
                hist_df = hist_df.melt(id_vars=["Agent"], value_vars=["Paid_Current_Month", "Paid_Last_Month"],
                                       var_name="Month", value_name="Paid Amount")
                fig_line = px.line(hist_df, x="Agent", y="Paid Amount", color="Month", markers=True)
                st.plotly_chart(fig_line)

            st.download_button("📥 Download Excel", to_excel_download(merged_df), file_name=f"{process_name}_report.xlsx")

            st.markdown("### 🧾 Agent PDFs")
            for _, row in merged_df.iterrows():
                with st.expander(f"📄 {row['Agent']}"):
                    pdf_path = generate_agent_pdf(row, process_name)
                    with open(pdf_path, "rb") as f:
                        st.download_button("⬇ Download PDF", data=f, file_name=f"{row['Agent']}.pdf", mime="application/pdf")

            st.markdown("---")

        except Exception as e:
            st.error(f"❌ Error: {e}")
    else:
        st.info(f"Upload Allocation and Current Paid for {process_name}.")
