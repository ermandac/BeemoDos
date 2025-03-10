import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend before importing pyplot

import os
import logging
import numpy as np
import sounddevice as sd
import librosa
import matplotlib.pyplot as plt
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from scipy.io import wavfile
import json
import soundfile as sf

import tensorflow as tf
from datetime import datetime

import sys
sys.path.append(os.path.join(settings.BASE_DIR, 'predictors'))
import BNBpredictor
import QNQpredictor
import TOOTpredictor

logger = logging.getLogger(__name__)

def index(request):
    """
    Render the main index page for bee audio analysis
    """
    # Get list of available audio input devices
    devices = sd.query_devices()
    input_devices = [
        {
            'index': i, 
            'name': device['name'], 
            'max_input_channels': device['max_input_channels']
        } 
        for i, device in enumerate(devices) 
        if device['max_input_channels'] > 0
    ]
    
    return render(request, 'index.html', {
        'input_devices': input_devices
    })

@csrf_exempt
def record_audio(request):
    """
    Handle audio recording request with device selection
    """
    try:
        # Get device and recording parameters from request
        device_index = int(request.POST.get('device', 0))
        duration = float(request.POST.get('duration', 5))  # seconds
        sample_rate = int(request.POST.get('sample_rate', 44100))  # Hz
        
        # Record audio from specified device
        recording = sd.rec(
            int(duration * sample_rate), 
            samplerate=sample_rate, 
            channels=1, 
            dtype='float64',
            device=device_index
        )
        sd.wait()
        
        # Save recording
        audio_filename = 'bee_recording.wav'
        audio_path = os.path.join(settings.MEDIA_ROOT, audio_filename)
        
        # Ensure media directory exists
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        
        # Write audio file using scipy
        wavfile.write(audio_path, sample_rate, (recording * 32767).astype(np.int16))
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Audio recorded successfully',
            'filename': audio_filename,
            'device': device_index
        })
    
    except Exception as e:
        logger.error(f"Audio recording error: {str(e)}")
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)

def get_audio_devices(request):
    """
    List available audio input devices
    """
    try:
        # Import sounddevice here to catch any import errors
        import sounddevice as sd
        
        # Get the list of all devices
        all_devices = sd.query_devices()
        
        # Log total number of devices for debugging
        logger.info(f"Total devices found: {len(all_devices)}")
        
        # Get the list of input devices
        input_devices = [
            {
                'index': i, 
                'name': device['name'], 
                'max_input_channels': device['max_input_channels']
            } 
            for i, device in enumerate(all_devices) 
            if device['max_input_channels'] > 0
        ]
        
        # Log input devices for debugging
        logger.info(f"Input devices found: {input_devices}")
        
        return JsonResponse({
            'status': 'success', 
            'devices': input_devices
        })
    except ImportError as e:
        logger.error(f"Failed to import sounddevice: {str(e)}")
        return JsonResponse({
            'status': 'error', 
            'message': f'Sounddevice import failed: {str(e)}'
        }, status=500)
    except Exception as e:
        # Log the full traceback for more detailed error information
        import traceback
        logger.error(f"Error listing audio devices: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)

def generate_spectrogram(request=None, audio_path=None, predictor_type='BNQ'):
    """
    Generate spectrogram from audio file
    
    Args:
        request (HttpRequest, optional): Django request object
        audio_path (str, optional): Path to the input audio file
        predictor_type (str, optional): Type of predictor for naming, defaults to 'BNQ'
    
    Returns:
        JsonResponse or str path to spectrogram
    """
    try:
        # Ensure media directory exists
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        
        # If called from URL route, find the most recent audio file
        if request is not None:
            # Find the most recent audio file
            audio_files = [f for f in os.listdir(settings.MEDIA_ROOT) if f.startswith('bee_recording')]
            if not audio_files:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No audio file found'
                }, status=404)
            
            # Use the most recent audio file
            audio_path = os.path.join(settings.MEDIA_ROOT, max(audio_files, key=lambda f: os.path.getctime(os.path.join(settings.MEDIA_ROOT, f))))
        
        # Validate audio path
        if audio_path is None or not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return JsonResponse({
                'status': 'error',
                'message': 'Audio file not found'
            }, status=404)
        
        # Generate timestamp for unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create spectrogram filename with predictor type
        spectrogram_filename = f'BeemoDosSpectrogram_{predictor_type}_{timestamp}.png'
        spectrogram_path = os.path.join(settings.MEDIA_ROOT, spectrogram_filename)
        
        # Load audio file
        y, sr = librosa.load(audio_path)
        
        # Create spectrogram
        plt.figure(figsize=(12, 8))
        librosa.display.specshow(
            librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max), 
            sr=sr, 
            x_axis='time', 
            y_axis='hz'
        )
        plt.colorbar(format='%+2.0f dB')
        plt.title(f'Spectrogram - {predictor_type}')
        plt.tight_layout()
        
        # Save spectrogram
        plt.savefig(spectrogram_path)
        plt.close()
        
        # If called from URL route, return JSON response
        if request is not None:
            return JsonResponse({
                'status': 'success',
                'spectrogram_path': spectrogram_filename
            })
        
        # If called programmatically, return spectrogram path
        return spectrogram_path
    
    except Exception as e:
        logger.error(f"Spectrogram generation error for {predictor_type}: {e}")
        
        # If called from URL route, return error JSON
        if request is not None:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
        
        # If called programmatically, return None
        return None

@csrf_exempt
def record_and_generate_spectrograms(request):
    """
    Record audio for multiple predictors and generate spectrograms
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        duration = data.get('duration', 5)  # Default 5 seconds
        device_index = data.get('device_index', None)

        # Validate inputs
        if not isinstance(duration, (int, float)) or duration <= 0:
            return JsonResponse({
                'status': 'error', 
                'message': 'Invalid recording duration'
            }, status=400)

        # Predictors to record
        predictors = ['BNQ', 'QNQ', 'TOOT']
        num_recordings = 1

        # Prepare storage for recordings and spectrograms
        all_recordings = {}
        all_spectrograms = {}
        analysis_results = {}

        # Create directory for this recording session
        session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        recordings_base_dir = os.path.join(settings.MEDIA_ROOT, 'recordings')
        session_dir = os.path.join(recordings_base_dir, session_timestamp)
        os.makedirs(session_dir, exist_ok=True)

        # Ensure proper permissions
        os.chmod(session_dir, 0o755)

        # Detailed logging of paths
        print("Path Configuration:")
        print(f"BASE_DIR: {settings.BASE_DIR}")
        print(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
        print(f"MEDIA_URL: {settings.MEDIA_URL}")
        print(f"Session Directory: {session_dir}")
        print(f"Recordings Base Directory: {recordings_base_dir}")

        # Find the most recent recording directory
        try:
            # List all subdirectories in the recordings directory
            existing_sessions = [
                d for d in os.listdir(recordings_base_dir) 
                if os.path.isdir(os.path.join(recordings_base_dir, d))
            ]
            
            # Sort sessions by timestamp (newest first)
            existing_sessions.sort(reverse=True)
            
            print("Existing Recording Sessions:", existing_sessions)
        except Exception as dir_list_error:
            print(f"Error listing recording sessions: {dir_list_error}")
            existing_sessions = []

        # Record and process for each predictor
        for predictor in predictors:
            predictor_recordings = []
            predictor_spectrograms = []

            for i in range(num_recordings):
                # Generate unique filenames
                audio_filename = f'{predictor}_recording_{i+1}.wav'
                spectrogram_filename = f'{predictor}_spectrogram_{i+1}.png'
                
                # Full paths with absolute resolution
                audio_path = os.path.abspath(os.path.join(session_dir, audio_filename))
                spectrogram_path = os.path.abspath(os.path.join(session_dir, spectrogram_filename))

                # Record audio
                sample_rate = 44100
                recording = sd.rec(
                    int(duration * sample_rate), 
                    samplerate=sample_rate, 
                    channels=1, 
                    dtype='float64',
                    device=device_index
                )
                sd.wait()  # Wait for recording to complete

                # Save audio file
                sf.write(audio_path, recording, sample_rate)
                os.chmod(audio_path, 0o644)

                # Generate spectrogram
                plt.figure(figsize=(10, 4))
                librosa.display.specshow(
                    librosa.amplitude_to_db(
                        np.abs(librosa.stft(recording.flatten())), 
                        ref=np.max
                    ), 
                    sr=sample_rate, 
                    x_axis='time', 
                    y_axis='hz'
                )
                plt.colorbar(format='%+2.0f dB')
                plt.title(f'{predictor} Spectrogram')
                plt.tight_layout()
                plt.savefig(spectrogram_path)
                os.chmod(spectrogram_path, 0o644)
                plt.close()

                # Relative paths for frontend
                rel_audio_path = os.path.relpath(audio_path, settings.MEDIA_ROOT)
                rel_spectrogram_path = os.path.relpath(spectrogram_path, settings.MEDIA_ROOT)

                # Detailed path logging
                print(f"\nSpectrogram for {predictor}:")
                print(f"  Full Path: {spectrogram_path}")
                print(f"  Relative Path: {rel_spectrogram_path}")
                print(f"  Media URL Path: {settings.MEDIA_URL}{rel_spectrogram_path}")
                print(f"  File Exists: {os.path.exists(spectrogram_path)}")

                # Store recordings and spectrograms
                predictor_recordings.append({
                    'audio_path': rel_audio_path,
                    'spectrogram_path': rel_spectrogram_path
                })
                
                # Use full media URL
                predictor_spectrograms.append(f'{settings.MEDIA_URL}{rel_spectrogram_path}')

            # Store for each predictor
            all_recordings[predictor] = predictor_recordings
            all_spectrograms[predictor] = predictor_spectrograms

            # Perform analysis (placeholder - replace with actual analysis)
            analysis_results[predictor] = {
                'recording_count': num_recordings,
                'status': 'Processed successfully'
            }

        # Return successful response
        return JsonResponse({
            'status': 'success',
            'recordings': all_recordings,
            'spectrograms': all_spectrograms,
            'analysis_results': analysis_results,
            'debug_info': {
                'existing_sessions': existing_sessions,
                'current_session': session_timestamp
            }
        })

    except Exception as e:
        # Log the full error
        logger.error(f"Error in record_and_generate_spectrograms: {str(e)}")
        logger.error(traceback.format_exc())

        # Return error response
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)

def predictors_view(request):
    """
    Render the predictors analysis page
    """
    return render(request, 'predictors.html')

@csrf_exempt
def analyze_audio(request):
    """
    Analyze multiple spectrograms using pre-trained machine learning models
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

    try:
        # Parse request data
        data = json.loads(request.body)
        spectrograms = data.get('spectrograms', [])

        # Validate input
        if not spectrograms:
            return JsonResponse({'error': 'No spectrograms provided'}, status=400)

        # Perform analysis for each predictor
        analysis_results = {}

        # Predictor configurations with more robust error handling
        predictors = [
            {
                'name': 'BNQ',
                'function': BNBpredictor.predict_and_display,
                'labels': ['No Bees Detected', 'Bees Detected']
            },
            {
                'name': 'QNQ',
                'function': QNQpredictor.QNQpredictor,
                'labels': ['No Queen Detected', 'Queen Detected']
            },
            {
                'name': 'TOOT',
                'function': TOOTpredictor.predict_and_display,
                'labels': ['No Tooting', 'Tooting']
            }
        ]

        # Process each predictor
        for predictor in predictors:
            try:
                # Predict using the specific predictor
                result = predictor['function'](spectrograms[0])
                
                # Log raw result for debugging
                logger.info(f"{predictor['name']} Raw Result: {result}")
                
                # Safely extract prediction details with extensive error checking
                if not isinstance(result, (list, tuple)) or len(result) < 2:
                    logger.error(f"{predictor['name']} returned invalid result: {result}")
                    raise ValueError(f"Invalid prediction result for {predictor['name']}")
                
                # Handle different return formats (4 or 2 elements)
                if len(result) == 4:
                    predicted_class, confidence, f1, precision = result
                else:
                    predicted_class, confidence = result
                    f1, precision = 0.0, 0.0
                
                # Log detailed prediction information
                logger.info(f"{predictor['name']} Prediction - Class: {predicted_class}, Raw Confidence: {confidence}")
                
                # Store results with explicit type conversion
                analysis_results[predictor['name']] = {
                    'predicted_class': int(predicted_class),
                    'confidence': float(confidence),
                    'label': predictor['labels'][int(predicted_class)],
                    'f1_score': float(f1),
                    'precision': float(precision),
                    'raw_result': list(result)  # Ensure full result is preserved
                }
            except Exception as e:
                logger.error(f"{predictor['name']} prediction error: {e}")
                analysis_results[predictor['name']] = {
                    'predicted_class': 0,
                    'confidence': 0.0,
                    'label': 'Prediction Failed',
                    'error': str(e)
                }

        # Prepare final response with additional metadata
        response_data = {
            'success': True,
            'recording_count': 1,  # Assuming single recording
            'status': 'Processed successfully',
            'analysis_results': analysis_results
        }

        # Log the entire response for verification
        logger.info(f"Complete Response: {json.dumps(response_data, indent=2)}")

        return JsonResponse(response_data)
    
    except Exception as e:
        logger.error(f"Audio analysis error: {str(e)}")
        return JsonResponse({
            'success': False,
            'recording_count': 0,
            'status': 'Processing failed',
            'error': str(e)
        }, status=500)
