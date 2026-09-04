import os
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# =========================================================
# FILE PATH
# =========================================================

DATASET = "uploads/prepared_solar_dataset.csv"


# =========================================================
# CHECK DATASET
# =========================================================

if not os.path.exists(DATASET):

    print("")
    print("ERROR: Prepared dataset not found.")
    print("Please upload and prepare the dataset first.")
    print("")

    raise SystemExit


# =========================================================
# LOAD DATA
# =========================================================

data = pd.read_csv(DATASET)

print("")
print("======================================")
print("       SOLARVISION MODEL TRAINING")
print("======================================")
print("")

print("Dataset loaded successfully.")
print("Records:", len(data))
print("Columns:", len(data.columns))
print("")


# =========================================================
# FEATURES AND TARGET
# =========================================================

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


X = data[features]

y = data[target]


# =========================================================
# TRAIN / TEST SPLIT
# =========================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)


print("Training records:", len(X_train))
print("Testing records:", len(X_test))
print("")


# =========================================================
# RANDOM FOREST MODEL
# =========================================================

model = RandomForestRegressor(
    n_estimators=200,
    random_state=42,
    n_jobs=-1
)


print("Training Random Forest model...")
print("")


model.fit(
    X_train,
    y_train
)


print("Model training completed.")
print("")


# =========================================================
# PREDICTIONS
# =========================================================

predictions = model.predict(X_test)


# =========================================================
# PERFORMANCE
# =========================================================

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = mean_squared_error(
    y_test,
    predictions
) ** 0.5

r2 = r2_score(
    y_test,
    predictions
)


# =========================================================
# RESULTS
# =========================================================

print("======================================")
print("       MODEL PERFORMANCE")
print("======================================")
print("")

print(f"MAE  : {mae:.4f}")
print(f"RMSE : {rmse:.4f}")
print(f"R²   : {r2:.4f}")

# Save performance metrics for the Admin Dashboard
import json

metrics = {
    "mae": round(float(mae), 4),
    "rmse": round(float(rmse), 4),
    "r2": round(float(r2), 4),
    "records": len(data),
    "training_records": len(X_train),
    "testing_records": len(X_test),
    "trees": 200
}

with open("models/model_metrics.json", "w") as f:
    json.dump(metrics, f, indent=4)

print("Performance metrics saved.")

print("")

print("======================================")
print("       MODEL READY")
print("======================================")
print("")


# =========================================================
# SAVE MODEL
# =========================================================

import joblib

MODEL_FOLDER = "models"

os.makedirs(
    MODEL_FOLDER,
    exist_ok=True
)

MODEL_PATH = os.path.join(
    MODEL_FOLDER,
    "solar_power_model.pkl"
)

joblib.dump(
    model,
    MODEL_PATH
)

print("Model saved to:")
print(MODEL_PATH)

print("")
