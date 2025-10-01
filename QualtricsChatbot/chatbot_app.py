import streamlit as st
from openai import OpenAI
import json
import os

# --- 0. Setup ---
# Set page configuration for a cleaner embedded look
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
        /* Hide Streamlit default header and footer */
        .stDeployButton, #MainMenu, footer { visibility: hidden; }
        /* Remove padding around the chat to make it fit better in an iframe */
        .main, .block-container {
            padding-top: 1rem;
            padding-right: 1rem;
            padding-left: 1rem;
            padding-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

# Initialize OpenAI client (replace with your actual API key or use environment variable)
# client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) # Recommended for deployment
# For a local test, you can use:
try:
    openai_api_key = st.secrets["openai_api_key"]
except Exception:
    st.error("OpenAI client initialization failed. Please check your API key.")
    st.stop()


# --- 1. Get Context from Query Parameters ---
# st.query_params provides a dictionary-like interface to URL query parameters
query_params = st.query_params

# Set up initial context variables (default values for testing)
context = {
    "name": query_params.get("name", ["Participant"])[0],
    "Q_E_ID": query_params.get("Q_E_ID", ["TEST_ID_123"])[0],
    # Add other context variables from Qualtrics here
}


# --- 2. Initialize State and System Prompt ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []
    
    # Custom system prompt that incorporates the context
    system_prompt = (
        f"You are a helpful, friendly, and concise survey assistant chatbot. "
        f"The current user is named {context['name']} and their Qualtrics ID is {context['Q_E_ID']}. "
        "Keep your answers short and conversational. Your goal is to provide a brief interaction "
        "and then encourage them to click the 'End Chat & Submit Data' button. "
        "Do not offer to submit data yourself, only encourage the button use."
    )
    st.session_state["messages"].append({"role": "system", "content": system_prompt})
    
    # Start the conversation
    initial_message = f"Hello {context['name']}! I'm your survey assistant. How can I help you today?"
    st.session_state["messages"].append({"role": "assistant", "content": initial_message})

# --- Display Messages ---
st.title("Qualtrics Chatbot Demo")
for message in st.session_state["messages"]:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- 3. Chatbot Logic & 4. User Input ---
if prompt := st.chat_input("Ask me a question..."):
    # Add user message to history
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    try:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Prepare messages for the API (exclude the system prompt at index 0, it's already used)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo", # Use your preferred model
                    messages=st.session_state["messages"][1:] # Skip system prompt for API call
                )
                assistant_response = response.choices[0].message.content
                st.markdown(assistant_response)
        
        # Add assistant response to history
        st.session_state["messages"].append({"role": "assistant", "content": assistant_response})
    
    except Exception as e:
        error_message = f"An error occurred with the AI service: {e}"
        st.session_state["messages"].append({"role": "assistant", "content": error_message})
        st.error(error_message)


# --- 5. Final Submission Button & postMessage Logic ---

def submit_data_to_qualtrics():
    """
    Function to prepare data and inject JavaScript for postMessage.
    """
    # 1. Prepare Data
    # Get all user and assistant messages (skip system prompt at index 0)
    chat_transcript = [
        f"{msg['role'].title()}: {msg['content']}"
        for msg in st.session_state["messages"]
        if msg["role"] != "system"
    ]
    
    final_data = {
        "chat_log": "\n---\n".join(chat_transcript),
        "total_messages": len(st.session_state["messages"]) - 1, # Exclude system prompt
        "interaction_complete": "True",
        # Pass back context data to ensure Qualtrics can match it up
        "Q_E_ID_FROM_BOT": context["Q_E_ID"], 
        # Add any other derived data
    }

    # 2. Encode Data for JavaScript
    # Convert Python dict to a JSON string for safe transmission
    json_data = json.dumps(final_data)
    
    # 3. Create JavaScript postMessage string
    # The message sent to the parent window is a JSON object string.
    # The targetOrigin MUST be set to the origin of your Qualtrics survey page.
    # Using '*' is for demonstration/debugging but is INSECURE in production.
    # A safe origin would be like 'https://youruni.qualtrics.com'
    # Qualtrics uses nested iframes, so we use window.parent.parent.postMessage or similar.
    js_code = f"""
        <script>
            console.log("Sending message to parent window...");
            // Use window.parent.postMessage or potentially window.parent.parent.postMessage
            // You may need to experiment with how deep the parent is depending on Qualtrics setup.
            window.parent.postMessage({json_data}, '*');
            console.log("Message sent: " + {json_data});
        </script>
    """
    
    # 4. Inject JavaScript into Streamlit
    # st.components.v1.html allows you to inject raw HTML/JavaScript
    st.components.v1.html(js_code, height=0, width=0)
    
    # Final Streamlit message
    st.success("Data submitted! You can now proceed in the survey.")
    st.snow()
    
    # Optional: Disable chat input after submission
    st.session_state["chat_submitted"] = True


if "chat_submitted" not in st.session_state:
    st.session_state["chat_submitted"] = False

if not st.session_state["chat_submitted"]:
    # The final button to trigger the data submission
    st.button(
        "End Chat & Submit Data", 
        on_click=submit_data_to_qualtrics,
        use_container_width=True
    )
else:
    # After submission, display a final message and keep the chat history static
    st.info("The chat transcript has been saved and submitted to the survey. Please continue to the next page.")

# Optional: Displaying context data for debugging
with st.expander("Debug Information"):
    st.write("Context from URL Parameters:", context)
    st.write("Full Session State:", st.session_state)
