from flask import Flask, render_template, request, redirect, session
import sqlite3
import hashlib
import os

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "solar_forecasting_secret_key"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "solar_users.db")


def create_database():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    admin_password = hashlib.sha256(
        "admin123".encode()
    ).hexdigest()

    try:
        cursor.execute("""
            INSERT INTO users
            (full_name, username, email, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "System Administrator",
            "admin",
            "admin@example.com",
            admin_password,
            "admin"
        ))
    except sqlite3.IntegrityError:
        pass

    user_password = hashlib.sha256(
        "user123".encode()
    ).hexdigest()

    try:
        cursor.execute("""
            INSERT INTO users
            (full_name, username, email, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "System User",
            "user",
            "user@example.com",
            user_password,
            "user"
        ))
    except sqlite3.IntegrityError:
        pass

    connection.commit()
    connection.close()


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Please enter username and password"

            return render_template(
                "login.html",
                error=error
            )

        hashed_password = hashlib.sha256(
            password.encode()
        ).hexdigest()

        connection = get_db_connection()

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE username = ?
            AND password = ?
        """, (
            username,
            hashed_password
        )).fetchone()

        connection.close()

        if user:

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin")

            return redirect("/user")

        error = "Invalid username or password"

    return render_template(
        "login.html",
        error=error
    )


@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "admin":
        return "Access Denied - Admins Only", 403

    return render_template("admin.html")


@app.route("/user")
def user_dashboard():

    if "user_id" not in session:
        return redirect("/")

    return render_template("user.html")


@app.route("/users")
def users():

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "admin":
        return "Access Denied - Admins Only", 403

    connection = get_db_connection()

    users = connection.execute("""
        SELECT
            id,
            full_name,
            username,
            email,
            role
        FROM users
        ORDER BY id
    """).fetchall()

    connection.close()

    return render_template(
        "users.html",
        users=users
    )


@app.route("/add-user", methods=["POST"])
def add_user():

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "admin":
        return "Access Denied - Admins Only", 403

    full_name = request.form.get(
        "full_name", ""
    ).strip()

    username = request.form.get(
        "username", ""
    ).strip()

    email = request.form.get(
        "email", ""
    ).strip()

    password = request.form.get(
        "password", ""
    )

    role = request.form.get(
        "role", ""
    ).strip().lower()

    if not full_name:
        return "Full name is required", 400

    if not username:
        return "Username is required", 400

    if not email:
        return "Email is required", 400

    if not password:
        return "Password is required", 400

    if role not in ["admin", "user"]:
        return "Invalid role", 400

    hashed_password = hashlib.sha256(
        password.encode()
    ).hexdigest()

    connection = get_db_connection()

    try:

        connection.execute("""
            INSERT INTO users
            (full_name, username, email, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            full_name,
            username,
            email,
            hashed_password,
            role
        ))

        connection.commit()

    except sqlite3.IntegrityError:

        connection.close()

        return "Username already exists", 400

    connection.close()

    return redirect("/users")


@app.route(
    "/delete-user/<int:user_id>",
    methods=["POST"]
)
def delete_user(user_id):

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "admin":
        return "Access Denied - Admins Only", 403

    if user_id == session.get("user_id"):
        return "You cannot delete your own account.", 400

    connection = get_db_connection()

    connection.execute("""
        DELETE FROM users
        WHERE id = ?
    """, (user_id,))

    connection.commit()
    connection.close()

    return redirect("/users")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# IMPORTANT:
# Create the database when Flask/Gunicorn loads app.py.
create_database()


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5050
        )
    )

    print("======================================")
    print("       SOLARVISION STARTING")
    print("======================================")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
