import os
import numpy as np
import logging
import sys
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam
from sklearn.metrics import f1_score, precision_score
from audio_analyzer.sheets_utils import save_prediction_to_sheets

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TOOTpredictor")

# Suppress TensorFlow and absl logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Model path
base_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(project_root, 'training_models', 'TOOT_model.keras')

# Check if model exists, if not create a placeholder
try:
    if not os.path.exists(model_path):
        logger.warning(f"Model file not found at {model_path}. Creating a placeholder model.")
        
        # Create a simple placeholder model
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import Dense, Flatten, Conv2D, MaxPooling2D
        
        model = Sequential([
            Conv2D(32, (3, 3), activation='relu', input_shape=(224, 224, 3)),
            MaxPooling2D((2, 2)),
            Flatten(),
            Dense(64, activation='relu'),
            Dense(2, activation='softmax')  # Binary classification
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001), 
            loss='categorical_crossentropy', 
            metrics=['accuracy']
        )
        
        # Save the placeholder model
        model.save(model_path)
        logger.info(f"Placeholder model saved to {model_path}")
    else:
        model = load_model(model_path)
except Exception as e:
    logger.error(f"Error creating/loading model: {e}")
    model = None

# Function to load and preprocess images
def load_and_preprocess_image(img_path):
    if img_path is None:
        logger.error("Image path is None")
        raise ValueError("Image path is None")
    if not os.path.exists(img_path):
        logger.error(f"Image file does not exist: {img_path}")
        raise FileNotFoundError(f"Image file does not exist: {img_path}")
    img = image.load_img(img_path, target_size=(224, 224))  # Adjust size as per your model's input
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    img_array /= 255.0  # Normalize to [0, 1]
    return img_array

# Function to predict and display results for a specific image
def predict_and_display(img_path, output_box=None):
    # Define class names
    class_names = ['No Tooting', 'Tooting']

    # Check if model is available
    if model is None:
        logger.error("No model available for prediction")
        return 0, 0.0

    try:
        # Load and preprocess the specific image
        img_array = load_and_preprocess_image(img_path)

        # Predict the class of the image
        pred = model.predict(img_array)
        
        # Handle different prediction output shapes
        if pred.ndim > 1 and pred.shape[1] > 1:
            confidence = pred[0][1]  # Confidence for the positive class
        elif pred.ndim == 1 or pred.shape[1] == 1:
            confidence = pred[0][0]  # Use the first (and only) value
        else:
            logger.error(f"Unexpected prediction shape: {pred.shape}")
            return 0, 0.0

        predicted_class = 1 if confidence > 0.5 else 0  # Threshold for binary classification

        # Logging instead of GUI output
        logger.info(f'File: {os.path.basename(img_path)}, Predicted: {class_names[predicted_class]}, Confidence: {confidence * 100:.2f}%')

        # Save prediction to Google Sheets
        prediction_data = {
            'model': 'TOOT',
            'filename': os.path.basename(img_path),
            'prediction': class_names[predicted_class],
            'confidence': float(confidence)
        }
        save_prediction_to_sheets('toot', prediction_data)

        # Calculate metrics (with a single prediction)
        f1 = 0.0
        precision = 0.0

        return predicted_class, confidence, f1, precision

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return 0, 0.0, 0.0, 0.0

# Placeholder for other functions to maintain compatibility
def connect_to_google_sheets():
    logger.warning("Google Sheets integration is not available")
    return None

def save_results_to_google_sheets(*args, **kwargs):
    logger.warning("Google Sheets logging is not available")
    pass

def handle_feedback(*args, **kwargs):
    logger.warning("Manual retraining is not available")
    pass