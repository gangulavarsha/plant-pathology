import os, sqlite3, uuid
from functools import wraps
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import ml

app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")
app.secret_key = "change-me"
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "plant.db")
UPLOADS = os.path.join(BASE, "uploads")

# ---------- database ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def init_db():
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT,
      role TEXT CHECK(role IN ('user','farmer','admin')), phone TEXT, location TEXT,
      is_frozen INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS predictions(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, image TEXT, disease TEXT,
      confidence REAL, treatment TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS queries(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, question TEXT, answer TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP, answered_at TEXT);
    """)
    if not c.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
        c.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                  ("Admin", "admin@plant.com", generate_password_hash("admin123"), "admin"))
    c.commit(); c.close()

# ---------- auth helpers ----------
def login_required(*roles):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if "uid" not in session:
                return redirect(url_for("login"))
            if roles and session["role"] not in roles:
                flash("Not allowed for your role."); return redirect(url_for("home"))
            return f(*a, **k)
        return w
    return deco

# ---------- common ----------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        role = f["role"] if f["role"] in ("user", "farmer") else "user"
        try:
            db().execute("INSERT INTO users(name,email,password,role,phone,location) VALUES(?,?,?,?,?,?)",
                         (f["name"], f["email"], generate_password_hash(f["password"]), role, f["phone"], f["location"]))
            db().commit(); flash("Registered! Please login."); return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db().execute("SELECT * FROM users WHERE email=?", (request.form["email"],)).fetchone()
        if not u or not check_password_hash(u["password"], request.form["password"]):
            flash("Invalid credentials.")
        elif u["is_frozen"]:
            flash("Your account is frozen by admin.")
        else:
            session.update(uid=u["id"], role=u["role"], name=u["name"])
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.route("/profile", methods=["GET", "POST"])
@login_required()
def profile():
    if request.method == "POST":
        f = request.form
        db().execute("UPDATE users SET name=?, phone=?, location=? WHERE id=?",
                     (f["name"], f["phone"], f["location"], session["uid"]))
        db().commit(); session["name"] = f["name"]; flash("Profile updated.")
    u = db().execute("SELECT * FROM users WHERE id=?", (session["uid"],)).fetchone()
    return render_template("profile.html", u=u)

@app.route("/dashboard")
@login_required()
def dashboard():
    d, uid = db(), session["uid"]
    one = lambda sql, *a: d.execute(sql, a).fetchone()[0]
    if session["role"] == "admin":
        stats = [("Users", one("SELECT COUNT(*) FROM users WHERE role='user'")),
                 ("Farmers", one("SELECT COUNT(*) FROM users WHERE role='farmer'")),
                 ("Predictions", one("SELECT COUNT(*) FROM predictions")),
                 ("Pending queries", one("SELECT COUNT(*) FROM queries WHERE answer IS NULL"))]
    else:
        stats = [("My predictions", one("SELECT COUNT(*) FROM predictions WHERE user_id=?", uid)),
                 ("My queries", one("SELECT COUNT(*) FROM queries WHERE user_id=?", uid)),
                 ("Answered", one("SELECT COUNT(*) FROM queries WHERE user_id=? AND answer IS NOT NULL", uid))]
    return render_template("dashboard.html", stats=stats)

# ---------- user / farmer ----------
@app.route("/predict", methods=["GET", "POST"])
@login_required("user", "farmer")
def predict():
    result = None
    if request.method == "POST" and request.files.get("image"):
        fn = uuid.uuid4().hex + ".png"
        path = os.path.join(UPLOADS, fn)
        request.files["image"].save(path)
        label, conf, tip = ml.predict(path)
        db().execute("INSERT INTO predictions(user_id,image,disease,confidence,treatment) VALUES(?,?,?,?,?)",
                     (session["uid"], fn, label, conf, tip)); db().commit()
        result = dict(image=fn, disease=label, confidence=round(conf * 100, 1), treatment=tip)
    return render_template("predict.html", r=result)

@app.route("/history")
@login_required("user", "farmer")
def history():
    rows = db().execute("SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC", (session["uid"],)).fetchall()
    return render_template("history.html", rows=rows)

@app.route("/ask", methods=["GET", "POST"])
@login_required("user")
def ask():
    if request.method == "POST":
        db().execute("INSERT INTO queries(user_id,question) VALUES(?,?)", (session["uid"], request.form["question"]))
        db().commit(); flash("Query submitted."); return redirect(url_for("my_queries"))
    return render_template("ask.html")

@app.route("/queries")
@login_required("user", "farmer")
def my_queries():
    if session["role"] == "user":   # own queries + admin updates
        rows = db().execute("SELECT q.*, u.name FROM queries q JOIN users u ON u.id=q.user_id "
                            "WHERE user_id=? ORDER BY q.id DESC", (session["uid"],)).fetchall()
    else:                           # farmers view answered queries
        rows = db().execute("SELECT q.*, u.name FROM queries q JOIN users u ON u.id=q.user_id "
                            "WHERE answer IS NOT NULL ORDER BY q.id DESC").fetchall()
    return render_template("queries.html", rows=rows)

@app.route("/uploads/<fn>")
@login_required()
def uploads(fn):
    return send_from_directory(UPLOADS, fn)

# ---------- admin ----------
@app.route("/admin/users")
@login_required("admin")
def admin_users():
    role = request.args.get("role")  # view users / view farmers
    sql, args = "SELECT * FROM users WHERE role!='admin'", ()
    if role in ("user", "farmer"):
        sql += " AND role=?"; args = (role,)
    return render_template("admin_users.html", rows=db().execute(sql, args).fetchall(), role=role)

@app.route("/admin/freeze/<int:uid>")
@login_required("admin")
def freeze(uid):
    db().execute("UPDATE users SET is_frozen = 1 - is_frozen WHERE id=? AND role!='admin'", (uid,))
    db().commit(); return redirect(request.referrer or url_for("admin_users"))

@app.route("/admin/queries", methods=["GET", "POST"])
@login_required("admin")
def admin_queries():
    if request.method == "POST":
        db().execute("UPDATE queries SET answer=?, answered_at=CURRENT_TIMESTAMP WHERE id=?",
                     (request.form["answer"], request.form["qid"])); db().commit()
    rows = db().execute("SELECT q.*, u.name FROM queries q JOIN users u ON u.id=q.user_id ORDER BY q.id DESC").fetchall()
    return render_template("admin_queries.html", rows=rows)

@app.route("/admin/predictions")
@login_required("admin")
def admin_predictions():
    rows = db().execute("SELECT p.*, u.name FROM predictions p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC").fetchall()
    return render_template("admin_predictions.html", rows=rows)

if __name__ == "__main__":
    os.makedirs(UPLOADS, exist_ok=True)
    init_db()
    app.run(debug=True)
