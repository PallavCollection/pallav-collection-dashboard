# Enhanced version of your original script
# Adds the following features:
# - Dashboard Filtering
# - Auto-refresh with st_autorefresh
# - Admin-Agent File Access Control
# - KPI Metrics
# - Hashed Passwords (bcrypt)
# - Date-wise Report Filtering
# - Basic AI Insight stub
# - Admin-only User Registration and Management
# - Password Reset Option
# - Optional Enhancements:
#   - Chart Titles/Labels
#   - Better PDF with sample data
#   - Column type detection
#   - File Deletion Option
#   - Multi-column Charting (X + multiple Y)

import streamlit as st
import pandas as pd
import os
import bcrypt
from datetime import datetime, timedelta
from io import BytesIO
from fpdf import FPDF
import zipfile
import sqlite3
import tempfile
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
CACHE_DIR = "cache"
UPLOAD_DIR = os.path.join(CACHE_DIR, "uploads")
DB_FILE = "database.db"
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- INIT DB ---
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    password BLOB,
    role TEXT
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    filename TEXT,
    content BLOB,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# --- INSERT DEFAULT ADMIN ---
def insert_default_admin():
    admin_email = "jjagarbattiudyog@gmail.com"
    admin_password = b"$2b$12$rVhN2hZpdA/mINSCjCynjO6GzTFfIonr9pN8awjg5iggVqNPHiYGS"  # Hashed "Sanu@1998"
    c.execute("SELECT * FROM users WHERE email=?", (admin_email,))
    if not c.fetchone():
        c.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (admin_email, admin_password, "admin"))
        conn.commit()

insert_default_admin()

# --- HELPERS ---
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

def register_user(email, password, role):
    c.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (email, hash_password(password), role))
    conn.commit()

def update_password(email, new_password):
    c.execute("UPDATE users SET password=? WHERE email=?", (hash_password(new_password), email))
    conn.commit()

def validate_user(email, password):
    c.execute("SELECT password, role FROM users WHERE email=?", (email,))
    result = c.fetchone()
    if result and check_password(password.encode(), result[0]):
        return result[1]
    return None

def save_file_to_db(email, filename, content):
    c.execute("INSERT INTO uploads (email, filename, content) VALUES (?, ?, ?)", (email, filename, content))
    conn.commit()

def get_user_files(email, role):
    if role == "admin":
        c.execute("SELECT filename, content, uploaded_at, email FROM uploads")
    else:
        c.execute("SELECT filename, content, uploaded_at, email FROM uploads WHERE email=?", (email,))
    return c.fetchall()

def delete_file(email, filename):
    if st.session_state.role == "admin":
        c.execute("DELETE FROM uploads WHERE filename=?", (filename,))
    else:
        c.execute("DELETE FROM uploads WHERE filename=? AND email=?", (filename, email))
    conn.commit()

# --- SESSION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.email = ""
    st.session_state.role = ""

# --- LOGIN / REGISTER ---
if not st.session_state.authenticated:
    tab1, tab2, tab3 = st.tabs(["Login", "Register (Admin Only)", "Reset Password"])

    with tab1:
        st.subheader("🔐 Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            role = validate_user(email, password)
            if role:
                st.session_state.authenticated = True
                st.session_state.email = email
                st.session_state.role = role
                st.success("Logged in successfully.")
                st.rerun()
            else:
                st.error("Invalid credentials.")

    with tab2:
        st.subheader("📝 Register New User (Admin Only)")
        if "role" in st.session_state and st.session_state.role == "admin":
            new_email = st.text_input("New Email")
            new_password = st.text_input("New Password", type="password")
            new_role = st.selectbox("Role", ["admin", "agent"])
            if st.button("Register"):
                try:
                    register_user(new_email, new_password, new_role)
                    st.success("User registered successfully.")
                except:
                    st.error("User already exists.")
        else:
            st.info("Only admins can register users.")

    with tab3:
        st.subheader("🔑 Reset Password")
        reset_email = st.text_input("Email for Reset")
        new_password = st.text_input("New Password", type="password")
        if st.button("Reset Password"):
            try:
                update_password(reset_email, new_password)
                st.success("Password updated successfully.")
            except:
                st.error("Failed to update password.")

    st.stop()

# --- AUTO REFRESH ---
st_autorefresh(interval=15 * 60 * 1000, key="auto_refresh")

# --- DASHBOARD ---
st.title("📊 Pallav Collection Dashboard")
st.caption(f"Logged in as: {st.session_state.email} ({st.session_state.role})")

if st.button("🚪 Logout"):
    st.session_state.authenticated = False
    st.session_state.email = ""
    st.session_state.role = ""
    st.rerun()

# --- ADMIN USER LIST ---
if st.session_state.role == "admin":
    st.subheader("👥 User Management (Admin Only)")
    c.execute("SELECT email, role FROM users")
    users = c.fetchall()
    for email, role in users:
        st.text(f"{email} - {role}")

# --- FILE UPLOAD ---
st.subheader("📂 Upload a File")
file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
if file:
    content = file.read()
    save_file_to_db(st.session_state.email, file.name, content)
    st.success(f"Uploaded: {file.name}")

# --- FILES & FILTERS ---
st.subheader("📄 Your Uploaded Files")
files = get_user_files(st.session_state.email, st.session_state.role)

# Filters
date_range = st.date_input("Select Date Range", [datetime.today() - timedelta(days=30), datetime.today()])
selected_user = None
if st.session_state.role == "admin":
    users = list(set([row[3] for row in files]))
    selected_user = st.selectbox("Filter by Agent", options=["All"] + users)

# Metrics
st.metric("Total Files", len(files))

# Insights stub
if len(files) > 5:
    st.info("💡 Insight: High file upload activity this month.")

# File Display
for name, content, uploaded_at, owner in files:
    if selected_user and selected_user != "All" and owner != selected_user:
        continue

    uploaded_date = datetime.strptime(uploaded_at.split(" ")[0], "%Y-%m-%d")
    if not (date_range[0] <= uploaded_date.date() <= date_range[1]):
        continue

    with st.expander(f"{name} ({owner})"):
        try:
            if name.endswith(".csv"):
                df = pd.read_csv(BytesIO(content))
            else:
                df = pd.read_excel(BytesIO(content))
        except Exception as e:
            st.error(f"Error reading file {name}: {e}")
            continue

        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        df = df.convert_dtypes()
        st.dataframe(df.head())

        if st.button(f"❌ Delete {name}", key=f"del_{name}"):
            delete_file(owner, name)
            st.success(f"Deleted: {name}")
            st.rerun()

        st.markdown("#### 📊 Select Analysis")
        col_options = df.columns.tolist()
        if len(col_options) < 2:
            st.warning("Not enough columns to plot.")
            continue

        x_axis = st.selectbox("X-axis", col_options, key=f"x_{name}")
        y_axes = st.multiselect("Y-axis", col_options, default=col_options[1], key=f"y_{name}")
        chart_type = st.selectbox("Chart Type", ["Bar", "Line", "Pie"], key=f"chart_{name}")
        chart_title = st.text_input("Chart Title", f"Chart for {name}", key=f"title_{name}")

        if st.button("📈 Generate Chart", key=f"plot_{name}"):
            try:
                chart_df = df[[x_axis] + y_axes].dropna()
                if chart_type == "Bar":
                    st.bar_chart(chart_df.set_index(x_axis))
                elif chart_type == "Line":
                    st.line_chart(chart_df.set_index(x_axis))
                elif chart_type == "Pie" and len(y_axes) == 1:
                    st.plotly_chart(px.pie(df, names=x_axis, values=y_axes[0], title=chart_title))
                else:
                    st.warning("Pie chart supports only one Y column.")
            except:
                st.warning("Unable to generate chart. Check selected columns.")

        st.download_button("⬇️ Download Excel", data=content, file_name=name)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Report for {name}", ln=True)
        for i, col in enumerate(df.columns[:10]):
            pdf.cell(200, 10, txt=f"{col}: {df[col].iloc[0]}", ln=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf.output(tmp.name)
            with open(tmp.name, "rb") as f:
                st.download_button("⬇️ Download PDF", f, file_name=name.replace(".xlsx", ".pdf"))

# --- ZIP EXPORT ---
st.subheader("📦 Export All as ZIP")
if st.button("Download ZIP"):
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zipf:
        for name, content, _, _ in files:
            zipf.writestr(name, content)
    st.download_button("⬇️ Download All Files (ZIP)", zip_buf.getvalue(), file_name="all_reports.zip")
