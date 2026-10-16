import os
import json
import re
import time
import random
import string
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import google.generativeai as genai

# 1. Initialize Flask app FIRST before any routes
app = Flask(__name__, template_folder='templates', static_folder='static')

# MongoDB Atlas Connection
MONGO_URI = os.environ.get("MONGO_URI", "")
client = MongoClient(MONGO_URI)
db = client.quiz_database
users_collection = db.users
quizzes_collection = db.quizzes
submissions_collection = db.submissions

# Google GenAI Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def fetch_quiz_from_gemini(topic, num_questions):
    if not GEMINI_API_KEY:
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
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
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

@app.route('/assess/<quiz_id>')
def assess_quiz(quiz_id):
    return render_template('index.html')

# --- Send OTP Route ---
@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    mobile = data.get('mobile')
    
    if not mobile or len(mobile) < 10:
        return jsonify({"success": False, "error": "Please enter a valid mobile number."}), 400
        
    generated_otp = "".join(random.choices(string.digits, k=6))
    
    return jsonify({
        "success": True, 
        "message": f"OTP sent successfully to {mobile}",
        "demoOtp": generated_otp
    })

# --- Streamlined Account Signup Route ---
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')
    mobile = data.get('mobile')
    password = data.get('password')
    
    if not name or not mobile or not password:
        return jsonify({"success": False, "error": "All fields are required."}), 400
        
    existing_user = users_collection.find_one({"mobile": mobile})
    if existing_user:
        return jsonify({"success": False, "error": "An account with this mobile number already exists. Please log in."}), 400
        
    name_prefix = name.split()[0].upper()[:3]
    random_digits = "".join(random.choices(string.digits, k=4))
    custom_user_id = f"{name_prefix}-{random_digits}"
    
    user_doc = {
        "userId": custom_user_id,
        "name": name,
        "mobile": mobile,
        "password": password,
        "role": "student",
        "createdAt": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    users_collection.insert_one(user_doc)
    
    return jsonify({
        "success": True, 
        "userId": custom_user_id,
        "message": f"Account created successfully! Your unique ID is {custom_user_id}"
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    identifier = data.get('identifier')
    password = data.get('password')
    
    user = users_collection.find_one({
        "$or": [
            {"userId": identifier},
            {"mobile": identifier},
            {"identifier": identifier}
        ]
    })
    
    if user and user.get("password") == password:
        return jsonify({
            "success": True, 
            "message": "Login successful", 
            "role": user.get("role", "student"), 
            "name": user.get("name", "User"),
            "userId": user.get("userId", user.get("identifier"))
        })
    return jsonify({"success": False, "error": "Invalid ID/Mobile or Password"}), 401

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