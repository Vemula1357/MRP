from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import joblib
import google.generativeai as genai

app = Flask(__name__)
GEMINI_API_KEY = "AIzaSyC50LcX6xZPO1k__ZRwAOr0CSrGPwDrfnM"
genai.configure(api_key=GEMINI_API_KEY)

def query_gemini(prompt):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(prompt)
        return response.text.strip() if hasattr(response, 'text') else "No response from Gemini"
    except Exception as e:
        return f"Gemini API Error: {str(e)}"
  
data_file = "patient_data.xlsx"

model = joblib.load("disease_prediction_model.pkl")
label_encoder_symptom = joblib.load("label_encoder_symptom.pkl")
label_encoder_medication = joblib.load("label_encoder_medication.pkl")
label_encoder_diagnosis = joblib.load("label_encoder_diagnosis.pkl")

patients = pd.read_excel(data_file, sheet_name="Patients", dtype={"Patient ID": str})
symptoms = pd.read_excel(data_file, sheet_name="Symptoms", dtype={"Patient ID": str})
diagnoses = pd.read_excel(data_file, sheet_name="Diagnoses", dtype={"Patient ID": str})
treatments = pd.read_excel(data_file, sheet_name="Treatments", dtype={"Patient ID": str})

dataframes = {"Patients": patients, "Symptoms": symptoms, "Diagnoses": diagnoses, "Treatments": treatments}

@app.route('/get_tables', methods=['GET'])
def get_tables():
    return jsonify({"tables": list(dataframes.keys())})

@app.route('/get_columns', methods=['POST'])
def get_columns():
    table = request.json.get("table")
    if table in dataframes:
        return jsonify({"columns": dataframes[table].columns.tolist()})
    return jsonify({"error": "Invalid table"}), 400

@app.route('/get_summary', methods=['POST'])
def get_summary():
    table = request.json.get("table")
    column = request.json.get("column")

    if table in dataframes and column in dataframes[table].columns:
        col_data = dataframes[table][column]
        
        if col_data.dtype in ['int64', 'float64']:  # Numeric
            summary = col_data.describe().to_frame().reset_index().values.tolist()
            summary.insert(0, ["Type", "Numeric"])
        else:  # Categorical
            summary = [
                ["Type", "Categorical"],
                ["Unique Values", col_data.nunique()],
                ["Top 5 Values", "<br>".join(col_data.value_counts().head(5).to_string().split("\n"))]
            ]
        return jsonify({"summary": summary})
    
    return jsonify({"error": "Invalid table or column"}), 400
    
@app.route('/plot_univariate', methods=['POST'])
def plot_univariate():
    table, column = request.json.get("table"), request.json.get("column")
    top_n = int(request.json.get("top_n", 10))
    
    if table in dataframes and column in dataframes[table].columns:
        plt.figure(figsize=(8, 4))
        col_data = dataframes[table][column]
        
        if col_data.dtype in ['int64', 'float64']:
            sns.histplot(col_data, kde=True, bins=top_n)
        else:
            top_values = col_data.value_counts().head(top_n)
            sns.barplot(x=top_values.values, y=top_values.index)
        
        plt.title(f"Univariate Analysis: {column} (Top {top_n})")
        plt.tight_layout()
        plt.savefig("static/univariate.png")
        plt.close()
        return jsonify({"image": "static/univariate.png"})
    
    return jsonify({"error": "Invalid table or column"}), 400

@app.route('/plot_bivariate', methods=['POST'])
def plot_bivariate():
    table, column_x, column_y = request.json.get("table"), request.json.get("column_x"), request.json.get("column_y")
    top_n = int(request.json.get("top_n", 10))
    
    if table in dataframes and column_x in dataframes[table].columns and column_y in dataframes[table].columns:
        plt.figure(figsize=(8, 4))
        col_x_data, col_y_data = dataframes[table][column_x], dataframes[table][column_y]
        
        if col_x_data.dtype in ['int64', 'float64'] and col_y_data.dtype in ['int64', 'float64']:
            sns.scatterplot(x=col_x_data, y=col_y_data)
        elif col_x_data.dtype == 'object' and col_y_data.dtype in ['int64', 'float64']:
            top_values = col_x_data.value_counts().head(top_n).index
            filtered_data = dataframes[table][dataframes[table][column_x].isin(top_values)]
            sns.boxplot(x=filtered_data[column_x], y=filtered_data[column_y])
            plt.xticks(rotation=45)
        else:
            top_values = col_x_data.value_counts().head(top_n).index
            filtered_data = dataframes[table][dataframes[table][column_x].isin(top_values)]
            sns.countplot(x=filtered_data[column_x], hue=filtered_data[column_y])
            plt.xticks(rotation=45)
        
        plt.title(f"Bivariate Analysis: {column_x} vs {column_y} (Top {top_n})")
        plt.tight_layout()
        plt.savefig("static/bivariate.png")
        plt.close()
        return jsonify({"image": "static/bivariate.png"})
    
    return jsonify({"error": "Invalid table or columns"}), 400
    
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():    
    return render_template('dashboard.html')

@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    if request.method == 'POST':
        symptom = request.form.get('symptom')
        
        try:
            encoded_symptom = label_encoder_symptom.transform([symptom])[0]
        except ValueError:
            encoded_symptom = None
        
        if encoded_symptom is None:
            predicted_disease = query_gemini(f"A patient has symptom '{symptom}'. Provide the most likely diagnosis in 5 words or less.")
        else:
            prediction_encoded = model.predict([[encoded_symptom]])[0]
            predicted_disease = label_encoder_diagnosis.inverse_transform([prediction_encoded])[0]
        
        medication = query_gemini(f"Suggest a common medication for {predicted_disease} in 5 words or less.")
        suggestion = query_gemini(f"Provide a short medical advice (20 words or less) for {predicted_disease}.")
        
        return render_template('prediction.html', symptom=symptom, prediction=predicted_disease, medication=medication, suggestion=suggestion)
    
    return render_template('prediction.html', symptom=None, prediction=None, medication=None, suggestion=None)
    
if __name__ == '__main__':
    app.run(debug=False)

