import functools

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from .db import get_db, db_query

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        error = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."

        if error is None:
            try:
                try:
                    db.execute(
                        "INSERT INTO app_user (username, password) VALUES (?, ?)",
                        (username, generate_password_hash(password)),
                    )
                    db.commit()
                except AttributeError:
                    sql = (
                        "INSERT INTO app_user (username, password) VALUES ('%s', '%s')"
                        % (
                            username,
                            generate_password_hash(password),
                        )
                    )
                    try:
                        db_query(sql)
                    except Exception as e:
                        # error = f"User {username} is already registered. ({e})"
                        raise db.IntegrityError
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        error = None
        try:
            db = get_db()
            user = db.execute(
                "SELECT * FROM app_user WHERE username = ?", (username,)
            ).fetchone()
        except (AttributeError, TypeError):
            sql = "SELECT * FROM app_user WHERE username = '%s'" % username
            try:
                user = db_query(sql)[0]
            except IndexError:
                user = None

        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user["password"], password):
            error = "Incorrect password."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html")


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        try:
            g.user = (
                get_db()
                .execute("SELECT * FROM app_user WHERE id = ?", (user_id,))
                .fetchone()
            )
        except AttributeError:
            sql = "SELECT * FROM app_user WHERE id = %s" % user_id
            try:
                g.user = db_query(sql)[0]
            except IndexError:
                g.user = None


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view
