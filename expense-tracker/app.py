import csv, io, os, sqlite3
from datetime import date
from functools import wraps
from flask import (Flask, Response, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE, "expenses.db"))
CATEGORIES = ["Food", "Transport", "Rent", "Shopping", "Bills",
              "Health", "Entertainment", "Other"]


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT DEFAULT '');
        """)


def login_required(f):
    @wraps(f)
    def wrapper(*a, **k):
        if "uid" not in session:
            return redirect(url_for("login"))
        return f(*a, **k)
    return wrapper


@app.route("/")
def index():
    return redirect(url_for("dashboard" if "uid" in session else "login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        if len(pw) < 6:
            flash("Password must be at least 6 characters.")
        else:
            try:
                db().execute(
                    "INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                    (name, email, generate_password_hash(pw)))
                db().commit()
                flash("Account created. Log in to continue.")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That email is already registered. Log in instead.")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db().execute("SELECT * FROM users WHERE email=?",
                         (request.form["email"].strip().lower(),)).fetchone()
        if u and check_password_hash(u["password_hash"], request.form["password"]):
            session.clear()
            session["uid"], session["name"] = u["id"], u["name"]
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def month_rows(uid, month):
    return db().execute(
        "SELECT * FROM expenses WHERE user_id=? AND substr(date,1,7)=? "
        "ORDER BY date DESC, id DESC", (uid, month)).fetchall()


@app.route("/dashboard")
@login_required
def dashboard():
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    rows = month_rows(session["uid"], month)
    totals = {}
    for r in rows:
        totals[r["category"]] = totals.get(r["category"], 0) + r["amount"]
    return render_template("dashboard.html", rows=rows, month=month,
                           totals=totals, total=sum(totals.values()),
                           categories=CATEGORIES, today=date.today().isoformat())


@app.route("/add", methods=["POST"])
@login_required
def add():
    f = request.form
    try:
        amount = round(float(f["amount"]), 2)
        if amount <= 0:
            raise ValueError
        date.fromisoformat(f["date"])
    except ValueError:
        flash("Enter an amount above 0 and a valid date.")
        return redirect(url_for("dashboard"))
    cat = f["category"] if f["category"] in CATEGORIES else "Other"
    db().execute(
        "INSERT INTO expenses(user_id,amount,category,date,note) VALUES(?,?,?,?,?)",
        (session["uid"], amount, cat, f["date"], f.get("note", "").strip()[:200]))
    db().commit()
    return redirect(url_for("dashboard", month=f["date"][:7]))


@app.route("/delete/<int:eid>", methods=["POST"])
@login_required
def delete(eid):
    db().execute("DELETE FROM expenses WHERE id=? AND user_id=?",
                 (eid, session["uid"]))
    db().commit()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/export")
@login_required
def export():
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Category", "Amount", "Note"])
    for r in month_rows(session["uid"], month):
        w.writerow([r["date"], r["category"], r["amount"], r["note"]])
    return Response(buf.getvalue(), mimetype="text/csv", headers={
        "Content-Disposition": f"attachment; filename=expenses-{month}.csv"})


init_db()

if __name__ == "__main__":
    app.run(debug=True)
