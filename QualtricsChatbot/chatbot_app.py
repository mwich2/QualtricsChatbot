import streamlit as st
import openai
import json # Used to correctly format data sent back to Qualtrics

# --- 1. CONFIGURATION AND SECRETS ---
# The key is securely read from the Streamlit Secrets manager
try:
    openai_api_key = st.secrets["openai_api_key"]
except KeyError:
    st.error("OpenAI API key not found. Please configure it in Streamlit Secrets.")
    st.stop()

client = openai.OpenAI(api_key=openai_api_key)

# DEFINE THE AI PERSONA: Customize this prompt!
SYSTEM_MESSAGE = (
    "You are a neutral research assistant. Answer user questions about the survey topic. Act like you are interviewing a housing problem solver, someone who helps people on the brink of homelessness"
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

# Concatenate the full transcript
transcript_lines = [
    f'{m["role"].capitalize()}: {m["content"].replace("\\n", " ")}' 
    for m in st.session_state.messages 
    if m["role"] != "system"
]
full_transcript = " | ".join(transcript_lines)

# Add JavaScript to post the transcript to the Qualtrics parent window
# This script runs every time the page updates (i.e., when a new message is sent)
if full_transcript:
    # We send the transcript data as a JSON object
    data_to_send = {
        "type": "QualtricsDataTransfer",
        "data": full_transcript
    }

    # NOTE: This is the JavaScript that sends the data.
    # It assumes the Qualtrics survey is the parent window.
    st.components.v1.html(f"""
    <script>
    window.parent.postMessage({json.dumps(data_to_send)}, '*');
    </script>
    """, height=0, width=0)
