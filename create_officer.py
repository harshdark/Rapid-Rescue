from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    username = input("Enter officer username: ")
    password = input("Enter officer password: ")

    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')

    new_user = User(username=username, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    print(f"✅ Officer account created successfully: {username}")
