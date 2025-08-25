# api.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from datetime import timedelta

from app import db, User, Complaint, ComplaintHistory, assign_nearest_officer, send_fcm_notification

api = Blueprint("api", __name__, url_prefix="/api")

# ---------- AUTH ----------
@api.post("/login")
def api_login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"msg": "username/password required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"msg": "invalid credentials"}), 401

    # optional: update fcm token sent by client
    fcm_token = data.get("fcm_token")
    if fcm_token:
        user.fcm_token = fcm_token
        db.session.commit()

    access = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "username": user.username},
        expires_delta=timedelta(days=3)
    )
    return jsonify({"access_token": access, "role": user.role, "user_id": user.id})

# ---------- USER: create complaint ----------
@api.post("/complaints")
@jwt_required()
def create_complaint():
    uid = int(get_jwt_identity())
    data = request.get_json() or {}

    c = Complaint(
        reporter_name=data.get("reporter_name"),
        email=data.get("email"),
        phone_number=data.get("phone_number"),
        incident_type=data.get("incident_type"),
        description=data.get("description"),
        location=data.get("location"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        maps_link=data.get("maps_link"),
    )
    db.session.add(c); db.session.commit()

    # history
    db.session.add(ComplaintHistory(
        complaint_id=c.id, old_status=None, new_status="New", changed_by=f"user:{uid}"
    )); db.session.commit()

    # auto-assign
    if c.latitude is not None and c.longitude is not None:
        officer = assign_nearest_officer(c.latitude, c.longitude)
        if officer:
            c.assigned_officer_id = officer.id
            c.status = "Assigned"
            officer.is_available = False
            db.session.commit()
            if officer.fcm_token:
                send_fcm_notification(officer.fcm_token, "New Complaint Assigned", c.description or "")

    return jsonify({"id": c.id, "ref_id": c.ref_id, "status": c.status})

# ---------- USER: my complaints by email (simple) ----------
@api.get("/my-complaints")
@jwt_required()
def my_complaints():
    from flask_jwt_extended import get_jwt
    email = (get_jwt() or {}).get("username")
    q = Complaint.query.filter_by(email=email).order_by(Complaint.created_at.desc()).all()
    return jsonify([{
        "id": c.id, "ref_id": c.ref_id, "status": c.status,
        "assigned_officer": c.assigned_officer_id, "created_at": c.created_at
    } for c in q])

# ---------- OFFICER: my assigned ----------
from utils.jwt_auth import role_required_api
@api.get("/officer/assigned")
@role_required_api("officer","admin")
def officer_assigned():
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    officer_id = int(claims.get("sub"))  # identity
    comps = Complaint.query.filter_by(assigned_officer_id=officer_id).all()
    return jsonify([{"id": c.id, "ref_id": c.ref_id, "status": c.status} for c in comps])

# ---------- OFFICER: update status ----------
@api.post("/complaints/<int:cid>/status")
@role_required_api("officer","admin")
def api_update_status(cid):
    data = request.get_json() or {}
    new_status = (data.get("status") or "").strip()
    if not new_status:
        return jsonify({"msg": "status required"}), 400

    c = Complaint.query.get_or_404(cid)
    old = c.status
    c.status = new_status
    db.session.commit()

    # history + availability
    from flask_jwt_extended import get_jwt
    changer = (get_jwt() or {}).get("username")
    db.session.add(ComplaintHistory(
        complaint_id=c.id, old_status=old, new_status=new_status, changed_by=changer
    ))
    if c.assigned_officer_id:
        officer = User.query.get(c.assigned_officer_id)
        if officer:
            if new_status.lower() in ["resolved", "closed"]:
                officer.is_available = True
            if officer.fcm_token:
                send_fcm_notification(officer.fcm_token, "Complaint Status Updated",
                                      f"Ref {c.ref_id}: {new_status}")
    db.session.commit()

    return jsonify({"msg": "updated", "ref_id": c.ref_id, "status": c.status})

# ---------- ADMIN: search ----------
@api.get("/admin/complaints")
@role_required_api("admin")
def admin_search():
    ref = (request.args.get("ref") or "").strip()
    q = Complaint.query
    if ref:
        q = q.filter(Complaint.ref_id.like(f"%{ref}%"))
    q = q.order_by(Complaint.created_at.desc()).all()
    return jsonify([{
        "id": c.id, "ref_id": c.ref_id, "status": c.status,
        "assigned_officer": c.assigned_officer_id, "created_at": c.created_at
    } for c in q])
