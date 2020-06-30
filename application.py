import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for, make_response
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
import pytz
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests


from helpers import login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

scopes = 'https://www.googleapis.com/auth/calendar'
# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def _force_https():
    # my local dev is set on debug, but on AWS it's not (obviously)
    # I don't need HTTPS on local, change this to whatever condition you want.
    if not app.debug:
        from flask import _request_ctx_stack
        if _request_ctx_stack is not None:
            reqctx = _request_ctx_stack.top
            reqctx.url_adapter.url_scheme = 'https'

app.before_request(_force_https)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


###----- Credits ----->
@app.route("/credits", methods=["GET", "POST"])
def credits():

    if request.method == "POST":

        name = request.form.get("name")
        job = request.form.get("job")
        location = request.form.get("location")
        company = request.form.get("company")

        # Error checking
        if not name:
            flash("Please enter name")
            return redirect("/credits")
        if not job:
            flash("Please enter job or specialism")
            return redirect("/credits")
        if not location:
            flash("Please enter location")
            return redirect("/credits")
        if not company:
            flash("Please enter company, freelance, or student")
            return redirect("/credits")

        #Add to notes table
        db.execute("INSERT INTO credits (name, job, location, company) VALUES (:name, :job, :location, :company)",
        {"name": name,
        "job": job,
        "location": location,
        "company": company})
        db.commit()

        return redirect("/credits")

    list = db.execute("SELECT * FROM credits ORDER by id Desc").fetchall()

    return render_template("credits.html", list=list)



""" Errors """

###----- Errors ----->
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    flash(f"Error {e.code}, {e.name}")
    return redirect("/")


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
