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

# Utility functions
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

# Load config and session
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

# Auto refresh every 15 minutes
last_refresh = st.session_state.get("last_refresh")
if not last_refresh or datetime.now() - datetime.fromisoformat(last_refresh) > timedelta(minutes=15):
    st.session_state.last_refresh = datetime.now().isoformat()
    st.rerun()

st.title("📊 Pallav Collection Dashboard")
st.caption(f"Last refreshed at {now.strftime('%Y-%m-%d %H:%M:%S')}")

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
        st.session_state.authenticated = False
        st.success("Logged out successfully.")
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
        st.markdown(f"📁 {default_name}")

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

for process_key, files in uploaded_files.items():
    name = files["name"]
    alloc_file = files.get("alloc")
    paid_file = files.get("paid_curr")

    if not alloc_file or not paid_file:
        st.warning(f"⚠ Skipping {name} - Allocation or Paid file missing.")
        continue

    try:
        df_alloc = pd.read_excel(alloc_file)
        df_paid = pd.read_excel(paid_file)
        df_alloc = clean_headers(df_alloc)
        df_paid = clean_headers(df_paid)

        alloc_col = correct_column(df_alloc, ALLOC_COLUMNS)
        paid_col = correct_column(df_paid, PAID_COLUMNS)
        agent_col_alloc = correct_column(df_alloc, AGENT_COLUMNS)
        agent_col_paid = correct_column(df_paid, AGENT_COLUMNS)

        if not alloc_col or not paid_col:
            st.warning(f"❌ Could not find required columns in {name}.")
            continue

        alloc_summary = df_alloc.groupby(agent_col_alloc).agg(
            Target_Amount=(alloc_col, "sum"),
            Allocation_Count=(alloc_col, "count")
        ).reset_index()

        paid_summary = df_paid.groupby(agent_col_paid).agg(
            Paid_Amount=(paid_col, "sum"),
            Paid_Count=(paid_col, "count")
        ).reset_index()

        merged = pd.merge(alloc_summary, paid_summary, left_on=agent_col_alloc, right_on=agent_col_paid, how="outer").fillna(0)
        merged["Recovery %"] = (merged["Paid_Amount"] / merged["Target_Amount"] * 100).round(2)
        merged = merged.rename(columns={agent_col_alloc: "Agent"})

        st.markdown(f"### 📌 Summary for {name}")
        st.dataframe(merged)

        st.plotly_chart(px.bar(merged, x="Agent", y=["Target_Amount", "Paid_Amount"], barmode="group", title=f"{name} - Amount Comparison"), use_container_width=True)
        st.plotly_chart(px.bar(merged, x="Agent", y=["Allocation_Count", "Paid_Count"], barmode="group", title=f"{name} - Count Comparison"), use_container_width=True)

        # Daily Trend
        date_col = correct_column(df_paid, DATE_COLUMNS)
        if date_col:
            df_paid[date_col] = pd.to_datetime(df_paid[date_col], errors='coerce')
            df_paid['payment_date_only'] = df_paid[date_col].dt.date
            trend_curr = df_paid.groupby('payment_date_only')[paid_col].sum().reset_index()
            trend_curr.columns = ['Date', 'Current Paid']

            trend_merged = trend_curr.copy()
            paid_prev_file = files.get("paid_prev")
            if paid_prev_file:
                df_prev = pd.read_excel(paid_prev_file)
                df_prev = clean_headers(df_prev)
                prev_paid_col = correct_column(df_prev, PAID_COLUMNS)
                prev_date_col = correct_column(df_prev, DATE_COLUMNS)
                if prev_paid_col and prev_date_col:
                    df_prev[prev_date_col] = pd.to_datetime(df_prev[prev_date_col], errors='coerce')
                    df_prev['payment_date_only'] = df_prev[prev_date_col].dt.date
                    trend_prev = df_prev.groupby('payment_date_only')[prev_paid_col].sum().reset_index()
                    trend_prev.columns = ['Date', 'Previous Paid']
                    trend_merged = pd.merge(trend_curr, trend_prev, on='Date', how='outer').fillna(0)

            trend_merged = trend_merged.sort_values("Date")
            fig_trend = px.line(trend_merged, x="Date", y=["Current Paid", "Previous Paid"], title=f"{name} - Daily Payment Trend")
            st.plotly_chart(fig_trend, use_container_width=True)

        below_target = merged[merged["Recovery %"] < below_target_threshold]
        if not below_target.empty:
            st.warning(f"🔻 Agents below {below_target_threshold}% recovery for {name}:")
            st.dataframe(below_target[["Agent", "Recovery %"]])

    except Exception as e:
        st.error(f"⚠ Error generating report for {name}: {e}")
# -----------------------------
# 📊 General Pivot Table Section
# -----------------------------
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

st.markdown("---")
st.header("📊 General Pivot Table Report")

pivot_file = st.file_uploader("Upload any Excel file for Pivot Table Report", type=["xlsx"], key="pivot_any_file")

if pivot_file:
    try:
        df_pivot_raw = pd.read_excel(pivot_file)
        df_pivot_raw = clean_headers(df_pivot_raw)

        st.markdown("### 🔍 Data Preview")
        st.dataframe(df_pivot_raw.head(10))

        all_columns = df_pivot_raw.columns.tolist()

        with st.form("pivot_settings_form"):
            st.markdown("### 🛠 Pivot Table Settings")
            col1, col2, col3 = st.columns(3)

            with col1:
                index_col = st.selectbox("Row (Index)", all_columns)
            with col2:
                column_col = st.selectbox("Column (Pivot)", all_columns)
            with col3:
                value_col = st.selectbox("Values (Aggregation)", all_columns)

            agg_func = st.selectbox("Aggregation Function", ["sum", "mean", "count", "max", "min"])
            submitted = st.form_submit_button("Generate Pivot")

        if submitted:
            pivot_result = pd.pivot_table(
                df_pivot_raw,
                index=index_col,
                columns=column_col,
                values=value_col,
                aggfunc=agg_func,
                fill_value=0,
                margins=True,
                margins_name="Total"
            )

            st.markdown("### 📊 Pivot Table Result")
            st.dataframe(pivot_result)

            st.markdown("### 🧾 Interactive Grid")
            gb = GridOptionsBuilder.from_dataframe(pivot_result.reset_index())
            gb.configure_pagination()
            gb.configure_default_column(editable=False, groupable=True)
            gb.configure_grid_options(domLayout='normal')
            gridOptions = gb.build()

            AgGrid(
                pivot_result.reset_index(),
                gridOptions=gridOptions,
                enable_enterprise_modules=False,
                allow_unsafe_jscode=True,
                theme="blue"
            )

    except Exception as e:
        st.error(f"Failed to generate pivot table: {e}")
