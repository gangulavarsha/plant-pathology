# Plant Pathology using ML

Web app that predicts plant leaf diseases from an image. Roles: **User, Farmer, Admin**.

## Structure
    backend/    Flask app (app.py), ML (ml.py, train.py), SQLite DB
    frontend/   templates/ (HTML), static/css/style.css, static/js/main.js

## Run
    pip install -r requirements.txt
    cd backend
    python make_samples.py
    python train.py
    python app.py        # http://127.0.0.1:5000

Admin: admin@plant.com / admin123

## Features
- User: register, login, update profile, predict, ask query, view queries/updates, history
- Farmer: register, login, update profile, predict, view queries
- Admin: view users, view farmers, freeze farmers, reply to queries, view predictions

For real accuracy: `python train.py dataset/` with images in dataset/<ClassName>/*.jpg
