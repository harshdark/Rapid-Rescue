from functools import wraps
from flask import session, redirect

def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if session.get('role') != role:
                return redirect('/unauthorized')
            return f(*args, **kwargs)
        return wrapped
    return decorator