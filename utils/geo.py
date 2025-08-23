from models import User
from math import radians, cos, sin, asin, sqrt

def haversine(lat1, lon1, lat2, lon2):
    # Haversine formula
    ...

def assign_nearest_officer(lat, lon):
    officers = User.query.filter_by(role='officer').all()
    nearest = min(officers, key=lambda o: haversine(lat, lon, o.latitude, o.longitude))
    return nearest