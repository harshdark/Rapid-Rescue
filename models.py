from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20))  # 'user', 'officer', 'admin'
    fcm_token = db.Column(db.String(255))

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    description = db.Column(db.Text)
    status = db.Column(db.String(50))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class ComplaintHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaint.id'))
    status = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime)