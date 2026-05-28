import google.generativeai as genai
import os
from app.db import load_messages
from dotenv import load_dotenv
load_dotenv()

# configure API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("models/gemini-flash-latest")


def summarize_chat(room):
    messages = load_messages(room)

    if not messages:
        return "No messages to summarize."

    # combine messages
    text = "\n".join([f"{m['username']}: {m['message']}" for m in messages])

    prompt = f"""
    Summarize the following chat conversation in 2-3 lines:

    {text}
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating summary: {e}"