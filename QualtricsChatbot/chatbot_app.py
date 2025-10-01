import streamlit as st
import openai
import json  # Used to correctly format data sent back to Qualtrics
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIGURATION AND SECRETS ---
# OpenAI API key from Streamlit Secrets
try:
    openai_api_key = st.secrets["openai_api_key"]
except KeyError:
    st.error("OpenAI API key not found. Please configure it in Streamlit Secrets.")
    st.stop()

client = openai.OpenAI(api_key=openai_api_key)

# Define AI persona
SYSTEM_MESSAGE = (
    "You are a neutral research assistant. Answer user questions about the survey topic "
    "concisely (under 3 sentences) and politely. Do not ask any questions yourself."
)

st.set_page_config(layout="wide")
st.title("Qualtrics AI Assistant")

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": SYSTEM_MESSAGE}
    ]

# --- 2. RECEIVE DATA (QUALTRICS -> CHATBOT) ---
qualtrics_id = st.query_params.get("qualtrics_id", "NOT_FOUND")
if qualtrics_id != "NOT_FOUND":
    st.caption(f"Survey ID: {qualtrics_id} (Data linked)")

# --- 3. CHAT INTERFACE AND LOGIC ---
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if prompt := st.chat_input("Ask the AI a question..."):

    # Display user message and add to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        try:
            stream = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")

            message_placeholder.markdown(full_response)

        except Exception as e:
            full_response = f"Error: Could not connect to AI. ({e})"
            message_placeholder.error(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

# --- 4. DATA TRANSFER BACK (CHATBOT -> QUALTRICS) ---
transcript_lines = [
    f'{m["role"].capitalize()}: {m["content"].replace("\\n", " ")}' 
    for m in st.session_state.messages 
    if m["role"] != "system"
]
full_transcript = " | ".join(transcript_lines)

# Send transcript back to Qualtrics
if full_transcript:
    data_to_send = {
        "type": "QualtricsDataTransfer",
        "data": full_transcript
    }
    st.components.v1.html(f"""
    <script>
    window.parent.postMessage({json.dumps(data_to_send)}, '*');
    </script>
    """, height=0, width=0)

# --- 5. APPEND TRANSCRIPT TO GOOGLE SHEET ---
if full_transcript:
    # Google Sheets setup
    SERVICE_ACCOUNT_FILE = "/Users/matthewwich/Documents/QualtricsChatbot/qualtrics-473801-506590ec4293.json"  # <-- Replace with your JSON key path
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        gs_client = gspread.authorize(creds)

        SHEET_NAME = "QualtricsTranscripts"  # <-- Your Google Sheet name
        WORKSHEET_NAME = "Sheet1"  # <-- Your worksheet/tab name
        sheet = gs_client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

        # Append transcript with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, qualtrics_id, full_transcript]
        sheet.append_row(row)

    except Exception as e:
        st.error(f"Error writing to Google Sheet: {e}")
