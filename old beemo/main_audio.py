import os
import numpy as np
import time
from datetime import datetime
import sounddevice as sd
from scipy.io.wavfile import write
import matplotlib.pyplot as plt
from scipy.io import wavfile
import logging

# Google Sheets and Discord imports
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import discord
from discord.ext import commands
import asyncio

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FOLDER = os.path.join(BASE_DIR, 'SavedIMG')
os.makedirs(SAVE_FOLDER, exist_ok=True)

# Audio Recording Parameters
CHANNELS = 2
RATE = 44100
CHUNK = 1024
DURATION = 15
MIN_FREQUENCY = 20

# Logging Configuration
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BeemoAudioProcessor")

class BeemoAudioProcessor:
    def __init__(self, 
                 spreadsheet_id="1h387i_m0wb2RQ8zrO-gEwHPGzs0mp8qtgYjxXO7Gg00", 
                 scopes=["https://www.googleapis.com/auth/spreadsheets"]):
        """
        Initialize the audio processor with Google Sheets and Discord integration
        """
        self.spreadsheet_id = spreadsheet_id
        self.scopes = scopes
        self.sheet_service = self._connect_to_google_sheets()

    def _connect_to_google_sheets(self):
        """
        Authenticate and connect to Google Sheets
        """
        try:
            credentials_path = os.path.join(BASE_DIR, 'BeemoApp', 'GsheetAPI', 'Freq-New-Client.json')
            creds = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=self.scopes)
            creds.refresh(Request())
            service = build('sheets', 'v4', credentials=creds)
            return service.spreadsheets()
        except Exception as e:
            logger.error(f"Google Sheets connection error: {e}")
            return None

    def list_audio_devices(self):
        """
        Comprehensive audio device listing with advanced filtering and categorization
        """
        import sounddevice as sd
        
        try:
            all_devices = sd.query_devices()
            
            # Advanced device categorization
            input_devices = []
            output_devices = []
            usb_input_devices = []
            
            for idx, device in enumerate(all_devices):
                device_info = {
                    'index': idx,
                    'name': device['name'],
                    'max_input_channels': device['max_input_channels'],
                    'max_output_channels': device['max_output_channels'],
                    'default_samplerate': device.get('default_samplerate', 'N/A'),
                    'host_api': device.get('hostapi', 'Unknown')
                }
                
                if device['max_input_channels'] > 0:
                    input_devices.append(device_info)
                    if 'USB' in device['name']:
                        usb_input_devices.append(device_info)
                
                if device['max_output_channels'] > 0:
                    output_devices.append(device_info)
            
            # Logging and display
            print("\n=== Audio Device Inventory ===")
            print(f"Total Devices: {len(all_devices)}")
            print(f"Input Devices: {len(input_devices)}")
            print(f"USB Input Devices: {len(usb_input_devices)}")
            print(f"Output Devices: {len(output_devices)}")
            
            # Detailed device display
            print("\n=== Input Devices Details ===")
            for device in input_devices:
                print(f"\nDevice {device['index']}:")
                print(f"  Name: {device['name']}")
                print(f"  Input Channels: {device['max_input_channels']}")
                print(f"  Sample Rate: {device['default_samplerate']} Hz")
                print(f"  Host API: {device['host_api']}")
            
            return {
                'all_devices': all_devices,
                'input_devices': input_devices,
                'output_devices': output_devices,
                'usb_input_devices': usb_input_devices
            }
        
        except Exception as e:
            logger.error(f"Device listing error: {e}")
            return None

    def select_audio_device(self, device_index=None):
        """
        Advanced audio device selection with intelligent fallback and validation
        """
        import sounddevice as sd
        
        try:
            # Get comprehensive device information
            device_inventory = self.list_audio_devices()
            
            if not device_inventory or not device_inventory['input_devices']:
                raise ValueError("No input audio devices available!")
            
            input_devices = device_inventory['input_devices']
            usb_input_devices = device_inventory.get('usb_input_devices', [])
            
            # Device selection strategy
            if device_index is None:
                # Priority: USB devices → First input device
                if usb_input_devices:
                    device_index = usb_input_devices[0]['index']
                else:
                    device_index = input_devices[0]['index']
            
            # Validate device index
            valid_indices = [device['index'] for device in input_devices]
            if device_index not in valid_indices:
                logger.warning(f"Invalid device index {device_index}. Falling back to first input device.")
                device_index = input_devices[0]['index']
            
            # Safe device configuration
            try:
                selected_device = sd.query_devices(device_index)
                sd.default.device = (device_index, -1)  # Input device, default output
            except Exception as config_error:
                logger.error(f"Device configuration error: {config_error}")
                raise
            
            # Logging selected device details
            print("\n=== Selected Audio Device ===")
            print(f"Index: {device_index}")
            print(f"Name: {selected_device['name']}")
            print(f"Input Channels: {selected_device['max_input_channels']}")
            print(f"Sample Rate: {selected_device.get('default_samplerate', 'N/A')} Hz")
            
            return selected_device['name'], selected_device['max_input_channels']
        
        except Exception as e:
            logger.error(f"Comprehensive device selection error: {e}")
            raise

    def record_audio(self, duration=10, channels=None, filename=None, device_index=None):
        """
        Record audio with robust device and format configuration
        
        Args:
            duration (float): Recording duration in seconds
            channels (int, optional): Number of audio channels
            filename (str, optional): Output filename for the audio recording
            device_index (int, optional): Specific input device index to use
        
        Returns:
            str: Path to the recorded audio file or None if recording fails
        """
        try:
            # Validate and configure device
            devices = sd.query_devices()
            
            # Explicitly select input device
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            if not input_devices:
                raise ValueError("No input audio devices found")
            
            # Device selection logic
            if device_index is not None:
                # Validate user-selected device index
                if device_index < 0 or device_index >= len(devices):
                    logger.warning(f"Invalid device index {device_index}. Falling back to first available input device.")
                    device_index = devices.index(input_devices[0])
                elif devices[device_index]['max_input_channels'] == 0:
                    logger.warning(f"Selected device at index {device_index} is not an input device. Falling back.")
                    device_index = devices.index(input_devices[0])
            else:
                # Default to first input device if no index specified
                device_index = devices.index(input_devices[0])
            
            # Get selected device details
            selected_device = devices[device_index]
            
            # Print device details for debugging
            print(f"\n=== Selected Audio Device ===")
            print(f"Index: {device_index}")
            print(f"Name: {selected_device['name']}")
            print(f"Input Channels: {selected_device['max_input_channels']}")
            print(f"Sample Rate: {selected_device.get('default_samplerate', 44100.0)} Hz")
            
            # Determine max supported channels
            max_supported_channels = selected_device.get('max_input_channels', 2)
            
            # Channel configuration with robust fallback
            if channels is None or channels > max_supported_channels:
                channels = min(max_supported_channels, 2)  # Default to stereo or mono
            
            if channels < 1:
                logger.warning(f"Invalid channel count {channels}. Defaulting to 1.")
                channels = 1
            
            # Filename generation
            if not filename:
                filename = f"BeemoDos_Audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            
            audio_path = os.path.join(SAVE_FOLDER, filename)
            
            # Recording configuration
            RATE = int(selected_device.get('default_samplerate', 44100))
            CHUNK = 1024  # Smaller chunk size for better buffer management
            
            # Explicitly set device and parameters
            sd.default.device = (device_index, -1)  # Specific input device index
            sd.default.channels = channels
            sd.default.dtype = 'int16'  # Most compatible audio format
            sd.default.samplerate = RATE
            
            # Pre-allocate audio data array
            audio_data = np.zeros((int(duration * RATE), channels), dtype='int16')
            
            def audio_callback(indata, frames, time, status):
                """
                Robust audio input callback
                """
                if status:
                    logger.warning(f"Audio input status: {status}")
                
                # Copy input data to pre-allocated array
                current_frame = int(time.inputBufferAdcTime * RATE)
                end_frame = current_frame + frames
                
                if end_frame <= audio_data.shape[0]:
                    audio_data[current_frame:end_frame, :] = indata
                else:
                    logger.warning("Audio recording exceeded pre-allocated buffer")
            
            # Stream with explicit error handling and callback
            with sd.InputStream(callback=audio_callback, 
                                channels=channels, 
                                samplerate=RATE, 
                                blocksize=CHUNK,
                                dtype='int16',
                                device=device_index) as stream:
                # Wait for the specified duration
                sd.sleep(int(duration * 1000))
            
            # Trim any unused portions of the array
            audio_data = audio_data[:int(duration * RATE)]
            
            # Write audio to file
            write(audio_path, RATE, audio_data)
            print(f"Audio saved to {audio_path}")
            
            return audio_path
        
        except Exception as recording_error:
            logger.error(f"Recording error: {recording_error}")
            print(f"Fatal Error in Audio Recording: {recording_error}")
            return None

    def audio_to_spectrogram(self, audio_path):
        """
        Convert audio to spectrogram with robust multi-channel support
        """
        try:
            sample_rate, samples = wavfile.read(audio_path)
            
            # Robust multi-channel handling
            if len(samples.shape) > 1:
                # If more than 2 channels, reduce to stereo or mono
                if samples.shape[1] > 2:
                    logger.warning(f"Detected {samples.shape[1]} channels. Reducing to stereo.")
                    samples = samples[:, :2]  # Take first two channels
                
                # Average channels if more than one
                if samples.shape[1] > 1:
                    samples = np.mean(samples, axis=1)
            
            spectrogram_path = os.path.join(
                SAVE_FOLDER, 
                f"BeemoDosSpectrogram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            
            plt.figure(figsize=(10, 6))
            plt.specgram(samples, Fs=sample_rate, NFFT=1024, noverlap=512, cmap='magma')
            plt.title(f'Spectrogram ({sample_rate} Hz, {len(samples)} samples)')
            plt.xlabel('Time [s]')
            plt.ylabel('Frequency [Hz]')
            plt.axis('on')
            plt.tight_layout()
            plt.savefig(spectrogram_path)
            plt.close()
            
            return spectrogram_path
        except Exception as e:
            logger.error(f"Spectrogram generation error: {e}")
            return None

    def analyze_audio_frequencies(self, audio_path):
        """
        Analyze audio frequencies with improved multi-channel support
        """
        try:
            sample_rate, samples = wavfile.read(audio_path)
            
            # Handle multi-channel audio by averaging channels
            if len(samples.shape) > 1:
                samples = np.mean(samples, axis=1)
            
            # Perform FFT
            fft_data = np.fft.fft(samples)
            freqs = np.fft.fftfreq(len(fft_data), 1.0 / sample_rate)
            
            # Filter out low-frequency noise
            mask = np.abs(freqs) >= MIN_FREQUENCY
            filtered_freqs = freqs[mask]
            filtered_fft = np.abs(fft_data[mask])
            
            # Compute frequency statistics
            peak_freq = filtered_freqs[np.argmax(filtered_fft)]
            avg_freq = np.mean(np.abs(filtered_freqs))
            
            # Compute additional channel-aware statistics
            rms_amplitude = np.sqrt(np.mean(samples**2))
            
            # Classify activity level
            activity_level = self._classify_activity(avg_freq, rms_amplitude)
            
            return {
                'peak_frequency': peak_freq,
                'average_frequency': avg_freq,
                'rms_amplitude': rms_amplitude,
                'activity_level': activity_level,
                'channels': samples.shape[1] if len(samples.shape) > 1 else 1
            }
        except Exception as e:
            logger.error(f"Frequency analysis error: {e}")
            return None

    def _classify_activity(self, avg_freq, rms_amplitude):
        """
        Enhanced activity classification considering both frequency and amplitude
        """
        # Frequency-based classification
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
            return f"Very {base_level} Activity"
        elif 0.1 <= rms_amplitude < 0.3:
            return f"{base_level} Activity"
        elif 0.3 <= rms_amplitude < 0.6:
            return f"Intense {base_level} Activity"
        else:
            return f"Extremely {base_level} Activity"

    def log_to_sheets(self, analysis_data):
        """
        Log audio analysis data to Google Sheets
        """
        if not self.sheet_service or not analysis_data:
            return False
        
        try:
            now = datetime.now()
            row = [
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                str(round(analysis_data.get('average_frequency', 0), 2)),
                str(round(analysis_data.get('peak_frequency', 0), 2)),
                analysis_data.get('activity_level', 'Unknown')
            ]
            
            body = {'values': [row]}
            self.sheet_service.values().append(
                spreadsheetId=self.spreadsheet_id,
                range="Sheet1!A:E",
                valueInputOption="RAW",
                body=body
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Google Sheets logging error: {e}")
            return False

    async def process_audio(self, bot=None, channel_id=None, duration=DURATION):
        """
        Complete audio processing workflow
        """
        try:
            # Record audio
            audio_path = self.record_audio(duration=duration)
            if not audio_path:
                raise ValueError("Audio recording failed")
            
            # Generate spectrogram
            spectrogram_path = self.audio_to_spectrogram(audio_path)
            
            # Analyze frequencies
            analysis = self.analyze_audio_frequencies(audio_path)
            
            # Log to Google Sheets
            self.log_to_sheets(analysis)
            
            # Send report to Discord (if bot and channel provided)
            if bot and channel_id and analysis:
                message = f"🎵 Audio Analysis Report 🎵\n"
                message += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                message += f"Peak Frequency: {round(analysis['peak_frequency'], 2)} Hz\n"
                message += f"Average Frequency: {round(analysis['average_frequency'], 2)} Hz\n"
                message += f"Activity Level: {analysis['activity_level']}\n"
                
                await bot.get_channel(channel_id).send(message)
                if spectrogram_path:
                    await bot.get_channel(channel_id).send(file=discord.File(spectrogram_path))
            
            return analysis
        
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            if bot and channel_id:
                await bot.get_channel(channel_id).send(f"Error in audio processing: {e}")
            return None

def main():
    """
    Utility method to list and help identify audio devices
    """
    processor = BeemoAudioProcessor()
    
    # List all audio devices with comprehensive details
    device_inventory = processor.list_audio_devices()
    
    print("\n=== DEVICE SELECTION HELP ===")
    print("To select a specific device, use its index when calling select_audio_device()")
    print("Example: processor.select_audio_device(desired_index)")
    
    print("\nQuick Tips for Identifying Your USB Sound Adapter:")
    print("1. Look for device names containing 'USB', 'Adapter', or your device brand")
    print("2. Check the max input channels")
    print("3. Note the host API")

if __name__ == "__main__":
    main()