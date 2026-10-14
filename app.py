from flask import Flask
from flask import render_template, request, redirect, session, abort, make_response
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import config
import secrets

app = Flask(__name__)
app.secret_key = config.secret_key


def require_login():
    if "user_id" not in session:
        abort(403)


def check_csrf():
    if "csrf_token" not in session:
        abort(403)
    if request.form.get("csrf_token") != session["csrf_token"]:
        abort(403)


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
    CREATE TABLE IF NOT EXISTS movie_images (
        movie_id INTEGER PRIMARY KEY REFERENCES movies(id),
        image BLOB NOT NULL
    )
""")

db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        image BLOB
    )
""")

db.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER NOT NULL REFERENCES movies(id),
        user_id INTEGER NOT NULL REFERENCES users(id),
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        comment TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

    require_login()

    if request.method == "POST":
        check_csrf()
        name = request.form["name"]
        year = request.form["year"]
        description = request.form["description"]
        genres = request.form.getlist("genre")

        file = request.files.get("image")
        image = None
        if file and file.filename:
            if not file.filename.lower().endswith(".jpg"):
                return "VIRHE: väärä tiedostomuoto"
            image = file.read()
            if len(image) > 100 * 1024:
                return "VIRHE: liian suuri kuva"

        db = sqlite3.connect("database.db")

        cursor = db.execute(
            "INSERT INTO movies (name, year, genre, description) VALUES (?, ?, ?, ?)",
            [name, year, ", ".join(genres), description]
        )

        if image:
            db.execute(
                "INSERT INTO movie_images (movie_id, image) VALUES (?, ?)",
                [cursor.lastrowid, image]
            )

        db.commit()
        db.close()

        return redirect("/")

    return render_template("add.html")

@app.route("/edit_movie/<int:movie_id>", methods=["GET", "POST"])
def edit_movie(movie_id):
    require_login()

    db = sqlite3.connect("database.db")
    movie = db.execute(
        "SELECT * FROM movies WHERE id = ?",
        [movie_id]
    ).fetchone()
    db.close()

    if not movie:
        abort(404)

    if request.method == "GET":
        genres = movie[3].split(", ")
        return render_template("edit.html", movie=movie, genres=genres)

    check_csrf()

    name = request.form["name"]
    year = request.form["year"]
    description = request.form["description"]
    genres = request.form.getlist("genre")

    file = request.files.get("image")
    image = None
    if file and file.filename:
        if not file.filename.lower().endswith(".jpg"):
            return "VIRHE: väärä tiedostomuoto"
        image = file.read()
        if len(image) > 100 * 1024:
            return "VIRHE: liian suuri kuva"

    db = sqlite3.connect("database.db")

    db.execute(
        "UPDATE movies SET name = ?, year = ?, genre = ?, description = ? WHERE id = ?",
        [name, year, ", ".join(genres), description, movie_id]
    )

    if image:
        db.execute(
            "INSERT OR REPLACE INTO movie_images (movie_id, image) VALUES (?, ?)",
            [movie_id, image]
        )

    db.commit()
    db.close()

    return redirect("/movie/" + str(movie_id))


@app.route("/movie/<int:movie_id>")
def movie(movie_id):
    db = sqlite3.connect("database.db")
    movie = db.execute(
        "SELECT * FROM movies WHERE id = ?",
        [movie_id]
    ).fetchone()
    has_image = db.execute(
        "SELECT 1 FROM movie_images WHERE movie_id = ?",
        [movie_id]
    ).fetchone() is not None
    db.close()

    if not movie:
        abort(404)

    return render_template("movie.html", movie=movie, has_image=has_image)


@app.route("/movie/<int:movie_id>/image")
def movie_image(movie_id):
    db = sqlite3.connect("database.db")
    result = db.execute(
        "SELECT image FROM movie_images WHERE movie_id = ?",
        [movie_id]
    ).fetchone()
    db.close()

    if not result:
        abort(404)

    response = make_response(bytes(result[0]))
    response.headers.set("Content-Type", "image/jpeg")
    return response

@app.route("/search")
def search():
    query = request.args.get("query")
    results = []

    if query:
        like = "%" + query + "%"
        db = sqlite3.connect("database.db")
        results = db.execute(
            """SELECT * FROM movies
               WHERE name LIKE ? OR genre LIKE ? OR description LIKE ?
               ORDER BY name""",
            [like, like, like]
        ).fetchall()
        db.close()

    return render_template("index.html", query=query, results=results)
    results = []

    if query:
        like = "%" + query + "%"
        db = sqlite3.connect("database.db")
        results = db.execute(
            """SELECT * FROM movies
               WHERE name LIKE ? OR genre LIKE ? OR description LIKE ?
               ORDER BY name""",
            [like, like, like]
        ).fetchall()
        db.close()

    return render_template("index.html", query=query, results=results)

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

    username = request.form["username"].strip()
    password = request.form["password"]

    db = sqlite3.connect("database.db")
    result = db.execute(
        "SELECT id, password_hash FROM users WHERE username = ?",
        [username]
    ).fetchone()
    db.close()

    if result and check_password_hash(result[1], password):
        session["user_id"] = result[0]
        session["username"] = username
        session["csrf_token"] = secrets.token_hex(16)
        return redirect("/")

    return 'VIRHE: väärä tunnus tai salasana. <a href="/login">Yritä uudelleen</a>'


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    session.pop("csrf_token", None)
    return redirect("/")