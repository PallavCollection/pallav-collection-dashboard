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

# 👤 Agent Performance Pivot Table
st.markdown("## 👤 Agent Performance Pivot Table")
if "agent_file" in st.session_state:
    try:
        df_agent = pd.read_excel(st.session_state["agent_file"])
        df_agent = clean_headers(df_agent)

        from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

        pivot_key = "agent_pivot_settings"
        saved_grid = session.get(pivot_key)

        gb = GridOptionsBuilder.from_dataframe(df_agent)

        for col in df_agent.columns:
            if pd.api.types.is_numeric_dtype(df_agent[col]):
                gb.configure_column(col, type=["numericColumn", "numberColumnFilter", "customNumericFormat"], aggFunc='sum')
            else:
                gb.configure_column(col, rowGroup=True, enableRowGroup=True, enablePivot=True, enableValue=True)

        gb.configure_default_column(filter=True, editable=True, groupable=True)
        gb.configure_side_bar()
        gb.configure_selection("multiple", use_checkbox=True)

        # Custom field: Paid % = paid / allocation
        paid_col = correct_column(df_agent, PAID_COLUMNS)
        alloc_col = correct_column(df_agent, ALLOC_COLUMNS)
        if paid_col and alloc_col and "paid_percent" not in df_agent.columns:
            df_agent["paid_percent"] = (df_agent[paid_col] / df_agent[alloc_col]) * 100

        # Conditional formatting
        highlight_low_recovery = JsCode("""
            function(params) {
                if (params.colDef.field === 'recovery' && params.value < 1000) {
                    return {'backgroundColor': '#ffe6e6'};
                }
            }
        """)
        if "recovery" in df_agent.columns:
            gb.configure_column("recovery", cellStyle=highlight_low_recovery)

        grid_options = gb.build()

        if saved_grid:
            grid_options.update(saved_grid)

        st.subheader("📌 Drag columns to pivot/group/aggregate")
        grid_return = AgGrid(
            df_agent,
            gridOptions=grid_options,
            enable_enterprise_modules=True,
            allow_unsafe_jscode=True,
            update_mode="MODEL_CHANGED",
            height=500,
            fit_columns_on_grid_load=True
        )

        edited_df = pd.DataFrame(grid_return["data"])
        session[pivot_key] = grid_return["gridOptions"]
        save_session(session)

        # Visual chart (example)
        st.markdown("### 📊 Recovery by Agent")
        agent_col = correct_column(edited_df, AGENT_COLUMNS)
        if agent_col and paid_col:
            chart_df = edited_df.groupby(agent_col)[paid_col].sum().reset_index()
            fig = px.bar(chart_df, x=agent_col, y=paid_col, title="Total Recovery by Agent")
            st.plotly_chart(fig, use_container_width=True)

        # Download
        st.markdown("### 📤 Download Modified Table")
        download_data = to_excel_download(edited_df)
        st.download_button("⬇ Download as Excel", data=download_data, file_name="agent_performance_pivot.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        st.warning(f"Error loading pivot table: {e}")
        st.dataframe(df_agent)
else:
    st.info("📤 Please upload Agent Performance file from the sidebar to view pivot table.")
