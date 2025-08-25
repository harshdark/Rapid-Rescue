from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    username = input("Enter username: ")
    password = input("Enter password: ")

    # role select
    print("Select role:")
    print("1. user")
    print("2. officer")
    print("3. admin")
    choice = input("Enter role number (1/2/3): ")

    role_map = {"1": "user", "2": "officer", "3": "admin"}
    role = role_map.get(choice, "user")  # default user

    # check if already exists
    existing = User.query.filter_by(username=username).first()
    if existing:
        print(f"❌ Username '{username}' already exists with role={existing.role}")
    else:
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        print(f"✅ {role.capitalize()} account created successfully: {username}")
