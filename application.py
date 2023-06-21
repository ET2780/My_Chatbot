from flask import Flask, request, render_template, url_for, redirect
import openai
from os import getenv
from dotenv import load_dotenv
load_dotenv()
from openai.error import RateLimitError

application = Flask(__name__, template_folder='Templates/')
openai.api_key = getenv('OPENAI_API_KEY')

# A dictionary to store user context
user_context = {
    'conversation_history': [],
    'suggestions': []

}
# application.add_url_rule('/favicon-32x32.png', redirect_to=url_for('static', filename='Assets/favicon-32x32.png'))
states = ["intro",  "name", "conversation_with", "user_traits", "target_traits", "situation", "goal", "simulation", "Results"]

current_state = 0

def next_state():
    global current_state
    current_state += 1
    if current_state >= len(states):
        current_state = len(states) - 1

@application.route("/")
def index():
    return render_template("index.html")

@application.route("/finish_simulation")
def finish_simulation():
    return redirect(url_for("show_results"))

@application.route("/get")
def get_bot_response():
    global current_state
    userText = request.args.get('msg')
    print(f"User text: {userText}")

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
        return "How do you usually behave around this person?"
    elif states[current_state] == "user_traits":
        user_context['user_traits'] = userText
        next_state()
        return "Describe the person you wish to have a conversation with, what is their behavior around you?"
    elif states[current_state] == "target_traits":
        user_context['target_traits'] = userText
        next_state()
        return "What is the situation that led to this conversation? The more information you provide, the better the simulation"
    elif states[current_state] == "situation":
        user_context['situation'] = userText
        next_state()
        return "What is your goal in this conversation? What do you hope to achieve?"
    elif states[current_state] == "goal":
        user_context['goal'] = userText
        next_state()
        return start_simulation() 

    elif states[current_state] == "simulation":
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

        # Check alignment with rules and store suggestions
        alignment_check = check_alignment_with_rules(userText)
        if not alignment_check['aligns_with_rules'] and alignment_check['suggestion']:
         user_context['suggestions'].append(alignment_check['suggestion'])

        # Create the messages array for the API call
        messages = [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": userText},
        ] + user_context['conversation_history']  # Include the conversation history

        try:
            response = openai.ChatCompletion.create(
               model="gpt-3.5-turbo",
              messages=messages,
              max_tokens=100,
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

        return assistant_message

    elif states[current_state] == "Results":
        # Handle the transition to the results state
        suggestions = user_context['suggestions']
        acting_directions_issue = user_context['user_traits']
        acting_directions_target = user_context['target_traits']
        acting_directions_situation = user_context['situation']
        acting_directions_goal = user_context['goal']
        acting_directions = f"{acting_directions_issue}\n{acting_directions_target}\n{acting_directions_situation}\n{acting_directions_goal}"

        suggestions_and_feedback = generate_suggestions(user_context['conversation_history'], acting_directions, suggestions)

        return redirect(url_for("show_results", suggestions_and_feedback=suggestions_and_feedback, acting_directions=acting_directions))
    

def show_results(suggestions_and_feedback, acting_directions):
    return render_template("results.html", suggestions_and_feedback=suggestions_and_feedback, acting_directions=acting_directions)


def generate_suggestions(conversation_history, acting_directions, suggestions):
    acting_directions_issue = acting_directions.split("\n")[0]
    acting_directions_target = acting_directions.split("\n")[1]
    acting_directions_situation = acting_directions.split("\n")[2]
    acting_directions_goal = acting_directions.split("\n")[3]

    acting_directions_content = f"{acting_directions_issue}\n{acting_directions_target}\n{acting_directions_situation}\n{acting_directions_goal}"
    acting_directions_messages = [
        {"role": "system", "content": f"Here are the acting directions:\n{acting_directions_content}"}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=acting_directions_messages,
            max_tokens=1024,
            temperature=0.5,
        )
    except RateLimitError:
        return "I'm sorry, but I'm currently overloaded with requests. Please try again later or reload the bot."

    acting_directions_feedback = response['choices'][0]['message']['content']

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

    # Include the suggestions, feedback, acting directions, and goal alignment result in the output
    if suggestions:
        suggestions_text = "\n\nSuggestions for improvement based on crucial conversation rules:\n\n" + "\n".join(suggestions)
        return suggestions_from_model + "\n\n" + acting_directions_feedback + "\n\n" + feedback + suggestions_text + "\n\n" + goal_alignment_result
    else:
        return suggestions_from_model + "\n\n" + acting_directions_feedback + "\n\n" + feedback + "\n\n" + goal_alignment_result

# def provide_feedback(conversation_history, acting_directions_issue, acting_directions_situation, acting_directions_goal):
#     """
#     Provides feedback based on the crucial conversation rules and the conversation history.

#     Args:
#         conversation_history (list): List of conversation messages.
#         acting_directions_issue (str): Acting directions related to the issue.
#         acting_directions_situation (str): Acting directions related to the situation.
#         acting_directions_goal (str): Acting directions related to the goal.

#     Returns:
#         str: Feedback based on crucial conversation rules.
#     """
#     # Extract user messages from the conversation history
#     user_messages = [message["content"] for message in conversation_history if message["role"] == "user"]

#     # Example: Check if any user message doesn't align with crucial conversation rules
#     noncompliant_messages = []

#     for message in user_messages:
#         if not check_alignment_with_rules(message):
#             noncompliant_messages.append(message)

#     feedback = ""

#     if len(noncompliant_messages) > 0:
#         feedback += "Based on crucial conversation rules, the following messages could be improved:\n\n"
#         for message in noncompliant_messages:
#             feedback += f"- \"{message}\"\n"

#     # Additional feedback based on the acting directions and rules
#     # ...

#     return feedback


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
        messages = [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": "Assistant:"}
        ]

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=150,
                temperature=0.8,
                n=1,
                stop=None,
                log_level="info",
                logprobs=0
            )
        except RateLimitError:
            return "I'm sorry, but I'm currently overloaded with requests. Please try again later or reload the bot."

        return response['choices'][0]['message']['content']

def start_simulation():
    acting_directions_issue = user_context['user_traits']
    acting_directions_target = user_context['target_traits']
    acting_directions_situation = user_context['situation']
    acting_directions_goal = user_context['goal']
    acting_directions = f"{acting_directions_issue}\n{acting_directions_target}\n{acting_directions_situation}\n{acting_directions_goal}"

    # Create the system message
    system_message = {
        "role": "system",
        "content": f"You are a highly trained actor. You are playing the role of {user_context['conversation_with']}. Your objective is not to solve problems or give advice, but to embody the following traits and behaviors: {acting_directions} while taking into consideration the situation the user described. Interact with the user in a way that reflects these traits and behaviors. Remember, you are not providing personal advice or solutions. Act as a person with these {user_context['target_traits']}, do not end the conversation, only the user can end it."
    }

    # Create the messages array for the API call
    messages = [system_message]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1024,
            temperature=0.8,
        )
    except RateLimitError:
        return "I'm sorry, but I'm currently overloaded with requests. Please try again later or reload the bot."

    # Extract the assistant's message from the response
    assistant_message = response['choices'][0]['message']['content']

    # Add the system and assistant's message to the conversation history
    user_context['conversation_history'].append(system_message)
    user_context['conversation_history'].append({
        "role": "assistant",
        "content": assistant_message
    })

    return assistant_message

@application.route("/results")
def show_results():
    acting_directions_issue = user_context['user_traits']
    acting_directions_target = user_context['target_traits']
    acting_directions_situation = user_context['situation']
    acting_directions_goal = user_context['goal']
    acting_directions = f"{acting_directions_issue}\n{acting_directions_target}\n{acting_directions_situation}\n{acting_directions_goal}"

    suggestions_and_feedback = generate_suggestions(user_context['conversation_history'], acting_directions, user_context['suggestions'])
    return render_template("results.html", suggestions_and_feedback=suggestions_and_feedback, acting_directions=acting_directions)

def generate_suggestions(conversation_history, acting_directions, suggestions):
    acting_directions_issue = acting_directions.split("\n")[0]
    acting_directions_target = acting_directions.split("\n")[1]
    acting_directions_situation = acting_directions.split("\n")[2]
    acting_directions_goal = acting_directions.split("\n")[3]

    acting_directions_content = f"{acting_directions_issue}\n{acting_directions_target}\n{acting_directions_situation}\n{acting_directions_goal}"
    acting_directions_messages = [
        {"role": "system", "content": f"Here are the acting directions:\n{acting_directions_content}"}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=acting_directions_messages,
            max_tokens=1024,
            temperature=0.5,
        )
    except RateLimitError:
        return "I'm sorry, but I'm currently overloaded with requests. Please try again later or reload the bot."

    acting_directions_feedback = response['choices'][0]['message']['content']

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

    # Include the suggestions, feedback, acting directions, and goal alignment result in the output
    if suggestions:
        suggestions_text = "\n\nSuggestions for improvement based on crucial conversation rules:\n\n" + "\n".join(suggestions)
        return suggestions_from_model + "\n\n" + acting_directions_feedback + "\n\n" + feedback + suggestions_text + "\n\n" + goal_alignment_result
    else:
        return suggestions_from_model + "\n\n" + acting_directions_feedback + "\n\n" + feedback + "\n\n" + goal_alignment_result



if __name__ == "__main__":
    application.run(port=8000)
