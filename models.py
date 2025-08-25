from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Officer (police staff / admin bhi yahi table use karega)
class Officer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), unique=True, nullable=False)
    latitude = db.Column(db.Float, nullable=True)      # officer location
    longitude = db.Column(db.Float, nullable=True)
    is_available = db.Column(db.Boolean, default=True) # free/busy
    role = db.Column(db.String(20), default='officer') # user/officer/admin
    device_token = db.Column(db.String(255), nullable=True)  # for FCM push

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=True)      # complaint location
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(50), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Auto-assignment field
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('officer.id'), nullable=True)
    assigned_officer = db.relationship('Officer', backref='complaints')

class ComplaintHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaint.id'))
    changed_by = db.Column(db.String(120))  # kisne change kiya (officer/admin/system)
    old_status = db.Column(db.String(50))
    new_status = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
