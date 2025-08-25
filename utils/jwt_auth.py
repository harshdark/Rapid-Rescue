# utils/jwt_auth.py
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from functools import wraps
from flask import jsonify

def role_required_api(*allowed_roles):
    """
    Use: @role_required_api('admin')  OR  @role_required_api('officer','admin')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt() or {}
                role = claims.get("role")
                if role not in allowed_roles:
                    return jsonify({"msg": "forbidden: role not allowed"}), 403
            except Exception as e:
                return jsonify({"msg": "unauthorized", "error": str(e)}), 401
            return fn(*args, **kwargs)
        return wrapper
    return decorator
