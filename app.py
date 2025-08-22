from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
import datetime
import uuid
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///police.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = "static/uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Email Config
EMAIL_ADDRESS = "harshgupta79004@gmail.com"   # apna gmail
EMAIL_PASSWORD = "rndy nqpe sfbe bzkc"       # jo tu gmail se banaya hai

# ---------------- INIT ----------------
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- MODELS ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

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
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

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
        print(f"Email sent to {to_email}")
    except Exception as e:
        print("Email Error:", e)

# ---------------- ROUTES ----------------
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/mobile')
def mobile_complaint():
    return redirect(url_for('complaint'))

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

        # Photo handling
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

        # Save complaint
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

        # Send Email confirmation
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
    search_ref = request.form.get('search_ref')
    if search_ref:
        complaints = Complaint.query.filter(
            Complaint.ref_id.like(f"%{search_ref}%")
        ).order_by(Complaint.created_at.desc()).all()
    else:
        complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()

    return render_template('dashboard.html', complaints=complaints)



@app.route('/update_status/<int:complaint_id>', methods=['POST'])
@login_required
def update_status(complaint_id):
    new_status = request.form.get('status')
    complaint = Complaint.query.get_or_404(complaint_id)
    complaint.status = new_status
    db.session.commit()
    flash(f"Status updated to {new_status} for complaint {complaint.ref_id}", "success")
    return redirect(url_for('dashboard'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
