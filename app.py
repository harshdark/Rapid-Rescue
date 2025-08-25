from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
import datetime
import uuid
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from math import radians, cos, sin, asin, sqrt
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager

# ---------------- CONFIG ----------------
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///police.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt_fallback")
jwt = JWTManager(app)

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "static/uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY")

# ---------------- INIT ----------------
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    # ✅ Fixed: SQLAlchemy 2.x compatible
    return db.session.get(User, int(user_id))

# ---------------- MODELS ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user', 'officer', 'admin'
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    fcm_token = db.Column(db.String(255))
    is_available = db.Column(db.Boolean, default=True)  # ✅ Added column to fix error

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ref_id = db.Column(db.String(12), unique=True, default=lambda: uuid.uuid4().hex[:12].upper())
    reporter_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone_number = db.Column(db.String(15))
    incident_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    maps_link = db.Column(db.String(300))
    photo_path = db.Column(db.String(300))
    status = db.Column(db.String(50), default="New")
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class ComplaintHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaint.id'))
    old_status = db.Column(db.String(50))
    new_status = db.Column(db.String(50))
    changed_by = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

with app.app_context():
    db.create_all()

# ---------------- HELPERS ----------------
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email Error:", e)

def send_fcm_notification(token, title, body):
    headers = {
        'Authorization': f'key={FCM_SERVER_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {
        'to': token,
        'notification': {'title': title, 'body': body}
    }
    try:
        requests.post('https://fcm.googleapis.com/fcm/send', headers=headers, json=payload)
    except Exception as e:
        print("FCM Error:", e)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def assign_nearest_officer(lat, lon):
    officers = User.query.filter_by(role='officer', is_available=True).all()
    if not officers:
        return None
    nearest = min(officers, key=lambda o: haversine(lat, lon, o.latitude, o.longitude) if o.latitude and o.longitude else float('inf'))
    return nearest

def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = db.session.get(User, int(session['_user_id']))
            if user.role != role:
                flash("Unauthorized access", "danger")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

# ---------------- ROUTES ----------------
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        return jsonify({
            "success": True,
            "message": "Login successful",
            "user_id": user.id,
            "role": user.role
        })
    else:
        return jsonify({
            "success": False,
            "message": "Invalid credentials"
        }), 401


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/complaint', methods=['GET', 'POST'])
def complaint():
    if request.method == 'POST':
        name = request.form['reporter_name']
        email = request.form['email']
        phone = request.form['phone_number']
        inc_type = request.form['incident_type']
        desc = request.form['description']
        loc = request.form.get('location')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        maps_link = request.form.get('maps_link')

        lat, lng = None, None
        if latitude and longitude:
            try:
                lat = float(latitude)
                lng = float(longitude)
                if not maps_link:
                    maps_link = f"https://maps.google.com/?q={lat},{lng}"
            except ValueError:
                pass

        photo_file = request.files.get('photo')
        photo_path = None
        if photo_file and photo_file.filename != "":
            filename = secure_filename(photo_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo_file.save(filepath)
            img = Image.open(filepath)
            img.thumbnail((800, 800))
            compressed_path = os.path.join(app.config['UPLOAD_FOLDER'], f"compressed_{filename}")
            img.save(compressed_path, optimize=True, quality=70)
            os.remove(filepath)
            photo_path = compressed_path

        new_complaint = Complaint(
            reporter_name=name,
            email=email,
            phone_number=phone,
            incident_type=inc_type,
            description=desc,
            location=loc,
            latitude=lat,
            longitude=lng,
            maps_link=maps_link,
            photo_path=photo_path
        )
        db.session.add(new_complaint)
        db.session.commit()

        history = ComplaintHistory(complaint_id=new_complaint.id, old_status=None, new_status="New", changed_by="system")
        db.session.add(history)
        db.session.commit()

        officer = assign_nearest_officer(lat, lng)
        if officer:
            new_complaint.assigned_officer_id = officer.id
            officer.is_available = False
            new_complaint.status = "Assigned"
            db.session.commit()
            if officer.fcm_token:
                send_fcm_notification(officer.fcm_token, "New Complaint Assigned", desc)

        send_email(
            to_email=email,
            subject="Complaint Registered",
            body=f"Dear {name},\n\nYour complaint has been registered successfully.\nReference ID: {new_complaint.ref_id}\n\nWe will get back to you shortly.\n\nRegards,\nPolice Department"
        )

        flash(f'Complaint submitted successfully. Reference ID: {new_complaint.ref_id}', 'success')
        return redirect(url_for('home'))

    return render_template('complaint.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')



@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user = db.session.get(User, int(session['_user_id']))
    search_ref = request.form.get('search_ref')

    if user.role == 'user':
        complaints = Complaint.query.filter_by(email=user.username).order_by(Complaint.created_at.desc()).all()
        return render_template('user_dashboard.html', complaints=complaints)

    elif user.role == 'officer':
        complaints = Complaint.query.filter_by(assigned_officer_id=user.id).order_by(Complaint.created_at.desc()).all()
        return render_template('officer_dashboard.html', complaints=complaints)

    elif user.role == 'admin':
        if search_ref:
            complaints = Complaint.query.filter(
                Complaint.ref_id.like(f"%{search_ref}%")
            ).order_by(Complaint.created_at.desc()).all()
        else:
            complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
        return render_template('admin_dashboard.html', complaints=complaints)

    else:
        flash("Invalid role", "danger")
        return redirect(url_for('home'))

@app.route('/update_status/<int:complaint_id>', methods=['POST'])
@login_required
@role_required("officer")
def update_status(complaint_id):
    new_status = request.form.get('status')
    complaint = Complaint.query.get_or_404(complaint_id)
    old_status = complaint.status
    complaint.status = new_status
    db.session.commit()

    history = ComplaintHistory(
        complaint_id=complaint.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=db.session.get(User, int(session['_user_id'])).username
    )
    db.session.add(history)
    db.session.commit()

    officer = db.session.get(User, complaint.assigned_officer_id)
    if officer:
        if new_status.lower() in ["resolved", "closed"]:
            officer.is_available = True
        if officer.fcm_token:
            send_fcm_notification(officer.fcm_token, "Complaint Status Updated", f"Ref ID: {complaint.ref_id} → {new_status}")
        db.session.commit()

    flash(f"Status updated to {new_status} for complaint {complaint.ref_id}", "success")
    return redirect(url_for('dashboard'))

# ---------------- REST API ROUTES ----------------
@app.route('/api/complaints/<int:cid>', methods=['GET'])
def api_get_complaint(cid):
    c = Complaint.query.get_or_404(cid)
    return jsonify({
        "id": c.id,
        "ref_id": c.ref_id,
        "status": c.status,
        "assigned_officer": c.assigned_officer_id,
        "created_at": c.created_at
    })

@app.route('/api/officers/<int:oid>/complaints', methods=['GET'])
def api_officer_complaints(oid):
    complaints = Complaint.query.filter_by(assigned_officer_id=oid).all()
    return jsonify([{"id": c.id, "ref_id": c.ref_id, "status": c.status} for c in complaints])

# ---------------- MAIN ----------------
if __name__ == "__main__":
    from api import api
    app.register_blueprint(api)
    app.run(debug=True, host="0.0.0.0", port=5000)
