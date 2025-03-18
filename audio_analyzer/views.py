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
import re

import tensorflow as tf
from datetime import datetime

import sys
sys.path.append(os.path.join(settings.BASE_DIR, 'predictors'))
import BNBpredictor
import QNQpredictor
import TOOTpredictor

# Import Discord utilities
from .discord_utils import send_discord_message

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

        # Collect all spectrogram paths for analysis
        all_spectrogram_paths = []
        for predictor, paths in all_spectrograms.items():
            # Convert from media URL to relative path
            for path in paths:
                rel_path = path.replace(settings.MEDIA_URL, '')
                all_spectrogram_paths.append(rel_path)
        
        # Initialize analysis_results with default values
        analysis_results = {
            'BNQ': {'predicted_class': 0, 'confidence': 0.0, 'label': 'No Analysis', 'f1_score': 0.0, 'precision': 0.0, 'raw_result': [0, 0, 0, 0]},
            'QNQ': {'predicted_class': 0, 'confidence': 0.0, 'label': 'No Analysis', 'f1_score': 0.0, 'precision': 0.0, 'raw_result': [0, 0, 0, 0]},
            'TOOT': {'predicted_class': 0, 'confidence': 0.0, 'label': 'No Analysis', 'f1_score': 0.0, 'precision': 0.0, 'raw_result': [0, 0, 0, 0]}
        }
        
        # Analyze the spectrograms and send Discord notification
        if all_spectrogram_paths:
            logger.info(f"Calling analyze_audio with {len(all_spectrogram_paths)} spectrograms")
            
            # Create a mock request with the spectrogram paths in the body
            class MockRequest:
                method = 'POST'
                body = json.dumps({'spectrograms': all_spectrogram_paths}).encode('utf-8')
            
            # Call analyze_audio
            try:
                logger.info(f"About to call analyze_audio with paths: {all_spectrogram_paths}")
                analysis_response = analyze_audio(MockRequest())
                logger.info(f"analyze_audio response status: {analysis_response.status_code}")
                
                # Debug the response content
                response_content = analysis_response.content.decode('utf-8')
                logger.info(f"Raw response content: {response_content}")
                
                analysis_data = json.loads(response_content)
                analysis_results = analysis_data.get('analysis_results', {})
                
                logger.info(f"Analysis completed: {json.dumps(analysis_results, indent=2)}")
            except Exception as analysis_error:
                logger.error(f"Error in analysis: {analysis_error}")
                logger.error(traceback.format_exc())
        else:
            logger.warning("No spectrograms available for analysis")

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
                # Convert relative path to absolute path if needed
                spectrogram_path = spectrograms[0]
                if not os.path.isabs(spectrogram_path):
                    spectrogram_path = os.path.join(settings.MEDIA_ROOT, spectrogram_path)
                
                # Ensure the file exists before prediction
                if not os.path.exists(spectrogram_path):
                    logger.error(f"Spectrogram file not found: {spectrogram_path}")
                    raise FileNotFoundError(f"Spectrogram file not found: {spectrogram_path}")
                
                logger.info(f"Predicting {predictor['name']} using file: {spectrogram_path}")
                result = predictor['function'](spectrogram_path)
                
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
                    'confidence': float(confidence) * 100,  # Multiply by 100 for frontend display
                    'label': predictor['labels'][int(predicted_class)],
                    'f1_score': float(f1),
                    'precision': float(precision),
                    'raw_result': list(result)  # Ensure full result is preserved
                }
            except Exception as e:
                logger.error(f"{predictor['name']} prediction error: {e}")
                analysis_results[predictor['name']] = {
                    'predicted_class': 0,
                    'confidence': 0.0,  # Keep as 0.0 for failed predictions
                    'label': 'Prediction Failed',
                    'error': str(e)
                }

        # Send notification to Discord with analysis results
        try:
            # Format the message with prediction results in JSON-like format
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = "**BeemoDos Analysis Results** - " + timestamp + "\n"
            message += "```json\n{"
            
            # Add BNB result if available
            if 'BNQ' in analysis_results:
                message += '\n  "BNB Prediction": {'
                message += '\n    "File": "' + (spectrograms[0] if spectrograms else "Unknown") + '",'  
                message += '\n    "Predicted": "' + analysis_results["BNQ"]["label"] + '",'  
                message += '\n    "Confidence": ' + str(analysis_results["BNQ"]["confidence"]) + ','  
                message += '\n    "Predicted Class": ' + str(analysis_results["BNQ"]["predicted_class"]) + ','  
                message += '\n    "F1 Score": ' + str(analysis_results["BNQ"]["f1_score"]) + ','  
                message += '\n    "Precision": ' + str(analysis_results["BNQ"]["precision"]) + ''  
                message += '\n  }'
            
            # Add QNQ result if available
            if 'QNQ' in analysis_results:
                if 'BNQ' in analysis_results:  # Add comma if BNQ was included
                    message += ","
                message += '\n  "QNQ Prediction": {'
                message += '\n    "File": "' + (spectrograms[0] if spectrograms else "Unknown") + '",'  
                message += '\n    "Predicted": "' + analysis_results["QNQ"]["label"] + '",'  
                message += '\n    "Confidence": ' + str(analysis_results["QNQ"]["confidence"]) + ','  
                message += '\n    "Predicted Class": ' + str(analysis_results["QNQ"]["predicted_class"]) + ','  
                message += '\n    "F1 Score": ' + str(analysis_results["QNQ"]["f1_score"]) + ','  
                message += '\n    "Precision": ' + str(analysis_results["QNQ"]["precision"]) + ''  
                message += '\n  }'
            
            # Add TOOT result if available
            if 'TOOT' in analysis_results:
                if 'BNQ' in analysis_results or 'QNQ' in analysis_results:  # Add comma if previous results were included
                    message += ","
                message += '\n  "TOOT Prediction": {'
                message += '\n    "File": "' + (spectrograms[0] if spectrograms else "Unknown") + '",'  
                message += '\n    "Predicted": "' + analysis_results["TOOT"]["label"] + '",'  
                message += '\n    "Confidence": ' + str(analysis_results["TOOT"]["confidence"]) + ','  
                message += '\n    "Predicted Class": ' + str(analysis_results["TOOT"]["predicted_class"]) + ','  
                message += '\n    "F1 Score": ' + str(analysis_results["TOOT"]["f1_score"]) + ','  
                message += '\n    "Precision": ' + str(analysis_results["TOOT"]["precision"]) + ''  
                message += '\n  }'
            
            message += '\n}\n```\n'
            
            # Add recording analysis information
            message += "**Recording Analysis**\n"
            message += "Date: " + datetime.now().strftime("%Y-%m-%d") + "\n"
            message += "Time: " + datetime.now().strftime("%H:%M:%S") + "\n"
            
            # Try to extract frequency information if available
            try:
                # Calculate frequency information from the audio file
                if spectrograms and len(spectrograms) > 0:
                    # Get the audio file path from the spectrogram path
                    spectrogram_path = spectrograms[0]
                    logger.info(f"Attempting frequency analysis for spectrogram: {spectrogram_path}")
                    
                    # Extract session directory from spectrogram path
                    # Format appears to be: recordings/20250313_152709/BNQ_spectrogram_1.png
                    match = re.match(r'recordings/(\d+_\d+)/', spectrogram_path)
                    if match:
                        session_dir = match.group(1)
                        audio_dir = os.path.join(settings.MEDIA_ROOT, 'recordings', session_dir)
                        logger.info(f"Looking for audio files in: {audio_dir}")
                        
                        # Look for WAV files in the session directory
                        if os.path.exists(audio_dir):
                            audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.wav')]
                            logger.info(f"Found audio files in {audio_dir}: {audio_files}")
                            
                            if audio_files:
                                # Use the first audio file found
                                audio_path = os.path.join(audio_dir, audio_files[0])
                                logger.info(f"Using audio file for analysis: {audio_path}")
                                
                                # Load the audio file
                                sample_rate, samples = wavfile.read(audio_path)
                                
                                # Convert stereo to mono if needed
                                if len(samples.shape) > 1 and samples.shape[1] > 1:
                                    samples = np.mean(samples, axis=1)
                                
                                # Perform FFT
                                fft_data = np.fft.rfft(samples)
                                freqs = np.fft.rfftfreq(len(samples), 1/sample_rate)
                                
                                # Filter out low-frequency noise (below 20 Hz)
                                MIN_FREQUENCY = 20
                                mask = np.abs(freqs) >= MIN_FREQUENCY
                                filtered_freqs = freqs[mask]
                                filtered_fft = np.abs(fft_data[mask])
                                
                                # Compute frequency statistics
                                if len(filtered_freqs) > 0 and len(filtered_fft) > 0:
                                    # Find the index of the maximum amplitude in the filtered FFT data
                                    max_idx = np.argmax(filtered_fft)
                                    peak_freq = filtered_freqs[max_idx]
                                    avg_freq = np.mean(np.abs(filtered_freqs))
                                    
                                    # Compute RMS amplitude for activity classification
                                    rms_amplitude = np.sqrt(np.mean(samples**2)) / 32768.0
                                    
                                    # Classify activity level based on frequency and amplitude
                                    if avg_freq < 100:
                                        base_level = "Low"
                                    elif 100 <= avg_freq <= 300:
                                        base_level = "Normal"
                                    elif 300 < avg_freq <= 500:
                                        base_level = "High"
                                    else:
                                        base_level = "Chaotic"
                                    
                                    # Amplitude-based refinement
                                    if rms_amplitude < 0.1:
                                        activity = f"Very {base_level}"
                                    elif 0.1 <= rms_amplitude < 0.3:
                                        activity = f"{base_level}"
                                    elif 0.3 <= rms_amplitude < 0.6:
                                        activity = f"Intense {base_level}"
                                    else:
                                        activity = f"Extremely {base_level}"
                                    
                                    # Add frequency information to the message
                                    message += "Frequency Data: Average " + str(avg_freq) + "Hz, Peak " + str(peak_freq) + "Hz\n"
                                    message += "Activity Level: " + activity + " Activity\n"
                                    
                                    logger.info(f"Frequency analysis complete: Avg={avg_freq}Hz, Peak={peak_freq}Hz, Activity={activity}")
                                else:
                                    logger.warning("No valid frequency data found after filtering")
                                    message += "Frequency Data: No valid frequency data found\n"
                                    message += "Activity Level: Unknown\n"
                            else:
                                logger.warning(f"No audio files found in directory: {audio_dir}")
                                message += "Frequency Data: No audio files found\n"
                                message += "Activity Level: Unknown\n"
                        else:
                            logger.warning(f"Audio directory not found: {audio_dir}")
                            message += "Frequency Data: Audio directory not found\n"
                            message += "Activity Level: Unknown\n"
                    else:
                        logger.warning(f"Could not extract session directory from path: {spectrogram_path}")
                        message += "Frequency Data: Could not locate audio file\n"
                        message += "Activity Level: Unknown\n"
                else:
                    logger.warning("No spectrograms available for frequency analysis")
                    message += "Frequency Data: No spectrograms available\n"
                    message += "Activity Level: Unknown\n"
            except Exception as e:
                logger.error(f"Error in frequency analysis: {e}")
                logger.error(traceback.format_exc())
                message += "Frequency Data: Error during analysis\n"
                message += "Activity Level: Unknown\n"
            
            # Add interpretation and recommendations based on predictions
            message += "\n**Interpretation & Recommendations**\n"
            
            # BNQ interpretation
            if 'BNQ' in analysis_results:
                bnq_class = analysis_results['BNQ']['predicted_class']
                bnq_confidence = analysis_results['BNQ']['confidence']
                if bnq_class == 1 and bnq_confidence > 50:
                    message += "**Bees Detected**: Hive is active. Continue regular monitoring.\n"
                else:
                    message += "**Low Bee Activity**: Consider checking for potential issues.\n"
            
            # QNQ interpretation
            if 'QNQ' in analysis_results:
                qnq_class = analysis_results['QNQ']['predicted_class']
                qnq_confidence = analysis_results['QNQ']['confidence']
                if qnq_class == 1 and qnq_confidence > 50:
                    message += "**Queen Detected**: Queen is present and active.\n"
                else:
                    message += "**No Queen Detected**: Consider checking queen status.\n"
            
            # TOOT interpretation
            if 'TOOT' in analysis_results:
                toot_class = analysis_results['TOOT']['predicted_class']
                toot_confidence = analysis_results['TOOT']['confidence']
                if toot_class == 1 and toot_confidence > 50:
                    message += "**Tooting Detected**: Potential queen emergence or competition.\n"
                else:
                    message += "**No Tooting**: Normal hive sounds detected.\n"
            
            # Add link to web interface
            message += "\n[View Full Analysis on BeemoDos Dashboard](http://localhost:8000/audio_analyzer/)\n"
            
            # Get the path to the spectrogram image
            spectrogram_path = None
            if spectrograms and len(spectrograms) > 0:
                spectrogram_path = os.path.join(settings.MEDIA_ROOT, spectrograms[0])
            
            # Send the message to Discord
            discord_result = send_discord_message(message, spectrogram_path)
            if discord_result:
                logger.info("Successfully sent analysis results to Discord")
            else:
                logger.error("Failed to send analysis results to Discord")
                logger.error(f"Discord message: {message}")
                logger.error(f"Spectrogram path: {spectrogram_path}")
        except Exception as discord_error:
            logger.error(f"Error sending Discord notification: {discord_error}")
            # Continue processing even if Discord notification fails

        # Prepare final response with additional metadata
        # Convert NumPy types to native Python types for JSON serialization
        serializable_results = {}
        for predictor_name, predictor_data in analysis_results.items():
            serializable_results[predictor_name] = {}
            for key, value in predictor_data.items():
                # Convert NumPy types to native Python types
                if hasattr(value, 'item') and callable(getattr(value, 'item')):
                    serializable_results[predictor_name][key] = value.item()
                elif isinstance(value, (list, tuple)):
                    # Convert each item in the list/tuple if needed
                    serializable_results[predictor_name][key] = [
                        item.item() if hasattr(item, 'item') and callable(getattr(item, 'item')) else item
                        for item in value
                    ]
                else:
                    serializable_results[predictor_name][key] = value
        
        response_data = {
            'success': True,
            'recording_count': 1,  # Assuming single recording
            'status': 'Processed successfully',
            'analysis_results': serializable_results
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

@csrf_exempt
def send_discord_notification(request):
    """
    API endpoint to send a notification to Discord
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        image_path = data.get('image_path', None)
        
        if not message:
            return JsonResponse({'success': False, 'error': 'Message is required'}, status=400)
        
        # Validate image path if provided
        if image_path and not os.path.exists(image_path):
            return JsonResponse({'success': False, 'error': 'Image file not found'}, status=404)
        
        # Send to Discord
        result = send_discord_message(message, image_path)
        
        if result:
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to send message'}, status=500)
    except Exception as e:
        logger.error(f'Error in send_discord_notification: {e}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def test_discord(request):
    """
    Simple endpoint to test Discord notification
    """
    try:
        logger.info("Testing Discord notification")
        message = "This is a test message from BeemoDos at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Send the message to Discord
        result = send_discord_message(message)
        
        if result:
            return JsonResponse({'success': True, 'message': 'Discord notification sent successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Failed to send Discord notification'}, status=500)
    except Exception as e:
        logger.error(f"Error in test_discord: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
