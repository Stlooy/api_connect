from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
from datetime import datetime
import os
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'

db = SQLAlchemy(app)

# Fetch key from environment variable instead of hardcoding
groq_api_key = "put it here"
groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

# Initialize OpenAI client with the API key and base URL
client = OpenAI(
    api_key=groq_api_key,
    base_url="https://api.groq.com/openai/v1"
) if groq_api_key else None


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def home():   
    all_messages = Message.query.order_by(Message.timestamp).all()
    return render_template('chat.html', messages=all_messages)

@app.route('/send', methods=['POST'])
def send():
    # Get the message from JSON or form data
    data = request.get_json() or {}
    user_message = data.get('message','').strip()
    
    # If the message is empty, redirect back to home
    if not user_message:
        return redirect(url_for('home'))

    # Save user message
    user_msg = Message(role="user", content=user_message)
    db.session.add(user_msg)
    db.session.commit()

    # Build system prompt + current user message
    conversation = [
        {"role": "system", "content": "You are a friendly assistant."},
        {"role": "user", "content": user_message}
    ]

    try:
        if client is None:
            raise RuntimeError("GROQ_API_KEY environment variable is not set")
        
        response = client.chat.completions.create(
            model=groq_model,
            messages=conversation
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Unable to contact the assistant: {e}"

    # Save bot reply
    bot_msg = Message(role="assistant", content=reply)
    db.session.add(bot_msg)
    db.session.commit()

    
    return jsonify({"status": "success", "reply": reply}), 200

if __name__ == '__main__':
    app.run(debug=True)