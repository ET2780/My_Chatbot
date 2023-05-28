from flask import Flask, request, render_template
import openai
from os import getenv
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
openai.api_key = getenv('OPENAI_API_KEY')

# A dictionary to store user context
user_context = {}

states = ["start", "topic", "issue", "simulation"]

current_state = 0

def next_state():
    current_state += 1
    if current_state >= len(states):
        raise IndexError("trying to move to a state that does not exist")
    

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
    elif states[current_state] == "start":
        next_state()
        return "What type of interaction are we discussing today? Family? Work? Relationships?"
    elif states[current_state] == "issue":
        user_context['issue'] = userText
        next_state()
        return "what "
    elif states[current_state] == "topic":
        user_context["topic"] = userText
        next_state()
    elif states[current_state] == "simulation":
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"You are an AI trained in the principles of the book 'Crucial Conversations'. The user is having the following issue: {revised_issue_description(user_context['issue'])}. As the AI, you will simulate a conversation with the user where you play the role of the person involved in their issue. You will respond to their concerns, provide feedback, and guide them in using the principles of crucial conversations to navigate this difficult situation. After each response from the user, you will analyze their response, provide constructive feedback, and adjust your next response accordingly. At the end of the conversation, you will provide a summary of their performance and suggestions for improving their communication skills."
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

def revised_issue_description(original_issue: str) -> str:
    """
    Uses the OpenAI chat completion API
    with a special prompt that takes
    the original issue description and revises
    it such that it can serve as acting directions
    for an actor tasked with playing the character
    our user want to simulate a conversation with.

    Return:
        the acting directions
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are an AI trained in the principles of the book 'Crucial Conversations'. The user will describe an issue they are facing. As the AI, you will revise this issue description into acting directions for an actor tasked with playing the character the user wants to simulate a conversation with."
            },
            {
                "role": "user",
                "content": original_issue
            }
        ],
        max_tokens=1024,
        temperature=0.7,
    )
    acting_directions = response['choices'][0]['message']['content']
    return acting_directions


if __name__ == "__main__":
    app.run()
