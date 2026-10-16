import random
import string

# --- NEW: Send OTP Route (Simulated or Ready for Twilio/Fast2SMS) ---
@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    mobile = data.get('mobile')
    
    if not mobile or len(mobile) < 10:
        return jsonify({"success": False, "error": "Please enter a valid mobile number."}), 400
        
    # Generate a 6-digit OTP (In production, integrate SMS gateway here)
    generated_otp = "".join(random.choices(string.digits, k=6))
    
    # Store temporarily in session or DB collection if needed, or return for demo testing
    return jsonify({
        "success": True, 
        "message": f"OTP sent successfully to {mobile}",
        "demoOtp": generated_otp  # Included for easy testing; remove in live production
    })

# --- NEW: Streamlined Account Creation Route ---
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')
    mobile = data.get('mobile')
    password = data.get('password')
    
    if not name or not mobile or not password:
        return jsonify({"success": False, "error": "All fields are required."}), 400
        
    # Check if mobile already exists in MongoDB
    existing_user = users_collection.find_one({"mobile": mobile})
    if existing_user:
        return jsonify({"success": False, "error": "An account with this mobile number already exists. Please log in."}), 400
        
    # Generate a unique custom user ID (e.g., SAM-8492)
    name_prefix = name.split()[0].upper()[:3]
    random_digits = "".join(random.choices(string.digits, k=4))
    custom_user_id = f"{name_prefix}-{random_digits}"
    
    # Save user details to MongoDB
    user_doc = {
        "userId": custom_user_id,
        "name": name,
        "mobile": mobile,
        "password": password, # In production, ensure you hash this with bcrypt/werkzeug
        "role": "student", # Default role or selectable
        "createdAt": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    users_collection.insert_one(user_doc)
    
    return jsonify({
        "success": True, 
        "userId": custom_user_id,
        "message": f"Account created successfully! Your unique ID is {custom_user_id}"
    })

# --- Updated Login Route to Support Custom ID or Mobile ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    identifier = data.get('identifier')  # Can be Custom ID or Mobile Number
    password = data.get('password')
    
    # Look up user by userId or mobile number in MongoDB
    user = users_collection.find_one({
        "$or": [
            {"userId": identifier},
            {"mobile": identifier}
        ]
    })
    
    if user and user.get("password") == password:
        return jsonify({
            "success": True, 
            "message": "Login successful", 
            "role": user.get("role", "student"), 
            "name": user.get("name", "User"),
            "userId": user.get("userId")
        })
        
    return jsonify({"success": False, "error": "Invalid ID/Mobile or Password"}), 401