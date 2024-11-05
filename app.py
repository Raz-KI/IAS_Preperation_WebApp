from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from groq import Groq
import cv2
import numpy as np
from deepface import DeepFace
import logging
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

global loggedin
loggedin=0

global endframe
endframe=0

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)     # Secret key for session management

# SQLite database connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # SQLite database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy object
db = SQLAlchemy(app)

# Define User model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# Create the database tables
with app.app_context():
    db.create_all()

# Sign-up route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        # Check if the username or email already exists
        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            flash("Username or Email already exists. Please try again with different details.", "error")
            return redirect(url_for('signup'))
        
        # Hash the password for security
        hashed_password = generate_password_hash(password)
        
        # Create a new user object
        new_user = User(username=username, password=hashed_password, email=email)
        
        # Add user to the database
        db.session.add(new_user)
        db.session.commit()
        
        flash("Sign-up successful! Please log in.", "success")
        return redirect(url_for('login'))  # Corrected the redirect to 'login'
    
    return render_template('iassignup.html')



# Initialize Groq client with API key
client = Groq(
    api_key="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"
)

# Mock user login details
users = {'admin': 'admin123'}

# To store questions and answers as a list of dictionaries
interview_data = []

@app.route('/')
def home():
    if loggedin==0:
        return render_template('iashome.html')
    else:
        return render_template('iashomelogged.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Retrieve the form data using request.form
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Query the user by username
        user = User.query.filter_by(username=username).first()
        
        # Check if the user exists and the password is correct
        if user and check_password_hash(user.password, password):
            # Redirect to interview.html after successful login
            global loggedin
            loggedin=1
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for('login'))
    
    # Render login.html for GET request
    return render_template('iaslogin.html')

# Interview route
@app.route('/interview')
def interview():
    return render_template('interview.html')

# Function to get AI-generated interview question from Groq
def get_ai_question(prompt):
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are an IAS(Indian Administrative Service) interviewer."},
            {"role": "user", "content": prompt}
        ],
        model="llama3-8b-8192",
    )
    return chat_completion.choices[0].message.content

# Function to rate the entire interview based on the collected answers
def get_feedback_from_ai(interview_data):
    # Prepare the message for the AI
    messages = []
    for entry in interview_data:
        messages.append(f"Q: {entry['question']}\nA: {entry['answer']}")
    
    # Join messages to create a prompt for the AI
    prompt = "\n".join(messages) + "\n\n"f"Please provide feedback on the candidates performance, strengths, and areas for improvement.His visual confidence score was{average_confidence}"
    # Call the AI model to get feedback
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are an expert interviewer providing feedback on a candidate's interview performance."},
            {"role": "user", "content": prompt}
        ],
        model="llama3-8b-8192",
    )
    
    return chat_completion.choices[0].message.content

# API route to start the interview with the first question: "Introduce yourself"
@app.route('/api/start_interview', methods=['GET'])
def start_interview():
    endframe=0
    first_question = "Hello Candidate! Introduce yourself."
    interview_data.append({"question": first_question, "answer": None})  # Store first question
    return jsonify({'question': first_question})




# API route for asking follow-up questions based on candidate's answer
@app.route('/api/answer', methods=['POST'])
def receive_answer():
    candidate_answer = request.json.get('answer')
    follow_count = request.json.get('follow_up_count')
    
    # Process candidate's answer and store it
    last_entry = interview_data[-1]  # Get the last question-answer entry

    # Store the candidate's answer for the last question
    last_entry['answer'] = candidate_answer  
    
    # Collect emotion data for the last question
    emotion_data = request.json.get('emotion_data')  # This should come from the frontend
    last_entry['emotion'] = emotion_data  # Store the emotion data

    # Check if follow_up_count exists, if not, initialize it to 0
    # Increment follow-up count
    if follow_count < 2:
        follow_count += 1
        follow_up = get_ai_question(f"The candidate said: '{candidate_answer}'. Based on their response, ask a thoughtful follow-up question to probe deeper.")
    else:
        follow_up = get_ai_question(f"The candidate said: '{candidate_answer}'. Now ask a new IAS interview question.")
    
    # Add the new question (either follow-up or new) to the interview data
    interview_data.append({"question": follow_up, "answer": None})

    return jsonify({'follow_up': follow_up})




# Modify the end_interview function
@app.route('/api/end_interview', methods=['GET'])
def end_interview():
    overall_feedback = get_feedback_from_ai(interview_data)

    # Calculate average confidence
    # if totalcall > 0:
    #     average_confidence = average_conf / totalcall
    # else:
    #     average_confidence = 0  # If no frames were analyzed, default to 0
    print(average_confidence)
    global endframe
    endframe=1
    loggedin=0
    return render_template('results.html', 
                           overall_feedback=overall_feedback, 
                           interview_data=interview_data, 
                           average_confidence=int((iterconf/frames)*20)
                           )


global frames,iterconf
frames=0
iterconf=0

confidence_mapping = {
    'happy': 8,
    'neutral': 6,
    'surprise': 7,
    'fear': 3,
    'sad': 2,
    'angry': 1,
    'disgust': 1
}

def avgconf(face_confidence, emotion):
    """
    Averages the confidence score based on face detection and emotion confidence mapping.
    If face_confidence is high, we factor that in with the emotion confidence from the mapping.
    """
    emotion_confidence = confidence_mapping.get(emotion, 5)  # Default to 5 if emotion not found
    return (face_confidence + emotion_confidence) / 2  # Adjust as needed

# Route to analyze video frame# Route to analyze video frame
@app.route('/api/analyze_frame', methods=['POST'])
def analyze_frame():
    if endframe==1:
         return jsonify({'message': 'Over'})
    global frames
    global iterconf
    frames+=1
    try:
        frame = request.files['frame'].read()
        npimg = np.frombuffer(frame, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        # Analyze emotions using DeepFace
        result = DeepFace.analyze(img, actions=['emotion'], enforce_detection=False)

        if isinstance(result, list):
            result = result[0]

        emotion = result.get('dominant_emotion', 'neutral')
        face_confidence = result.get('face_confidence', 5)

        adjusted_confidence = avgconf(face_confidence, emotion)
        global average_confidence
        average_confidence=adjusted_confidence
        # Log the result
        iterconf+=adjusted_confidence
        print(f"Emotion: {emotion}, Confidence: {adjusted_confidence},Frames: {frames}, average: {average_confidence}, score: {(iterconf/frames)*2}")

        return jsonify({'emotion': emotion, 'confidence': adjusted_confidence, 'face_visible': True})

    except Exception as e:
        print(f"Error processing frame: {str(e)}")  # Log the error
        return jsonify({'message': 'An error occurred during analysis', 'error': str(e), 'face_visible': False})




# if __name__ == '__main__':

#     app.run(debug=True)



