from flask import Flask, request, jsonify
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(creds)

# Open Google Sheet (make sure you shared it with your service account email!)
sheet = gc.open("Interview Transcripts").sheet1

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message")

    # Get model response
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an interview assistant."},
            {"role": "user", "content": user_message}
        ]
    )
    assistant_message = response.choices[0].message["content"]

    # Save transcript to Google Sheets (append new row)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([timestamp, user_message, assistant_message])

    return jsonify({"response": assistant_message})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
