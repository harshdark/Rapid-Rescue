
---

# Rapid-Rescue 🚓

**A live complaint and emergency management system for the Haryana Police.**

Rapid-Rescue is a web-based platform designed to streamline real-time reporting of complaints and emergencies, allowing police officers to respond efficiently. The system includes complaint submission by citizens, officer dashboards, and task assignment with status tracking.

---

## 📂 Project Structure

```
Rapid-Rescue/
├── app.py                  # Main Flask application
├── create_officer.py       # Script to create officer records
├── models.py               # Database models
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in repo)
├── static/                 # Static files (CSS, images, JS)
├── templates/              # HTML templates
├── uploads/                # Uploaded files
├── utils/                  # Helper scripts
├── instance/               # Instance-specific config
└── README.md               # Project documentation
```

---

## ⚙️ Features (Phase 1 & Phase 2 Completed)

**Phase 1: Basic Complaint Management**

* Citizen complaint submission
* Officer login and dashboard
* Complaint status tracking

**Phase 2: UI & Dashboard Enhancements**

* Professional login portal design
* Enhanced homepage with floating logo and job card
* Animated card borders for police portal
* Responsive and modern UI
* CSS and static assets structured for maintainability

**Phase 3 (Upcoming)**

* Real-time notifications for officers
* Advanced task assignment and priority system
* Data analytics dashboard
* Role-based access control

---

## 🚀 Installation

1. Clone the repository:

```bash
git clone https://github.com/harshdark/Rapid-Rescue.git
cd Rapid-Rescue
```

2. Create virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

3. Setup `.env` file with your database credentials.

4. Run the application:

```bash
python app.py
```

5. Access the portal at `http://localhost:5000`.

---

## 🛠️ Technologies Used

* Python 3.x
* Flask
* SQLAlchemy (Database ORM)
* HTML, CSS, JavaScript
* Jinja2 Templates

---

## 📌 Notes

* All sensitive information (passwords, API keys, DB credentials) should be kept in `.env`.
* Images, CSS, and JS are in the `static/` folder.
* Templates are in `templates/` folder.

---

