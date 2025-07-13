# 📊 Pallav Collection Dashboard

A secure, role-based internal dashboard built with **Streamlit** for file uploads, KPI visualization, and user access control.

## 🔐 Features

- Admin/Agent login with bcrypt password protection
- Admin-only:
  - Register new users
  - View all user accounts
- Password reset support for all users
- Upload & analyze Excel/CSV files
- Auto-refresh every 15 minutes
- Filter dashboard by date and agent (admin only)
- Download Excel and auto-generated PDF reports
- Export all files as ZIP
- Interactive charts (Bar, Line, Pie)
- SQLite backend – no external DB required

## 🚀 How to Deploy (e.g., on Render)

1. Clone the repo or copy the script
2. Add `requirements.txt`:
