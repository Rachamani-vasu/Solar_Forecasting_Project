from flask import Flask, render_template, request, redirect, session
import sqlite3
import hashlib
import os
import pandas as pd
import joblib

app = Flask(__name__)
app.secret_key = "solarvision-secret-key"

DATABASE = "solar_users.db"

UPLOAD_FOLDER = "uploads"
MODEL_FOLDER = "models"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MODEL_FOLDER, exist_ok=True)


# =========================================================
# DATABASE
# =========================================================

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_database():

    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    """)

    # Create default admin if no admin exists
    admin_count = connection.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin'"
    ).fetchone()[0]

    if admin_count == 0:

        connection.execute("""
            INSERT INTO users
            (username, password, full_name, email, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "admin",
            hash_password("admin123"),
            "System Administrator",
            "admin@example.com",
            "admin"
        ))

    connection.commit()
    connection.close()


create_database()


# =========================================================
# HOME / USER LOGIN
# =========================================================

@app.route("/", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        hashed_password = hash_password(password)

        connection = get_db_connection()

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE username = ?
            AND password = ?
            AND role = 'user'
        """, (username, hashed_password)).fetchone()

        connection.close()

        if user:

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]

            return redirect("/user")

        error = "Invalid username or password."

    return render_template("login.html", error=error)


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        hashed_password = hash_password(password)

        connection = get_db_connection()

        admin = connection.execute("""
            SELECT *
            FROM users
            WHERE username = ?
            AND password = ?
            AND role = 'admin'
        """, (username, hashed_password)).fetchone()

        connection.close()

        if admin:

            session["user_id"] = admin["id"]
            session["username"] = admin["username"]
            session["full_name"] = admin["full_name"]
            session["role"] = "admin"

            return redirect("/admin")

        error = "Invalid administrator username or password."

    return render_template("admin_login.html", error=error)


# =========================================================
# USER REGISTRATION
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()

        if len(password) < 8:
            error = "Password must contain at least 8 characters."

        elif not any(c.isupper() for c in password):
            error = "Password must contain an uppercase letter."

        elif not any(c.islower() for c in password):
            error = "Password must contain a lowercase letter."

        elif not any(c.isdigit() for c in password):
            error = "Password must contain a number."

        elif not any(not c.isalnum() for c in password):
            error = "Password must contain a special character."

        else:

            connection = get_db_connection()

            try:

                connection.execute("""
                    INSERT INTO users
                    (username, password, full_name, email, role)
                    VALUES (?, ?, ?, ?, 'user')
                """, (
                    username,
                    hash_password(password),
                    full_name,
                    email
                ))

                connection.commit()
                connection.close()

                return redirect("/")

            except sqlite3.IntegrityError:

                connection.close()
                error = "Username already exists."

    return render_template("register.html", error=error)


# =========================================================
# USER DASHBOARD
# =========================================================

@app.route("/user")
def user_dashboard():

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "user":
        return redirect("/admin")

    generation = {
        "records": 0,
        "average": 0,
        "maximum": 0,
        "minimum": 0
    }

    hourly_generation = []

    alert = {
        "status": "NO DATA",
        "message": "No generation data available."
    }

    prepared_path = os.path.join(
        UPLOAD_FOLDER,
        "prepared_solar_dataset.csv"
    )

    if os.path.exists(prepared_path):
        try:
            df = pd.read_csv(prepared_path)

            generation = {
                "records": len(df),
                "average": round(float(df["Power"].mean()), 2),
                "maximum": round(float(df["Power"].max()), 2),
                "minimum": round(float(df["Power"].min()), 2)
            }

            hourly = df.groupby("Hour")["Power"].mean().round(2)

            hourly_generation = [
                {
                    "hour": int(hour),
                    "power": float(power)
                }
                for hour, power in hourly.items()
            ]

            latest_power = float(df["Power"].iloc[-1])

            if latest_power <= 0:
                alert = {
                    "status": "ALERT",
                    "message": "No solar power generation detected in the latest record."
                }
            else:
                alert = {
                    "status": "NORMAL",
                    "message": f"Solar generation is active. Latest generation: {round(latest_power, 2)}"
                }

        except Exception:
            pass

    connection = get_db_connection()

    predictions = connection.execute(
        """
        SELECT prediction, created_at
        FROM predictions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 5
        """,
        (session.get("user_id"),)
    ).fetchall()

    connection.close()

    return render_template(
        "user.html",
        username=session.get("username"),
        full_name=session.get("full_name"),
        generation=generation,
        hourly_generation=hourly_generation,
        alert=alert,
        predictions=predictions
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        return redirect("/admin-login")

    if session.get("role") != "admin":
        return redirect("/")

    metrics = None

    metrics_path = os.path.join(
        MODEL_FOLDER,
        "model_metrics.json"
    )

    if os.path.exists(metrics_path):
        try:
            import json

            with open(metrics_path, "r") as f:
                metrics = json.load(f)

        except Exception:
            metrics = None

    connection = get_db_connection()

    total_users = connection.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'user'"
    ).fetchone()[0]

    total_predictions = connection.execute(
        "SELECT COUNT(*) FROM predictions"
    ).fetchone()[0]

    latest_prediction_row = connection.execute(
        """
        SELECT prediction
        FROM predictions
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    latest_prediction = (
        latest_prediction_row["prediction"]
        if latest_prediction_row
        else 0
    )



    forecast_history = connection.execute(
        """
        SELECT predictions.prediction,
               predictions.created_at,
               users.username
        FROM predictions
        LEFT JOIN users
        ON predictions.user_id = users.id
        ORDER BY predictions.id DESC
        LIMIT 10
        """
    ).fetchall()

    connection.close()

    return render_template(
        "admin.html",
        username=session.get("username"),
        full_name=session.get("full_name"),
        metrics=metrics,
        forecast_history=forecast_history,
        total_users=total_users,
        total_predictions=total_predictions,
        latest_prediction=latest_prediction
    )


# =========================================================
# DATA MANAGEMENT
# =========================================================

@app.route("/data")
def data_management():

    if "user_id" not in session:
        return redirect("/admin-login")

    if session.get("role") != "admin":
        return redirect("/")

    dataset_info = None
    validation = None
    preview = None
    preparation = None

    dataset_path = os.path.join(
        UPLOAD_FOLDER,
        "solar_dataset.csv"
    )

    prepared_path = os.path.join(
        UPLOAD_FOLDER,
        "prepared_solar_dataset.csv"
    )

    if os.path.exists(dataset_path):

        try:

            df = pd.read_csv(dataset_path)

            required_columns = [
                "Timestamp",
                "Hour",
                "Day",
                "Month",
                "DayOfWeek",
                "Temperature",
                "Irradiance_G",
                "Irradiance_A",
                "Cloud",
                "Power"
            ]

            numeric_columns = [
                "Hour",
                "Day",
                "Month",
                "DayOfWeek",
                "Temperature",
                "Irradiance_G",
                "Irradiance_A",
                "Cloud",
                "Power"
            ]

            missing_columns = [
                col for col in required_columns
                if col not in df.columns
            ]

            timestamp_valid = False

            if "Timestamp" in df.columns:

                timestamps = pd.to_datetime(
                    df["Timestamp"],
                    errors="coerce"
                )

                timestamp_valid = not timestamps.isna().any()

            numeric_valid = True

            for col in numeric_columns:

                if col in df.columns:

                    converted = pd.to_numeric(
                        df[col],
                        errors="coerce"
                    )

                    if converted.isna().any():
                        numeric_valid = False

                else:
                    numeric_valid = False

            missing_values = int(df.isnull().sum().sum())
            duplicates = int(df.duplicated().sum())

            validation_passed = (
                len(missing_columns) == 0
                and missing_values == 0
                and duplicates == 0
                and timestamp_valid
                and numeric_valid
            )

            if validation_passed:
                quality = "Excellent"
                validation_status = "PASSED"
            else:
                quality = "Needs Review"
                validation_status = "FAILED"

            dataset_info = {
                "filename": "solar_dataset.csv",
                "records": len(df),
                "columns": len(df.columns),
                "missing": missing_values,
                "duplicates": duplicates,
                "quality": quality
            }

            validation = {
                "required_columns": len(missing_columns) == 0,
                "missing_values": missing_values == 0,
                "duplicates": duplicates == 0,
                "timestamp": timestamp_valid,
                "numeric": numeric_valid,
                "passed": validation_passed,
                "status": validation_status,
                "errors": missing_columns
            }

            preview = df.head(10).to_dict(
                orient="records"
            )

        except Exception as e:

            validation = {
                "passed": False,
                "status": "FAILED",
                "errors": [str(e)]
            }

    if os.path.exists(prepared_path):

        try:

            prepared_df = pd.read_csv(prepared_path)

            preparation = {
                "ready": True,
                "records": len(prepared_df),
                "features": 8,
                "target": "Power",
                "status": "READY"
            }

        except Exception:

            preparation = None

    return render_template(
        "data.html",
        dataset={
            "error": None if validation and validation.get("passed") else (validation.get("errors", []) if validation else []),
            "rows": dataset_info["records"] if dataset_info else 0,
            "columns": dataset_info["columns"] if dataset_info else 0,
            "missing": dataset_info["missing"] if dataset_info else 0,
            "duplicates": dataset_info["duplicates"] if dataset_info else 0,
            "quality": dataset_info["quality"] if dataset_info else "Needs Review",
            "validation_passed": validation["passed"] if validation else False,
            "validation_status": validation["status"] if validation else "FAILED",
            "missing_columns": not validation["required_columns"] if validation else True,
            "timestamp_valid": validation["timestamp"] if validation else False,
            "numeric_valid": validation["numeric"] if validation else False,
            "prepared_records": preparation["records"] if preparation else 0,
            "feature_count": preparation["features"] if preparation else 0,
            "target_column": preparation["target"] if preparation else "Power"
        },
        validation=validation,
        preview=preview,
        preparation=preparation
    )


# =========================================================
# UPLOAD DATASET
# =========================================================

@app.route("/upload-dataset", methods=["POST"])
def upload_dataset():

    if "user_id" not in session:
        return redirect("/admin-login")

    if session.get("role") != "admin":
        return redirect("/")

    file = request.files.get("dataset")

    print("UPLOAD DEBUG - FILE:", file)
    print("UPLOAD DEBUG - FILENAME:", file.filename if file else "NONE")

    if not file:
        return redirect("/data")

    if file.filename == "":
        return redirect("/data")

    file_path = os.path.join(
        UPLOAD_FOLDER,
        "solar_dataset.csv"
    )

    file.save(file_path)

    return redirect("/data")


# =========================================================
# PREPARE DATASET
# =========================================================

@app.route("/prepare-dataset", methods=["POST"])
def prepare_dataset():

    if "user_id" not in session:
        return redirect("/admin-login")

    if session.get("role") != "admin":
        return redirect("/")

    source_path = os.path.join(
        UPLOAD_FOLDER,
        "solar_dataset.csv"
    )

    output_path = os.path.join(
        UPLOAD_FOLDER,
        "prepared_solar_dataset.csv"
    )

    if not os.path.exists(source_path):
        return redirect("/data")

    df = pd.read_csv(source_path)

    required_columns = [
        "Timestamp",
        "Hour",
        "Day",
        "Month",
        "DayOfWeek",
        "Temperature",
        "Irradiance_G",
        "Irradiance_A",
        "Cloud",
        "Power"
    ]

    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"],
        errors="coerce"
    )

    for col in required_columns[1:]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.dropna(
        subset=required_columns
    )

    features = [
        "Hour",
        "Day",
        "Month",
        "DayOfWeek",
        "Temperature",
        "Irradiance_G",
        "Irradiance_A",
        "Cloud"
    ]

    target = "Power"

    prepared_df = df[
        features + [target]
    ]

    prepared_df.to_csv(
        output_path,
        index=False
    )

    return redirect("/data")


# =========================================================
# USER MANAGEMENT
# =========================================================

@app.route("/users")
def users():

    if "user_id" not in session:
        return redirect("/admin-login")

    if session.get("role") != "admin":
        return redirect("/")

    connection = get_db_connection()

    users_list = connection.execute("""
        SELECT id, username, full_name, email, role
        FROM users
        ORDER BY id
    """).fetchall()

    connection.close()

    return render_template(
        "users.html",
        users=users_list
    )


# =========================================================
# ADD NORMAL USER
# =========================================================

@app.route("/add-user", methods=["POST"])
def add_user():

    if "user_id" not in session:
        return redirect("/admin-login")

    if session.get("role") != "admin":
        return redirect("/")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()

    # Admin can ONLY create normal users
    role = "user"

    if len(password) < 8:
        return redirect("/users")

    connection = get_db_connection()

    try:

        connection.execute("""
            INSERT INTO users
            (username, password, full_name, email, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            username,
            hash_password(password),
            full_name,
            email,
            role
        ))

        connection.commit()

    except sqlite3.IntegrityError:
        pass

    connection.close()

    return redirect("/users")


# =========================================================
# ADD SECOND ADMIN
# =========================================================

@app.route("/add-admin", methods=["POST"])
def add_admin():

    if "user_id" not in session:
        return redirect("/admin-login")

    if session.get("role") != "admin":
        return redirect("/")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()

    connection = get_db_connection()

    admin_count = connection.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin'"
    ).fetchone()[0]

    if admin_count >= 2:
        connection.close()
        return redirect("/users")

    if len(password) < 8:
        connection.close()
        return redirect("/users")

    if not any(c.isupper() for c in password):
        connection.close()
        return redirect("/users")

    if not any(c.islower() for c in password):
        connection.close()
        return redirect("/users")

    if not any(c.isdigit() for c in password):
        connection.close()
        return redirect("/users")

    if not any(not c.isalnum() for c in password):
        connection.close()
        return redirect("/users")

    try:
        connection.execute(
            """
            INSERT INTO users
            (username, password, full_name, email, role)
            VALUES (?, ?, ?, ?, 'admin')
            """,
            (
                username,
                hash_password(password),
                full_name,
                email
            )
        )

        connection.commit()

    except sqlite3.IntegrityError:
        pass

    connection.close()

    return redirect("/users")


# =========================================================
# DELETE NORMAL USER
# =========================================================

@app.route("/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):

    if "user_id" not in session:
        return redirect("/admin-login")

    if session.get("role") != "admin":
        return redirect("/")

    connection = get_db_connection()

    user = connection.execute("""
        SELECT role
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    if user and user["role"] == "user":

        connection.execute("""
            DELETE FROM users
            WHERE id = ?
            AND role = 'user'
        """, (user_id,))

        connection.commit()

    connection.close()

    return redirect("/users")


# =========================================================
# FORECASTING
# =========================================================

@app.route("/forecast")
def forecast():

    if "user_id" not in session:
        return redirect("/")

    return render_template(
        "forecast.html"
    )


# =========================================================
# PREDICTION
# =========================================================

@app.route("/predict", methods=["POST"])
def predict():

    if "user_id" not in session:
        return redirect("/")

    model_path = os.path.join(
        MODEL_FOLDER,
        "solar_power_model.pkl"
    )

    if not os.path.exists(model_path):

        return render_template(
            "forecast.html",
            error="Forecasting model not found. Please train the model first."
        )

    try:

        hour = float(request.form.get("hour"))
        day = float(request.form.get("day"))
        month = float(request.form.get("month"))
        dayofweek = float(request.form.get("dayofweek"))
        temperature = float(request.form.get("temperature"))
        irradiance_g = float(request.form.get("irradiance_g"))
        irradiance_a = float(request.form.get("irradiance_a"))
        cloud = float(request.form.get("cloud"))

        if not 0 <= hour <= 23:
            return render_template(
                "forecast.html",
                error="Hour must be between 0 and 23."
            )

        if not 1 <= day <= 31:
            return render_template(
                "forecast.html",
                error="Day must be between 1 and 31."
            )

        if not 1 <= month <= 12:
            return render_template(
                "forecast.html",
                error="Month must be between 1 and 12."
            )

        if not 0 <= dayofweek <= 6:
            return render_template(
                "forecast.html",
                error="Day of Week must be between 0 and 6."
            )

        if irradiance_g < 0:
            return render_template(
                "forecast.html",
                error="Global Irradiance cannot be negative."
            )

        if irradiance_a < 0:
            return render_template(
                "forecast.html",
                error="Ambient Irradiance cannot be negative."
            )

        if not 0 <= cloud <= 100:
            return render_template(
                "forecast.html",
                error="Cloud percentage must be between 0 and 100."
            )

        features = [
            hour,
            day,
            month,
            dayofweek,
            temperature,
            irradiance_g,
            irradiance_a,
            cloud
        ]

        model = joblib.load(model_path)

        feature_names = [
            "Hour",
            "Day",
            "Month",
            "DayOfWeek",
            "Temperature",
            "Irradiance_G",
            "Irradiance_A",
            "Cloud"
        ]

        input_data = pd.DataFrame(
            [features],
            columns=feature_names
        )

        prediction = model.predict(
            input_data
        )[0]

        prediction = round(
            float(prediction),
            2
        )

        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO predictions
            (user_id, prediction)
            VALUES (?, ?)
            """,
            (
                session.get("user_id"),
                prediction
            )
        )

        connection.commit()
        connection.close()

        return render_template(
            "forecast.html",
            prediction=prediction
        )

    except Exception as e:

        return render_template(
            "forecast.html",
            error=f"Prediction error: {e}"
        )


# =========================================================
# USER PROFILE
# =========================================================

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/")

    connection = get_db_connection()

    user = connection.execute(
        """
        SELECT username, full_name, email, role
        FROM users
        WHERE id = ?
        """,
        (session.get("user_id"),)
    ).fetchone()

    connection.close()

    if not user:
        return redirect("/")

    return render_template(
        "profile.html",
        user=user
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    create_database()

    app.run(
        host="0.0.0.0",
        port=5050,
        debug=True
    )
