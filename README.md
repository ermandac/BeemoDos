# BeemoDos: Bee Audio Analysis Platform

## Project Overview
BeemoDos is a Django-based web application designed to analyze bee audio recordings, generate spectrograms, and provide insights into bee behavior using machine learning.

## Key Components
- Audio recording functionality
- Spectrogram generation
- Machine learning model inference for bee behavior detection

## Prerequisites
- Python 3.9+
- pip
- virtualenv (recommended)
- Git
- FFmpeg (for audio processing)

## System Dependencies
### Ubuntu/Debian
```bash
# Audio processing dependencies
sudo apt-get update
sudo apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg \
    libsndfile1
```

### Fedora/RHEL
```bash
# Audio processing dependencies
sudo dnf install -y \
    portaudio-devel \
    python3-pyaudio \
    ffmpeg \
    libsndfile
```

### macOS (using Homebrew)
```bash
# Audio processing dependencies
brew install portaudio ffmpeg libsndfile
```

### Windows
- Download and install PortAudio from the official website
- Ensure FFmpeg is added to system PATH

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/ermandac/BeemoDos.git
cd BeemoDos
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root with the following content:
```
SECRET_KEY=your_django_secret_key
DEBUG=True
```

### 5. Set Up Database
```bash
python manage.py migrate
```

### 6. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 7. Run Development Server
```bash
python manage.py runserver
```

## Machine Learning Models
- Pre-trained models are excluded from the repository
- Place your machine learning models in the `training_models/` directory
- Supported model formats: `.keras`, `.h5`, `.pkl`

## Development Workflow
- Always work in a virtual environment
- Install new dependencies with `pip install` and update `requirements.txt`
- Run tests before committing: `python manage.py test`

## Project Structure
- `audio_analyzer/`: Core audio analysis logic
- `frontend/`: Web interface components
- `predictors/`: Machine learning model inference
- `training_models/`: (Gitignored) Machine learning model storage

## Troubleshooting
- Ensure all dependencies are installed
- Check Django and Python versions compatibility
- Verify audio processing dependencies (FFmpeg)
