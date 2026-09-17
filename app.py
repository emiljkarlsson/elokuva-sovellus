from flask import Flask
from flask import render_template, request

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", methods=["POST"])
from flask import Flask

@app.route("/add_movie", methods=["POST"])
def add():
    return render_template("add.html")