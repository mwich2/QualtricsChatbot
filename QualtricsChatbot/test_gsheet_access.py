import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Authenticate using the service account info stored in Streamlit Secrets
gsheet_creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

gc = gspread.authorize(gsheet_creds)

# Replace with your Google Sheet ID
SHEET_ID = "1nmrZ0iJ_LCwE8KYFI1COe0XzZVHs0X7tqUm5jizIHDM"

try:
    sheet = gc.open_by_key(SHEET_ID).sheet1
    st.success("✅ Sheet opened successfully!")
    st.write(sheet.get_all_values())  # Print all data in the sheet
except Exception as e:
    st.error(f"Failed to open Google Sheet by key: {e}")
