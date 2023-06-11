from flask import Flask, request, render_template
import openai
from os import getenv
from dotenv import load_dotenv
load_dotenv()
from openai.error import RateLimitError

application = Flask(__name__,  template_folder="templates")
openai.api_key = getenv('OPENAI_API_KEY')

# A dictionary to store user context
user_context = {
    'conversation_history': [],
    'suggestions': []

}

states = ["intro",  "name", "conversation_with", "user_traits", "target_traits", "situation", "goal", "simulation", "Results"]

current_state = 0

def next_state():
    global current_state
    current_state += 1
    if current_state >= len(states):
        raise IndexError("trying to move to a state that does not exist")

@application.route("/")
def index():
    return render_template("index.html")

@application.route("/get")
def get_bot_response():
    global current_state
    userText = request.args.get('msg')
    print(f"User text: {userText}")  # Print the user's input

    if states[current_state] == "intro":
        next_state()
        return "Welcome to the conversation simulation. What is your name?"
    elif states[current_state] == "name":
        user_context['name'] = userText
        next_state()
        return f"Nice to meet you, {user_context['name']}! Who is your conversation with?"
    elif states[current_state] == "conversation_with":
        user_context['conversation_with'] = userText
        next_state()
        return "Describe your traits and how you usually interact with this person."
    elif states[current_state] == "user_traits":
        user_context['user_traits'] = userText
        next_state()
        return "Describe the traits of the person you wish to have a conversation with."
    elif states[current_state] == "target_traits":
        user_context['target_traits'] = userText
        next_state()
        return "What is the situation that led to this conversation?"
    elif states[current_state] == "situation":
        user_context['situation'] = userText
        next_state()
        return "What is your goal in this conversation? What do you hope to achieve?"
    elif states[current_state] == "goal":
        user_context['goal'] = userText
        next_state()
        return "Thank you for providing all the details. Now, let's start the simulation. Please start the conversation as you would in real life. In order to end the conversation, type: 'Finish simulation'"
    elif states[current_state] == "simulation":
        if userText.lower() == "finish simulation":
            acting_directions = f"{user_context['user_traits']}\n{user_context['target_traits']}\n{user_context['situation']}\n{user_context['goal']}"
            suggestions = generate_suggestions(user_context['conversation_history'], acting_directions, user_context['suggestions'])
            next_state()  # Move to the next state
            return suggestions
        else:
            # Check alignment with rules and store suggestions
            alignment_check = check_alignment_with_rules(userText)
            if not alignment_check['aligns_with_rules'] and alignment_check['suggestion']:
                user_context['suggestions'].append(alignment_check['suggestion'])
            # Continue the simulation
            # Add the user's input to the conversation history
            user_context['conversation_history'].append({
                "role": "user",
                "content": userText
            })

            acting_directions_issue = user_context['user_traits']
            acting_directions_target = user_context['target_traits']
            acting_directions_situation = user_context['situation']
            acting_directions_goal = user_context['goal']
            acting_directions = f"{acting_directions_issue}\n{acting_directions_target}\n{acting_directions_situation}\n{acting_directions_goal}"

            # Create the messages array for the API call
            messages = [
                {
                    "role": "system",
                    "content": f"You are an AI assistant. You are playing the role of {user_context['conversation_with']}. Acting directions: {acting_directions}"
                },
                {
                    "role": "assistant",
                    "content": "Start the conversation."
                }
            ] + [{"role": message["role"], "content": message["content"]} for message in user_context['conversation_history']]


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

def generate_suggestions(conversation_history, acting_directions, suggestions):
    """
    Generates suggestions based on the conversation history, acting directions, and suggestions from the check_alignment_with_rules function.

    Args:
        conversation_history (list): List of conversation messages.
        acting_directions (str): Acting directions for the simulation.
        suggestions (list): List of suggestions from the check_alignment_with_rules function.

    Returns:
        str: Suggestions and feedback based on crucial conversation rules and goal alignment.
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

    suggestions_from_model = response['choices'][0]['message']['content']
    feedback = provide_feedback(conversation_history, acting_directions_issue, acting_directions_situation, acting_directions_goal)

    # Check goal alignment
    goal = acting_directions_goal
    goal_alignment_result = check_goal_alignment(goal, conversation_history)

    # Include the suggestions and goal alignment result in the output
    if suggestions:
        suggestions_text = "\n\nSuggestions for improvement based on crucial conversation rules:\n\n" + "\n".join(suggestions)
        return suggestions_from_model + "\n\n" + feedback + suggestions_text + "\n\n" + goal_alignment_result
    else:
        return suggestions_from_model + "\n\n" + feedback + "\n\n" + goal_alignment_result


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
        dict: A dictionary containing a boolean indicating alignment with the rules and a suggestion for improvement.
    """
    aligns_with_rules = True  # Placeholder implementation
    suggestion = ""  # Placeholder implementation

    # Implement your logic to check if the message aligns with crucial conversation rules
    # If it doesn't align, set aligns_with_rules to False and provide a suggestion

    return {'aligns_with_rules': aligns_with_rules, 'suggestion': suggestion}

def check_goal_alignment(goal, conversation_history):
    """
    Checks if the user's goal aligns with the results of the conversation.

    Args:
        goal (str): The user's goal.
        conversation_history (list): List of conversation messages.

    Returns:
        str: Feedback on how well the user's goal was achieved and what could be improved.
    """
    # Construct the conversation input for the GPT-3.5-turbo model
    conversation = []
    for message in conversation_history:
        conversation.append({"role": message["role"], "content": message["content"]})

    # Add the user's goal to the conversation input
    conversation.append({"role": "user", "content": goal})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation,
            max_tokens=100,
            temperature=0.7,
        )
    except RateLimitError:
        return "I'm sorry, but I'm currently overloaded with requests. Please try again later or reload the bot."

    # Get the assistant's response from the GPT-3.5-turbo model
    assistant_response = response.choices[0].message.content.strip()

    if "goal achieved" in assistant_response.lower():
        return "Your goal was achieved in the conversation."
    else:
        return f"Your goal was not fully achieved in the conversation. Here's a suggestion for improvement: {assistant_response}"

def check_alignment_with_rules(user_input):
    aligns_with_rules = True
    suggestion = ""

    # Check for inconsistencies and misalignment in user input
    if "called me to his office and told me I am about to be fired" in user_input:
        if "wants to avoid having to fire me" in user_input:
            aligns_with_rules = False
            suggestion = "The situation description and the target's traits seem to be inconsistent. Please ensure that the simulation is aligned with the provided description."
    
    return {
        "aligns_with_rules": aligns_with_rules,
        "suggestion": suggestion
    }
def get_assistant_response(user_input, acting_directions_issue, acting_directions_target):
    # Modify assistant's response based on the acting_directions_issue and acting_directions_target
    if "Hello" in user_input:
        return "Hello. I called you here today because I understand that you have concerns about your communication and technical skills. As your boss, I want to address these concerns and support your growth. Let's discuss how we can improve together."
    elif "communication and technical skills" in user_input:
        return "I understand that your goal is to communicate clearly and avoid any negative outcomes. I appreciate your commitment to improvement, and I'm here to help you overcome any challenges. Let's work together to find a resolution."
    else:
        # Use OpenAI's ChatGPT for assistant's responses
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"User: {user_input}\nAssistant:",
            temperature=0.6,
            max_tokens=50,
            n=1,
            stop=None,
            log_level="info",
            logprobs=0
        )
        return response['choices'][0]['text']


if __name__ == "__main__":
    application.run()
