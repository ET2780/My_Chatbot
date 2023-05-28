from flask import Flask, request, render_template
import openai
from os import getenv
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
openai.api_key = getenv('OPENAI_API_KEY')

# A dictionary to store user context
user_context = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get")
def get_bot_response():
    userText = request.args.get('msg')
    if userText.lower() == "i'm done":
        summary = "Here's a summary of the simulation and your performance:"
        # Add your summary and suggestions here
        suggestions = """
        1. Suggestion 1
        2. Suggestion 2
        3. Suggestion 3
        """
        return summary + suggestions
    elif not user_context:
        user_context['issue'] = userText
        return "Can you tell me more about this issue? What do you do for a living and who is involved in this issue?"
    else:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"You are an AI trained in the principles of the book 'Crucial Conversations'. The user is having the following issue: {user_context['issue']}. As the AI, you will simulate a conversation with the user where you play the role of the person involved in their issue. You will respond to their concerns, provide feedback, and guide them in using the principles of crucial conversations to navigate this difficult situation. After each response from the user, you will analyze their response, provide constructive feedback, and adjust your next response accordingly. At the end of the conversation, you will provide a summary of their performance and suggestions for improving their communication skills."
                },
                {
                    "role": "user",
                    "content": userText
                }
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        answer = response['choices'][0]['message']['content']
        return str(answer)

if __name__ == "__main__":
    app.run()
