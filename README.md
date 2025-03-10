# BeemoDos: Bee Audio Analysis Platform

## Project Overview
BeemoDos is a Django-based web application designed to analyze bee audio recordings, generate spectrograms, and provide insights into bee behavior using machine learning.

## Features
- Real-time audio recording
- Spectrogram generation
- Machine learning-based bee behavior analysis
- Web interface for easy interaction

## Prerequisites
- Python 3.9+
- pip
- virtualenv (recommended)

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/BeemoDos.git
cd BeemoDos
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Database
```bash
python manage.py migrate
```

### 5. Run Development Server
```bash
python manage.py runserver
```

## Machine Learning Model
Place your pre-trained `.keras` model in the `ml_models/` directory with the name `bee_behavior_model.keras`.

## Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
Distributed under the MIT License. See `LICENSE` for more information.

## Contact
Your Name - your.email@example.com

Project Link: [https://github.com/yourusername/BeemoDos](https://github.com/yourusername/BeemoDos)
