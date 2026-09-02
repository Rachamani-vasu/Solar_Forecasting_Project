from flask import Flask, render_template, request, redirect, session
import sqlite3
import hashlib
import re

app = Flask(__name__)
app.secret_key = "solar_forecasting_secret_key"

DATABASE = "solar_users.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    connection.commit()

    # Create ONLY ONE admin account
    admin_exists = connection.execute("""
        SELECT id
        FROM users
        WHERE role = 'admin'
        LIMIT 1
    """).fetchone()

    if admin_exists is None:
        admin_password = hashlib.sha256(
            "admin123".encode()
        ).hexdigest()

        connection.execute("""
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

        connection.commit()

    connection.close()


# =========================
# PASSWORD VALIDATION
# =========================

def valid_password(password):
    if len(password) < 8:
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"[0-9]", password):
        return False

    if not re.search(r"[^A-Za-z0-9]", password):
        return False

    return True


# =========================
# LOGIN
# =========================

@app.route("/", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

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

        error = "Invalid username or password."

    return render_template(
        "login.html",
        error=error
    )


# =========================
# REGISTER USER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    error = None

    if request.method == "POST":

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

        if not full_name:
            error = "Full name is required."

        elif not username:
            error = "Username is required."

        elif not email:
            error = "Email is required."

        elif not valid_password(password):
            error = (
                "Password must contain at least 8 characters, "
                "one uppercase letter, one lowercase letter, "
                "one number, and one special character."
            )

        else:

            connection = get_db_connection()

            existing_user = connection.execute("""
                SELECT id
                FROM users
                WHERE username = ?
            """, (username,)).fetchone()

            if existing_user:

                error = "Username already exists."

                connection.close()

            else:

                hashed_password = hashlib.sha256(
                    password.encode()
                ).hexdigest()

                connection.execute("""
                    INSERT INTO users
                    (full_name, username, email, password, role)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    full_name,
                    username,
                    email,
                    hashed_password,
                    "user"
                ))

                connection.commit()
                connection.close()

                return redirect("/?registered=1")

    return render_template(
        "register.html",
        error=error
    )


# =========================
# ADMIN DASHBOARD
# =========================

@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "admin":
        return "Access Denied - Admins Only", 403

    return render_template("admin.html")


# =========================
# USER DASHBOARD
# =========================

@app.route("/user")
def user_dashboard():

    if "user_id" not in session:
        return redirect("/")

    return render_template("user.html")


# =========================
# MANAGE USERS
# =========================

@app.route("/users")
def users():

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "admin":
        return "Access Denied - Admins Only", 403

    connection = get_db_connection()

    users = connection.execute("""
        SELECT id, full_name, username, email, role
        FROM users
        ORDER BY id
    """).fetchall()

    connection.close()

    return render_template(
        "users.html",
        users=users
    )


# =========================
# ADMIN CREATES NORMAL USER
# =========================

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

    if not full_name:
        return "Full name is required.", 400

    if not username:
        return "Username is required.", 400

    if not email:
        return "Email is required.", 400

    if not valid_password(password):
        return (
            "Password must contain at least 8 characters, "
            "one uppercase letter, one lowercase letter, "
            "one number, and one special character.",
            400
        )

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
            "user"
        ))

        connection.commit()

    except sqlite3.IntegrityError:

        connection.close()

        return "Username already exists.", 400

    connection.close()

    return redirect("/users")


# =========================
# DELETE NORMAL USER
# =========================

@app.route(
    "/delete-user/<int:user_id>",
    methods=["POST"]
)
def delete_user(user_id):

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "admin":
        return "Access Denied - Admins Only", 403

    # Admin cannot delete their own account
    if user_id == session.get("user_id"):
        return "You cannot delete the main administrator.", 400

    connection = get_db_connection()

    user = connection.execute("""
        SELECT role
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    if user is None:

        connection.close()

        return "User not found.", 404

    # Admin accounts can never be deleted
    if user["role"] == "admin":

        connection.close()

        return "The administrator account cannot be deleted.", 403

    connection.execute("""
        DELETE FROM users
        WHERE id = ?
    """, (user_id,))

    connection.commit()
    connection.close()

    return redirect("/users")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# START APPLICATION
# =========================

if __name__ == "__main__":

    create_database()

    print("")
    print("======================================")
    print("       SOLARVISION STARTING")
    print("======================================")
    print("")
    print("Login: http://127.0.0.1:5050")
    print("")

    app.run(
        host="0.0.0.0",
        port=5050,
        debug=True
    )
