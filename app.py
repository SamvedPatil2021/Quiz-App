import os
import json
import re
import time
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from google import genai

app = Flask(__name__, template_folder='templates', static_folder='static')

# MongoDB Atlas Connection
MONGO_URI = os.environ.get("MONGO_URI", "")
client = MongoClient(MONGO_URI)
db = client.quiz_database
users_collection = db.users
quizzes_collection = db.quizzes
submissions_collection = db.submissions

# Modern Google GenAI Client Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def fetch_quiz_from_gemini(topic, num_questions):
    if not ai_client:
        raise Exception("GEMINI_API_KEY environment variable is not set on Render.")
        
    prompt = (
        f"Create a unique {num_questions}-question multiple-choice quiz about '{topic}'. "
        f"Ensure all questions are completely distinct, covering different concepts, syntax, and applications of the topic. "
        f"Return ONLY a valid JSON array of objects, where each object has keys: "
        f"'q' (the question string), 'options' (an array of 4 distinct string choices), and 'correct' (integer index 0 to 3 of the correct answer)."
    )
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = ai_client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt,
            )
            raw_text = response.text.strip()
            cleaned_text = re.sub(r"^```json\s*|\s*```$", "", raw_text, flags=re.IGNORECASE).strip()
            return json.loads(cleaned_text)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    role = data.get('role')
    identifier = data.get('identifier')
    password = data.get('password')
    
    user = users_collection.find_one({"role": role, "identifier": identifier, "password": password})
    if user:
        return jsonify({"success": True, "message": "Login successful", "role": role, "name": user.get("name", "User")})
    return jsonify({"success": False, "message": "Invalid credentials or unauthorized access"}), 401

@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    data = request.json
    topic = data.get('topic')
    num_questions = int(data.get('numQuestions', 5))
    
    try:
        questions_list = fetch_quiz_from_gemini(topic, num_questions)
        
        quiz_id = quizzes_collection.insert_one({
            "title": f"{topic} (AI Generated)",
            "topic": topic,
            "createdBy": "AI Faculty Agent",
            "questions": questions_list
        }).inserted_id
        
        return jsonify({"success": True, "quizId": str(quiz_id), "questions": questions_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))