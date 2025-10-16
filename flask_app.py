from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import pandas as pd
import joblib
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')

# Load models and data once at startup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FAT_PATH = os.path.join(BASE_DIR, 'fat_model.pkl')
MODEL_WATER_PATH = os.path.join(BASE_DIR, 'water_model.pkl')
EXERCISE_CSV_PATH = os.path.join(BASE_DIR, 'exercise_intensity_new.csv')

model_fat = joblib.load(MODEL_FAT_PATH)
model_water = joblib.load(MODEL_WATER_PATH)
exercise_df = pd.read_csv(EXERCISE_CSV_PATH)
exercise_intensity = exercise_df.set_index('Name of Exercise')['Average Calories Per Rep'].to_dict()

DB_PATH = os.path.join(BASE_DIR, 'app.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            age INTEGER,
            gender TEXT,
            weight REAL,
            height REAL,
            session_duration REAL,
            frequency INTEGER,
            exercises_json TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()

init_db()


def ideal_fat_percentage(age: int, gender: str) -> int:
    gender = gender.lower()
    if gender == "male":
        if age <= 25: return 15
        elif age <= 35: return 16
        elif age <= 45: return 17
        elif age <= 55: return 18
        elif age <= 65: return 19
        else: return 20
    else:
        if age <= 25: return 22
        elif age <= 35: return 24
        elif age <= 45: return 25
        elif age <= 55: return 27
        elif age <= 65: return 28
        else: return 30


def build_model_input(model, features_dict: dict) -> pd.DataFrame:
    df = pd.DataFrame([features_dict])
    if 'Gender' in df.columns:
        df = pd.get_dummies(df, columns=['Gender'], prefix='Gender')
    expected_cols = getattr(model, 'feature_names_in_', None)
    if expected_cols is not None:
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0
        df = df.reindex(columns=expected_cols)
    return df


def calculate_rep_increase(fat_pred: float, ideal_fat: float, slope: float, user_exercises: dict, exercise_intensity_map: dict):
    if slope >= 0:
        slope = -0.01
    fat_diff = fat_pred - ideal_fat
    if fat_diff <= 0:
        return 0, {ex: 0 for ex in user_exercises}
    total_rep_increase = fat_diff / abs(slope)
    weighted = [exercise_intensity_map.get(ex, 1) * vals.get('Reps', 0) for ex, vals in user_exercises.items()]
    total_weight = sum(weighted) or 1
    rep_increase_each = {
        ex: int((exercise_intensity_map.get(ex, 1) * vals.get('Reps', 0) / total_weight) * total_rep_increase)
        for ex, vals in user_exercises.items()
    }
    total_rep_increase = min(total_rep_increase, 600)
    return int(total_rep_increase), rep_increase_each


@app.get('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    conn = get_db()
    user = conn.execute('SELECT id, email, name FROM users WHERE id=?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)


@app.get('/dashboard')
def dashboard():
    user = None
    if 'user_id' in session:
        conn = get_db()
        user = conn.execute('SELECT id, email, name FROM users WHERE id=?', (session['user_id'],)).fetchone()
        conn.close()
    return render_template('dashboard.html', exercises=list(exercise_intensity.keys()), user=user)


@app.post('/predict')
def predict():
    data = request.get_json(force=True) or {}
    try:
        age = int(data.get('age'))
        gender = str(data.get('gender'))
        weight = float(data.get('weight'))
        height = float(data.get('height'))
        session_duration = float(data.get('session_duration'))
        frequency = int(data.get('frequency'))
        user_exercises = data.get('exercises', {})  # { name: {Reps, Sets} }

        bmi = weight / (height ** 2)
        total_reps = sum(
            (vals.get('Reps', 0) * vals.get('Sets', 0) * (exercise_intensity.get(ex, 100) / 100))
            for ex, vals in user_exercises.items()
        )

        base_features = {
            'Age': age,
            'Gender': gender,
            'Weight (kg)': weight,
            'Height (m)': height,
            'BMI': bmi,
            'Session_Duration (hours)': session_duration,
            'Workout_Frequency (days/week)': frequency,
            'Total_Reps': total_reps
        }

        user_df_fat = build_model_input(model_fat, base_features)
        user_df_water = build_model_input(model_water, base_features)

        fat_pred = float(model_fat.predict(user_df_fat)[0])
        water_pred = float(model_water.predict(user_df_water)[0])
        ideal_fat = float(ideal_fat_percentage(age, gender))

        true_slope = -0.00185
        scaling_factor = 15
        slope = true_slope * scaling_factor

        total_inc, rep_increase_each = calculate_rep_increase(
            fat_pred=fat_pred,
            ideal_fat=ideal_fat,
            slope=slope,
            user_exercises=user_exercises,
            exercise_intensity_map=exercise_intensity,
        )

        return jsonify({
            'fat_pred': round(fat_pred, 2),
            'water_pred': round(water_pred, 2),
            'ideal_fat': round(ideal_fat, 2),
            'total_rep_increase': int(total_inc),
            'rep_increase_each': rep_increase_each,
        })
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.get('/exercises')
def list_exercises():
    return jsonify(sorted(list(exercise_intensity.keys())))


# -------- Auth --------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    data = request.form
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    name = data.get('name') or ''
    if not email or not password:
        return render_template('signup.html', error='Email and password are required.')
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO users(email, password_hash, name) VALUES (?, ?, ?)', (
            email, generate_password_hash(password), name
        ))
        conn.commit()
        user_id = cur.lastrowid
        session['user_id'] = user_id
        return redirect(url_for('index'))
    except sqlite3.IntegrityError:
        return render_template('signup.html', error='Email already registered.')
    finally:
        conn.close()


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'GET':
        return render_template('signin.html')
    data = request.form
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    conn.close()
    if not user or not check_password_hash(user['password_hash'], password):
        return render_template('signin.html', error='Invalid credentials.')
    session['user_id'] = user['id']
    return redirect(url_for('dashboard'))


@app.post('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


# -------- Profile APIs --------
@app.get('/api/profile')
def get_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    conn = get_db()
    prof = conn.execute('SELECT age, gender, weight, height, session_duration, frequency, exercises_json FROM profiles WHERE user_id=?', (session['user_id'],)).fetchone()
    conn.close()
    if not prof:
        return jsonify({}), 200
    data = dict(prof)
    return jsonify(data)


@app.post('/api/profile')
def save_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json(force=True) or {}
    age = data.get('age')
    gender = data.get('gender')
    weight = data.get('weight')
    height = data.get('height')
    session_duration = data.get('session_duration')
    frequency = data.get('frequency')
    exercises_json = data.get('exercises_json')  # stringified JSON from client
    conn = get_db()
    conn.execute(
        'REPLACE INTO profiles(user_id, age, gender, weight, height, session_duration, frequency, exercises_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (session['user_id'], age, gender, weight, height, session_duration, frequency, exercises_json)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


