# import streamlit as st
# import pandas as pd
# import joblib

# # Load models
# model_fat = joblib.load('fat_model.pkl')
# model_water = joblib.load('water_model.pkl')

# # Load exercise intensity data
# exercise_df = pd.read_csv('exercise_intensity_new.csv')
# exercise_intensity = exercise_df.set_index('Name of Exercise')['Average Calories Per Rep'].to_dict()


# def ideal_fat_percentage(age, gender):
#     gender = gender.lower()
#     if gender == "male":
#         if age <= 25: return 15
#         elif age <= 35: return 16
#         elif age <= 45: return 17
#         elif age <= 55: return 18
#         elif age <= 65: return 19
#         else: return 20
#     else:
#         if age <= 25: return 22
#         elif age <= 35: return 24
#         elif age <= 45: return 25
#         elif age <= 55: return 27
#         elif age <= 65: return 28
#         else: return 30

# st.title("🏋️‍♂️ Fitness Recommender: Fat% & Water Intake")

# # User input
# age = st.number_input("Age", 18, 70)
# gender = st.selectbox("Gender", ["Male", "Female"])
# weight = st.number_input("Weight (kg)")
# height = st.number_input("Height (m)")
# session_duration = st.slider("Session Duration (hours)", 0.5, 3.0, 1.0)
# frequency = st.slider("Workout Frequency (days/week)", 1, 7, 4)

# st.subheader("Select your exercises:")
# selected_exercises = st.multiselect("Exercises", list(exercise_intensity.keys()))

# user_exercises = {}
# for ex in selected_exercises:
#     reps = st.number_input(f"{ex} Reps", 1, 100, 20)
#     sets = st.number_input(f"{ex} Sets", 1, 10, 3)
#     user_exercises[ex] = {'Reps': reps, 'Sets': sets}

# if st.button("Predict Fitness Metrics"):
#     # Compute BMI
#     bmi = weight / (height ** 2)

#     # Compute total weighted reps
#     total_reps = sum(
#         d['Reps'] * d['Sets'] * (exercise_intensity.get(ex, 100)/100)
#         for ex, d in user_exercises.items()
#     )

#     # Prepare dataframe
#     user_df = pd.DataFrame([{
#         'Age': age,
#         'Gender': gender,
#         'Weight (kg)': weight,
#         'Height (m)': height,
#         'BMI': bmi,
#         'Session_Duration (hours)': session_duration,
#         'Workout_Frequency (days/week)': frequency,
#         'Total_Reps': total_reps
#     }])

#     # Predictions
#     fat_pred = model_fat.predict(user_df)[0]
#     water_pred = model_water.predict(user_df)[0]
#     ideal_fat = ideal_fat_percentage(age, gender)

#     st.write(f"**Predicted Fat%:** {fat_pred:.2f}")
#     st.write(f"**Ideal Fat%:** {ideal_fat:.2f}")
#     st.write(f"**Predicted Water Intake:** {water_pred:.2f} L/day")

#     slope=-0.00185
#     # # Recommendations
#     # if fat_pred > ideal_fat:
#     #     diff = fat_pred - ideal_fat
#     #     inc_reps = int(diff * 2)
#     #     st.warning(f"Increase total reps by about {inc_reps} per session to reach your ideal fat%")
#     # else:
#     #     st.success("✅ Your fat percentage is already in the ideal range! Maintain your current routine.")

#     # st.info(f"Recommended Water Intake: {water_pred:.2f} L/day")
# def calculate_rep_increase(fat_pred, ideal_fat, slope,user_exercises, user_reps, exercise_intensity):
#     """
#     Predicts total and per-exercise rep increase based on fat difference.
#     Uses regression slope (data-based) and exercise intensity (adjusted kcal/rep).
#     """
#     # Safety check for invalid slope
#     if slope >= 0:
#         slope = -0.01

#     # Fat difference to reduce
#     fat_diff = fat_pred - ideal_fat
#     if fat_diff <= 0:
#         return 0, {ex: 0 for ex in user_exercises}

#     # Total rep increase (scientific)
#     total_rep_increase = fat_diff / abs(slope)

#     # Weighted distribution based on current reps * intensity
#     weighted = [exercise_intensity.get(ex, 1) * r for ex, r in zip(user_exercises, user_reps)]
#     total_weight = sum(weighted)

#     rep_increase_each = {
#         ex: int((exercise_intensity.get(ex, 1) * r / total_weight) * total_rep_increase)
#         for ex, r in zip(user_exercises, user_reps)
#     }

#     return int(total_rep_increase), rep_increase_each

#     # --- FAT % RECOMMENDATION SECTION ---
# total_inc, rep_increase_each = calculate_rep_increase(
#     fat_pred=fat_pred,
#     ideal_fat=ideal_fat,
#     slope=slope,
#     user_exercises=user_exercises,
#     user_reps=user_reps,
#     exercise_intensity=exercise_intensity  # your adjusted kcal/rep dict
# )

# if total_inc == 0:
#     st.success("✅ Your fat percentage is already in the ideal range! Maintain your current routine.")
# else:
#     st.warning(f"⚡ You need to increase your total workout volume by approx. {total_inc} reps per session to reach your ideal fat%.")
#     st.subheader("Suggested Reps Increase per Exercise:")
#     for ex, inc in rep_increase_each.items():
#         st.write(f"🔹 {ex}: +{inc} reps per session")



import streamlit as st
import pandas as pd
import joblib

# Load models
model_fat = joblib.load('fat_model.pkl')
model_water = joblib.load('water_model.pkl')

# Load exercise intensity data
exercise_df = pd.read_csv('exercise_intensity_new.csv')
exercise_intensity = exercise_df.set_index('Name of Exercise')['Average Calories Per Rep'].to_dict()

# --- Helper Functions ---

def ideal_fat_percentage(age, gender):
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


def calculate_rep_increase(fat_pred, ideal_fat, slope, user_exercises, exercise_intensity):
    """
    Predicts total and per-exercise rep increase based on fat difference.
    Uses regression slope (data-based) and exercise intensity (adjusted kcal/rep).
    """
    # Safety check for invalid slope
    if slope >= 0:
        slope = -0.01

    # Fat difference to reduce
    fat_diff = fat_pred - ideal_fat
    if fat_diff <= 0:
        return 0, {ex: 0 for ex in user_exercises}

    # Total rep increase (scientific)
    total_rep_increase = fat_diff / abs(slope)

    # Weighted distribution based on current reps * intensity
    weighted = [exercise_intensity.get(ex, 1) * vals['Reps'] for ex, vals in user_exercises.items()]
    total_weight = sum(weighted)

    rep_increase_each = {
        ex: int((exercise_intensity.get(ex, 1) * vals['Reps'] / total_weight) * total_rep_increase)
        for ex, vals in user_exercises.items()
    }

    # Clamp the total increase to a reasonable maximum
    total_rep_increase = min(total_rep_increase, 600)
    return int(total_rep_increase), rep_increase_each


# --- Streamlit UI ---

st.title("🏋️‍♂️ Fitness Recommender: Fat% & Water Intake")

# User input
age = st.number_input("Age", 18, 70)
gender = st.selectbox("Gender", ["Male", "Female"])
weight = st.number_input("Weight (kg)")
height = st.number_input("Height (m)")
session_duration = st.slider("Session Duration (hours)", 0.5, 3.0, 1.0)
frequency = st.slider("Workout Frequency (days/week)", 1, 7, 4)

st.subheader("Select your exercises:")
selected_exercises = st.multiselect("Exercises", list(exercise_intensity.keys()))

user_exercises = {}
for ex in selected_exercises:
    reps = st.number_input(f"{ex} Reps", 1, 100, 20)
    sets = st.number_input(f"{ex} Sets", 1, 10, 3)
    user_exercises[ex] = {'Reps': reps, 'Sets': sets}

# Button: Predict
if st.button("Predict Fitness Metrics"):

    # Compute BMI
    bmi = weight / (height ** 2)

    # Compute total weighted reps (intensity × reps × sets)
    total_reps = sum(
        vals['Reps'] * vals['Sets'] * (exercise_intensity.get(ex, 100) / 100)
        for ex, vals in user_exercises.items()
    )

    # Prepare DataFrame for model input
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

    def build_model_input(model, features_dict):
        df = pd.DataFrame([features_dict])
        # One-hot encode Gender if model was trained with dummies
        if 'Gender' in df.columns:
            df = pd.get_dummies(df, columns=['Gender'], prefix='Gender')
        # Align to model's expected features if available
        expected_cols = getattr(model, 'feature_names_in_', None)
        if expected_cols is not None:
            # Add any missing columns with 0, drop extras, and order correctly
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = 0
            df = df.reindex(columns=expected_cols)
        return df

    user_df_fat = build_model_input(model_fat, base_features)
    user_df_water = build_model_input(model_water, base_features)

    # Predictions
    fat_pred = model_fat.predict(user_df_fat)[0]
    water_pred = model_water.predict(user_df_water)[0]
    ideal_fat = ideal_fat_percentage(age, gender)

    # Display results
    st.write(f"**Predicted Fat%:** {fat_pred:.2f}")
    st.write(f"**Ideal Fat%:** {ideal_fat:.2f}")
    st.write(f"**Predicted Water Intake:** {water_pred:.2f} L/day")

   # Use your dataset correlation as base slope
    true_slope = -0.00185

# Apply scaling factor so outputs become human-scale
# (This basically compresses unrealistic thousands of reps into few hundreds)
    scaling_factor = 15  # tweak between 10–20

    slope = true_slope * scaling_factor  # ≈ -0.028


    # --- Recommendations ---

    total_inc, rep_increase_each = calculate_rep_increase(
        fat_pred=fat_pred,
        ideal_fat=ideal_fat,
        slope=slope,
        user_exercises=user_exercises,
        exercise_intensity=exercise_intensity
    )

    if total_inc == 0:
        st.success("✅ Your fat percentage is already in the ideal range! Maintain your current routine.")
    else:
        st.warning(f"⚡ You need to increase your total workout volume by approx. {total_inc} reps per session to reach your ideal fat%.")
        st.subheader("Suggested Reps Increase per Exercise:")
        for ex, inc in rep_increase_each.items():
            st.write(f"🔹 {ex}: +{inc} reps per session")

    # Water recommendation
    st.info(f"💧 Recommended Daily Water Intake: {water_pred:.2f} L")
