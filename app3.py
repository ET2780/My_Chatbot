from flask import Flask, request, render_template
import openai

app = Flask(__name__)
openai.api_key = "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"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get")
def get_bot_response():
    userText = request.args.get('msg')
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are an AI trained in the principles of the book 'Crucial Conversations'. The user is a product manager in a cybersecurity company and is having difficulties with their boss and the developers they work with. They feel their boss is not supportive and the developers are not responsive. They are worried about their job performance and are seeking help in improving their communication and leadership skills. As the AI, you will simulate a conversation with the user where you play the role of their boss. You will respond to their concerns, provide feedback, and guide them in using the principles of crucial conversations to navigate this difficult situation. After each response from the user, you will analyze their response, provide constructive feedback, and adjust your next response accordingly. At the end of the conversation, you will provide a summary of their performance and suggestions for improving their communication skills."
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
