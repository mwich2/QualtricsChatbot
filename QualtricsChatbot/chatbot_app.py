import streamlit as st
import openai
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid  # For unique participant IDs

# --- 1. CONFIGURATION AND SECRETS ---

# OpenAI API key
try:
    openai_api_key = st.secrets["openai_api_key"]
except KeyError:
    st.error("OpenAI API key not found. Please configure it in Streamlit Secrets.")
    st.stop()

client = openai.OpenAI(api_key=openai_api_key)

# Google Sheets authentication using service account
try:
    gsheet_creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(gsheet_creds)
except KeyError:
    st.error("Google Sheets service account info not found in Streamlit Secrets.")
    st.stop()
except Exception as e:
    st.error(f"Failed to authorize Google Sheets: {e}")
    st.stop()

# Google Sheet ID
SHEET_ID = "1nmrZ0iJ_LCwE8KYFI1COe0XzZVHs0X7tqUm5jizIHDM"

try:
    sheet = gc.open_by_key(SHEET_ID).sheet1
except Exception as e:
    st.error(f"Failed to open Google Sheet by key: {e}")
    st.stop()

# --- 2. SYSTEM PROMPT (AI Persona) ---
SYSTEM_MESSAGE = (
    "In the interview, please explore how the respondent has helped people on the brink of homelessness. "
    "The respondent is a 'housing problem solver' from Santa Clara County. Ask one question at a time and do not number your questions. "
    "Begin the interview with: 'Hello! I'm glad to have the opportunity to speak about your experience as a housing problem solver today. "
    "Could you share the tools you find most useful in preventing homelessness? Please do not hesitate to ask if anything is unclear.'"
)

# --- 3. STREAMLIT PAGE SETUP ---
st.set_page_config(layout="wide")
st.title("Housing Problem Solver Interview")

# --- 4. SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "system", "content": SYSTEM_MESSAGE}]

if "participant_id" not in st.session_state:
    st.session_state["participant_id"] = str(uuid.uuid4())  # Unique ID per participant

st.caption(f"Participant ID: {st.session_state['participant_id']}")

# --- 5. START BUTTON ---
if "started" not in st.session_state:
    st.session_state["started"] = False

if not st.session_state["started"]:
    if st.button("Start Interview"):
        st.session_state["started"] = True
    else:
        st.stop()  # Do not show chat until interview is started

# --- 6. CHAT INTERFACE ---
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

prompt = st.chat_input("Ask the AI a question...")
if prompt:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI response
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

    # Add AI response to session
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # --- 7. AUTOMATIC STORAGE IN GOOGLE SHEETS ---
    try:
        transcript_lines = [
            f'{m["role"].capitalize()}: {m["content"].replace("\\n", " ")}'
            for m in st.session_state.messages
            if m["role"] != "system"
        ]
        full_transcript = " | ".join(transcript_lines)
        sheet.append_row([st.session_state["participant_id"], datetime.now().isoformat(), full_transcript])
    except Exception as e:
        st.error(f"Failed to save interview automatically: {e}")

# --- 8. OPTIONAL: SEND TO QUALTRICS ---
if st.session_state["messages"]:
    transcript_lines = [
        f'{m["role"].capitalize()}: {m["content"].replace("\\n", " ")}'
        for m in st.session_state.messages
        if m["role"] != "system"
    ]
    full_transcript = " | ".join(transcript_lines)
    data_to_send = {"type": "QualtricsDataTransfer", "data": full_transcript}
    st.components.v1.html(f"""
        <script>
        window.parent.postMessage({json.dumps(data_to_send)}, '*');
        </script>
    """, height=0, width=0)
