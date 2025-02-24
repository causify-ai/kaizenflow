from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import pickle

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict_gross_income():
    try:
        # Load the model from the pickle file.
        model_filename = 'randomforest.pkl'
        with open(model_filename, 'rb') as file:
            model = pickle.load(file)

        # Get input features from the request JSON.
        input_features = request.get_json()  # Adjusted here.

        # Convert the input features to a DataFrame.
        input_df = pd.DataFrame([input_features])

        # Preprocess and predict.
        prepared_input = model.named_steps['preprocessor'].transform(input_df)
        prediction = model.named_steps['regressor'].predict(prepared_input)

        # Send back the prediction.
        return jsonify({'Predicted Gross Income': float(prediction[0])})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    # Change the host parameter to '0.0.0.0' to make the Flask server externally visible.
    app.run(debug=True, host='0.0.0.0', port=8082)