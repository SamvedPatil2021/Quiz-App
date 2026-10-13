import os
import json
import re
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import google.generativeai as genai

app = Flask(__name__, template_folder='templates')

# MongoDB Atlas Connection
MONGO_URI = os.environ.get("MONGO_URI", "your_mongodb_atlas_connection_string_here")
client = MongoClient(MONGO_URI)
db = client.quiz_database
users_collection = db.users
quizzes_collection = db.quizzes
submissions_collection = db.submissions

# Google GenAI Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def fetch_quiz_from_gemini(topic, num_questions):
    prompt = (
        f"Create a unique {num_questions}-question multiple-choice quiz about '{topic}'. "
        f"Ensure all questions are completely distinct, covering different concepts, syntax, and applications of the topic. "
        f"Return ONLY a valid JSON array of objects, where each object has keys: "
        f"'q' (the question string), 'options' (an array of 4 distinct string choices), and 'correct' (integer index 0 to 3 of the correct answer)."
    )
    
    # Stable model identifier for Google GenAI SDK
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    
    raw_text = response.text.strip()
    cleaned_text = re.sub(r"^```json\s*|\s*```$", "", raw_text, flags=re.IGNORECASE).strip()
    
    return json.loads(cleaned_text)

# Root route to serve your main frontend dashboard
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
        # Calls Gemini API to generate the exact number of unique questions requested
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