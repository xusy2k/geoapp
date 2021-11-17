from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from .auth import login_required
from .db import get_db, db_query

bp = Blueprint("blog", __name__)


@bp.route("/")
def index():
    try:
        db = get_db()
        posts_qs = db.execute(
            "SELECT p.id, title, body, created, author_id, username"
            " FROM app_post p JOIN app_user u ON p.author_id = u.id"
            " ORDER BY created DESC"
        )
        posts = posts_qs.fetchall()
    except AttributeError:
        sql = (
            "SELECT p.id, title, body, created, author_id, username"
            " FROM app_post p JOIN app_user u ON p.author_id = u.id"
            " ORDER BY created DESC"
        )
        posts = db_query(sql)

    return render_template("blog/index.html", posts=posts)


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO app_post (title, body, author_id)" " VALUES (?, ?, ?)",
                    (title, body, g.user["id"]),
                )
                db.commit()
            except AttributeError:
                sql = (
                    "INSERT INTO app_post (title, body, author_id)"
                    " VALUES ('%s', '%s', '%s')" % (title, body, g.user["id"])
                )
                db_query(sql)

            return redirect(url_for("blog.index"))

    return render_template("blog/create.html")


def get_post(id, check_author=True):
    try:
        post = (
            get_db()
            .execute(
                "SELECT p.id, title, body, created, author_id, username"
                " FROM app_post p JOIN user u ON p.author_id = u.id"
                " WHERE p.id = ?",
                (id,),
            )
            .fetchone()
        )
    except AttributeError:
        sql = (
            "SELECT p.id, title, body, created, author_id, username"
            " FROM app_post p JOIN app_user u ON p.author_id = u.id"
            " WHERE p.id = %s" % id
        )
        post = db_query(sql)[0]

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post["author_id"] != g.user["id"]:
        abort(403)

    return post


@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    post = get_post(id)

    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            try:
                db = get_db()
                db.execute(
                    "UPDATE app_post SET title = ?, body = ?" " WHERE id = ?",
                    (title, body, id),
                )
                db.commit()
            except AttributeError:
                sql = "UPDATE app_post SET title = '%s', body = '%s' WHERE id = %s" % (
                    title,
                    body,
                    id,
                )
                db_query(sql)

            return redirect(url_for("blog.index"))

    return render_template("blog/update.html", post=post)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    get_post(id)
    try:
        db = get_db()
        db.execute("DELETE FROM app_post WHERE id = ?", (id,))
        db.commit()
    except AttributeError:
        sql = "DELETE FROM app_post WHERE id = %s" % id
        db_query(sql)
    return redirect(url_for("blog.index"))
