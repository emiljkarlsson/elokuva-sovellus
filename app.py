from flask import Flask
from flask import render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import config

app = Flask(__name__)
app.secret_key = config.secret_key

db = sqlite3.connect("database.db")

db.execute("""
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        year INTEGER NOT NULL,
        genre TEXT NOT NULL,
        description TEXT NOT NULL
    )
""")

db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
""")

db.commit()
db.close()

@app.route("/")
def index():
    db = sqlite3.connect("database.db")
    movies = db.execute("SELECT * FROM movies").fetchall()
    db.close()

    return render_template("index.html", movies=movies)


@app.route("/add_movie", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        name = request.form["name"]
        year = request.form["year"]
        description = request.form["description"]
        genres = request.form.getlist("genre")

        db = sqlite3.connect("database.db")

        db.execute(
            "INSERT INTO movies (name, year, genre, description) VALUES (?, ?, ?, ?)",
            [name, year, ", ".join(genres), description]
        )

        db.commit()
        db.close()

        return redirect("/")

    return render_template("add.html")



@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/create", methods=["POST"])
def create():
    username = request.form["username"].strip()
    password1 = request.form["password1"]
    password2 = request.form["password2"]

    if not username or not password1:
        return "VIRHE: tunnus ja salasana eivät saa olla tyhjiä"
    if password1 != password2:
        return "VIRHE: salasanat eivät ole samat"

    password_hash = generate_password_hash(password1)

    db = sqlite3.connect("database.db")
    try:
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            [username, password_hash]
        )
        db.commit()
    except sqlite3.IntegrityError:
        return "VIRHE: tunnus on jo varattu"
    finally:
        db.close()

    return 'Tunnus luotu. <a href="/login">Kirjaudu sisään</a>'

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form["username"]
    password = request.form["password"]

    sql = "SELECT password_hash FROM users WHERE username = ?"
    db = sqlite3.connect("database.db")
    result = db.execute(sql, [username]).fetchone()
    db.close()

    if result and check_password_hash(result[0], password):
        session["username"] = username
        return redirect("/")
    else:
        return "VIRHE: väärä tunnus tai salasana"

@app.route("/logout")
def logout():
    del session["username"]
    return redirect("/")