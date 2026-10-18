import os
import random
import string
from flask import Flask, render_template, request, jsonify, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB Configuration (uses local or environment MONGO_URI)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["quiz_ai_db"]
teachers_collection = db["teachers"]
students_collection = db["students"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/teacher/signup", methods=["POST"])
def teacher_signup():
    data = request.json
    name = data.get("name")
    phone = data.get("phone")
    password = data.get("password")

    if not name or not phone or not password:
        return jsonify({"success": False, "message": "All fields are required!"}), 400

    # Check if phone already exists
    if teachers_collection.find_one({"phone": phone}):
        return jsonify({"success": False, "message": "Phone number already registered!"}), 400

    # Auto-generate Teacher ID (e.g., TCH-8492) and Passcode (e.g., A7x9P2)
    random_num = ''.join(random.choices(string.digits, k=4))
    teacher_id = f"TCH-{random_num}"
    passcode = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    teacher_doc = {
        "teacher_id": teacher_id,
        "passcode": passcode, # In production, hash passcode or store securely
        "name": name,
        "phone": phone,
        "password_hash": generate_password_hash(password)
    }

    teachers_collection.insert_one(teacher_doc)

    return jsonify({
        "success": True,
        "teacher_id": teacher_id,
        "passcode": passcode,
        "message": "Teacher account created successfully!"
    })

@app.route("/api/teacher/login", methods=["POST"])
def teacher_login():
    data = request.json
    teacher_id = data.get("teacher_id")
    passcode = data.get("passcode")

    teacher = teachers_collection.find_one({"teacher_id": teacher_id, "passcode": passcode})
    if teacher:
        session["teacher_id"] = teacher_id
        return jsonify({"success": True, "message": "Login successful!"})
    
    return jsonify({"success": False, "message": "Invalid Teacher ID or Passcode!"}), 401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)