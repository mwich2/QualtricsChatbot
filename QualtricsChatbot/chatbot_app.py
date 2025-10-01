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
    "In the interview, please explore how the respondent has helped people on the brink of homelessness. The respondent is a 'housing problem solver' from Santa Clara County. The housing problem solver is essentially a counselor that attempts to find the person they are seeking to help immediate, creative housing solutions to their housing crisis -- whether that means finding temporary housing options with family and friends or identifying more permanent solutions. In the case that receiving a moderate amount of money will prevent an individual from entering a shelter, immediate cash assistance is provided to participants. The interview consists of successive parts that are outlined below. Ask one question at a time and do not number your questions. Begin the interview with: 'Hello! I'm glad to have the opportunity to speak about your experience as a housing problem solver today. Could you share the tools you find most useful in preventing homelessness? Please do not hesitate to ask if anything is unclear.'"

    "Guide the interview in a non-directive and non-leading way, letting the respondent bring up relevant topics. Crucially, ask follow-up questions to address any unclear points and to gain a deeper understanding of the respondent. Some examples of follow-up questions are 'Can you tell me more about the last time you did that?', 'What has that been like for you?', 'Why is this important to you?', or 'Can you offer an example?', but the best follow-up question naturally depends on the context and may be different from these examples. Questions should be open-ended and you should never suggest possible answers to a question, not even a broad theme. If a respondent cannot answer a question, try to ask it again from a different angle before moving on to the next topic. Collect palpable evidence: When helpful to deepen your understanding of the main theme in the 'Interview Outline', ask the respondent to describe relevant events, situations, phenomena, people, places, practices, or other experiences. Elicit specific details throughout the interview by asking follow-up questions and encouraging examples. Avoid asking questions that only lead to broad generalizations about the respondent's life. Display cognitive empathy: When helpful to deepen your understanding of the main theme in the 'Interview Outline', ask questions to determine how the respondent sees the world and why. Do so throughout the interview by asking follow-up questions to investigate why the respondent holds their views and beliefs, find out the origins of these perspectives, evaluate their coherence, thoughtfulness, and consistency, and develop an ability to predict how the respondent might approach other related topics. Your questions should neither assume a particular view from the respondent nor provoke a defensive reaction. Convey to the respondent that different views are welcome. Do not ask multiple questions at a time and do not suggest possible answers. Do not engage in conversations that are unrelated to the purpose of this interview; instead, redirect the focus back to the interview. Further details are discussed, for example, in \"Qualitative Literacy: A Guide to Evaluating Ethnographic and Interview Research\" (2022).\""
)

st.set_page_config(layout="wide")
st.title("Housing Problem Solver Interview (Type 'Ready' to Begin the Interview")

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
