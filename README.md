# ☀️ SolarVision — Solar Power Forecasting System

SolarVision is a machine learning-based web application that predicts solar power generation using environmental and time-related input features. It provides user authentication, solar power forecasting, prediction history, and an administration dashboard.

## 🚀 Project Features

- User registration and login
- Admin login and user management
- Machine learning-based solar power prediction
- Prediction history and dashboard analytics
- Dataset management
- Model performance metrics
- User profile management
- Input validation
- Responsive web interface

## 🛠️ Technologies Used

- **Python** — application logic and machine learning
- **Flask** — web application framework
- **Pandas** — dataset processing
- **Scikit-learn** — Random Forest regression model
- **SQLite** — user and prediction data storage
- **HTML and CSS** — user interface
- **Joblib** — saving and loading the trained model
- **Git and GitHub** — version control and source code hosting
- **Render** — web application deployment

## 📁 Project Structure

```text
Solar_Forecasting_Project/
├── app.py
├── train_model.py
├── requirements.txt
├── README.md
├── models/
│   ├── solar_power_model.pkl
│   └── model_metrics.json
├── templates/
│   ├── login.html
│   ├── register.html
│   ├── admin_login.html
│   ├── admin.html
│   ├── user.html
│   ├── forecast.html
│   ├── data.html
│   ├── users.html
│   └── profile.html
└── uploads/
    ├── solar_dataset.csv
    └── prepared_solar_dataset.csv
```

## 🤖 Machine Learning Model

SolarVision uses a **Random Forest Regressor** to estimate solar power generation.

- **Dataset size:** 1,200 records
- **Input features:** 8
- **Target variable:** Power
- **Training/testing split:** 80% training and 20% testing
- **Number of trees:** 200
- **Random state:** 42

### Model Evaluation

| Metric | Result |
|---|---:|
| Mean Absolute Error (MAE) | 6.0674 |
| Root Mean Squared Error (RMSE) | 14.8933 |
| R² Score | 0.9858 |

The model achieved an R² score of approximately **98.58%** on the evaluation dataset. This is an R² score, not a guarantee of 98.58% prediction accuracy on all future data.

## ⚙️ Run the Project Locally

### 1. Clone the repository

```bash
git clone https://github.com/Rachamani-vasu/Solar_Forecasting_Project.git
cd Solar_Forecasting_Project
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Start the Flask application

```bash
python app.py
```

Open the local URL shown in the terminal. If the application is configured to use port 5050, visit:

http://127.0.0.1:5050

## 📊 Dataset Features

The model uses these eight input features:

1. Hour
2. Day
3. Month
4. Day of Week
5. Temperature
6. Global Irradiance
7. Atmospheric Irradiance
8. Cloud

The target variable is **Power**, representing the value the model learns to predict from the dataset.

## 🌐 Deployment

The project is deployed on Render:

https://solar-forecasting-project.onrender.com

Source code is maintained in GitHub:

https://github.com/Rachamani-vasu/Solar_Forecasting_Project

## 🔒 Security Note

Do not commit passwords, secret keys, private credentials, or a database containing real user information. Configure production secrets through environment variables before using the application with real users.

## 👨‍💻 Project Purpose

This project demonstrates how machine learning can be integrated into a Flask web application to forecast solar power generation and present predictions through a user-friendly dashboard.
