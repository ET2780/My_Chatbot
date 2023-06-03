from flask import Flask, request, render_template
import openai
from os import getenv
from dotenv import load_dotenv
load_dotenv()
from openai.error import RateLimitError

app = Flask(__name__)
openai.api_key = getenv('OPENAI_API_KEY')

# A dictionary to store user context
user_context = {
    'conversation_history': []
}

states = ["intro",  "name", "conversation_with", "traits", "situation", "goal", "simulation", "Results"]

current_state = 0

def next_state():
    global current_state
    current_state += 1
    if current_state >= len(states):
        raise IndexError("trying to move to a state that does not exist")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get")
def get_bot_response():
    userText = request.args.get('msg')
    print(f"User text: {userText}")  # Print the user's input

    if states[current_state] == "simulation":
        if userText.lower() == "finish simulation":
            acting_directions = user_context['traits'] + "\n" + user_context['situation'] + "\n" + user_context['goal']
            suggestions = generate_suggestions(user_context['conversation_history'], acting_directions)
            return suggestions
        else:
            # Continue the simulation

            # Add the user's input to the conversation history
            user_context['conversation_history'].append({
                "role": "user",
                "content": userText
            })

            acting_directions_issue = user_context['traits']
            acting_directions_situation = user_context['situation']
            acting_directions_goal = user_context['goal']
            acting_directions = acting_directions_issue + "\n" + acting_directions_situation + "\n" + acting_directions_goal

            # Create the messages array for the API call
            messages = [
                {
                    "role": "system",
                    "content": f"You are an AI mentor creating a conversation simulation with the user, using these acting directions: {acting_directions}. You are playing the role of {user_context['conversation_with']}."
                },
                {
                    "role": user_context['conversation_with'],
                    "content": "Start the conversation."
                }
            ] + user_context['conversation_history']

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=1024,
                    temperature=0.7,
                )
            except RateLimitError:
                return "I'm sorry, but I'm currently overloaded with requests. Please try again later or reload the bot."

            # Extract the assistant's message from the response
            assistant_message = response['choices'][0]['message']['content']

            # Add the assistant's message to the conversation history
            user_context['conversation_history'].append({
                "role": "assistant",
                "content": assistant_message
            })

            return str(assistant_message)

    # Handle other stages of the conversation
    next_state()
    if states[current_state] == "intro":
        return "Welcome to the conversation simulation. What is your name?"
    elif states[current_state] == "name":
        user_context['name'] = userText
        return f"Nice to meet you, {user_context['name']}! Who is your conversation with?"
    elif states[current_state] == "conversation_with":
        user_context['conversation_with'] = userText
        return "Describe this person's traits that are relevant to this situation and your relationship."
    elif states[current_state] == "traits":
        user_context['traits'] = userText
        return "What is the situation that led to this conversation?"
    elif states[current_state] == "situation":
        user_context['situation'] = userText
        return "What is your goal in this conversation? What do you hope to achieve?"
    elif states[current_state] == "goal":
        user_context['goal'] = userText
        return "Thank you for providing all the details. Now, let's start the simulation. Please start the conversation as you would in real life. In order to end the conversation, type: 'Finish simulation'"

def generate_suggestions(conversation_history, acting_directions):
    """
    Generates suggestions based on the conversation history and acting directions.

    Args:
        conversation_history (list): List of conversation messages.
        acting_directions (str): Acting directions for the simulation.

    Returns:
        str: Suggestions and feedback based on crucial conversation rules.
    """
    acting_directions_issue = acting_directions.split("\n")[0]
    acting_directions_situation = acting_directions.split("\n")[1]
    acting_directions_goal = acting_directions.split("\n")[2]

    # Construct messages with system, user, and assistant roles
    messages = [
        {"role": "system", "content": "You are an AI mentor providing suggestions based on crucial conversation rules."},
        {"role": "user", "content": "What are some suggestions for how I could improve?"}
    ] + conversation_history

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )
    except RateLimitError:
        return "I'm sorry, but I'm currently overloaded with requests. Please try again later or reload the bot."

    suggestions = response['choices'][0]['message']['content']
    feedback = provide_feedback(conversation_history, acting_directions_issue, acting_directions_situation, acting_directions_goal)

    return suggestions + "\n\n" + feedback

def provide_feedback(conversation_history, acting_directions_issue, acting_directions_situation, acting_directions_goal):
    """
    Provides feedback based on the crucial conversation rules and the conversation history.

    Args:
        conversation_history (list): List of conversation messages.
        acting_directions_issue (str): Acting directions related to the issue.
        acting_directions_situation (str): Acting directions related to the situation.
        acting_directions_goal (str): Acting directions related to the goal.

    Returns:
        str: Feedback based on crucial conversation rules.
    """
    # Extract user messages from the conversation history
    user_messages = [message["content"] for message in conversation_history if message["role"] == "user"]

    # Example: Check if any user message doesn't align with crucial conversation rules
    noncompliant_messages = []

    for message in user_messages:
        if not check_alignment_with_rules(message):
            noncompliant_messages.append(message)

    feedback = ""

    if len(noncompliant_messages) > 0:
        feedback += "Based on crucial conversation rules, the following messages could be improved:\n\n"
        for message in noncompliant_messages:
            feedback += f"- \"{message}\"\n"

    # Additional feedback based on the acting directions and rules
    # ...

    return feedback

def check_alignment_with_rules(message):
    """
    Checks if a user message aligns with crucial conversation rules.

    Args:
        message (str): User message to check.

    Returns:
        bool: True if the message aligns with the rules, False otherwise.
    """
    # Implement your logic to check if the message aligns with crucial conversation rules
    # Return True if it aligns, False otherwise
    return True  # Placeholder implementation

if __name__ == "__main__":
    app.run()
