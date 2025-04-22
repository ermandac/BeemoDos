import logging
import socket
import threading
import os
from django.conf import settings
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import BlynkLib, with graceful fallback if not installed
try:
    import BlynkLib
    BLYNK_AVAILABLE = True
except ImportError:
    logger.warning("BlynkLib not installed. Blynk notifications will be disabled.")
    BLYNK_AVAILABLE = False

# Blynk authentication token - should be moved to settings.py
BLYNK_AUTH = getattr(settings, 'BLYNK_AUTH', 'G_3XV39JoVt7eCZnkqwdKP0dlvflgKHG')  # Default from old Beemo
BLYNK_SERVER = getattr(settings, 'BLYNK_SERVER', 'sgp1.blynk.cloud')
BLYNK_PORT = getattr(settings, 'BLYNK_PORT', 443)

# Global Blynk instance
blynk = None
blynk_thread = None

# Global flag to track initialization
_BLYNK_INITIALIZED = False

def initialize_blynk():
    """Initialize the Blynk connection if available"""
    global blynk, blynk_thread, BLYNK_AVAILABLE, _BLYNK_INITIALIZED
    
    # Prevent multiple initializations
    if _BLYNK_INITIALIZED:
        logger.debug("Blynk already initialized. Skipping re-initialization.")
        return True
    
    if not BLYNK_AVAILABLE:
        logger.warning("Blynk is not available.")
        return False
        
    try:
        # Fetch Blynk configuration from environment or settings
        blynk_auth = os.environ.get('BLYNK_AUTH', BLYNK_AUTH)
        
        # Validate authentication token
        if not blynk_auth or len(blynk_auth) < 10:
            logger.error("Invalid Blynk authentication token")
            BLYNK_AVAILABLE = False
            return False
        
        # Initialize Blynk with error handling
        blynk = BlynkLib.Blynk(
            blynk_auth, 
            server=BLYNK_SERVER, 
            port=BLYNK_PORT
        )
        
        # Add event handling for different bee-related virtual pins
        @blynk.VIRTUAL_WRITE(0)  # General notifications
        def on_general_notification(value):
            logger.info(f"Received general notification: {value}")
        
        @blynk.VIRTUAL_WRITE(6)  # BNQ (Bee Number) specific pin
        def on_bnq_notification(value):
            logger.info(f"Received BNQ notification on V6: {value}")
        
        @blynk.VIRTUAL_WRITE(4)  # QNQ (Queen Number) specific pin
        def on_qnq_notification(value):
            logger.info(f"Received QNQ notification on V4: {value}")
        
        @blynk.VIRTUAL_WRITE(5)  # TOOT specific pin
        def on_toot_notification(value):
            logger.info(f"Received TOOT notification on V5: {value}")
        
        # Start Blynk thread if not already running
        if blynk_thread is None or not blynk_thread.is_alive():
            blynk_thread = threading.Thread(target=run_blynk_thread, daemon=True)
            blynk_thread.start()
        
        # Mark as initialized to prevent duplicate initializations
        _BLYNK_INITIALIZED = True
        
        logger.info("Blynk connection initialized successfully")
        return True
    except (socket.gaierror, ValueError) as e:
        logger.error(f"Network error during Blynk initialization: {e}")
        BLYNK_AVAILABLE = False
        return False
    except Exception as e:
        # Log the full traceback for debugging
        import traceback
        logger.error(f"Unexpected error during Blynk initialization: {e}")
        logger.error(traceback.format_exc())
        BLYNK_AVAILABLE = False
        return False

def safe_initialize_blynk():
    """Safely initialize Blynk, ensuring it's only done once"""
    if not _BLYNK_INITIALIZED:
        initialize_blynk()

def send_string_to_blynk(pin, string):
    """Send a string to a virtual pin"""
    if not BLYNK_AVAILABLE or blynk is None:
        logger.warning(f"Blynk not available. Cannot send '{string}' to pin V{pin}")
        return False
        
    try:
        blynk.virtual_write(pin, string)
        logger.info(f"Sent '{string}' to virtual pin V{pin}")
        return True
    except Exception as e:
        logger.error(f"Failed to send data to Blynk: {e}")
        return False

def trigger_notification(event_name, event_code, description, additional_data=None):
    """Trigger a Blynk notification"""
    if not BLYNK_AVAILABLE or blynk is None:
        logger.warning(f"Blynk not available. Cannot send notification: {event_name}")
        return False
        
    try:
        logger.info(f"Triggering Blynk notification: {event_name} - {description}")
        
        # Prepare the notification message
        full_message = f"{event_name}: {description}"
        
        # If additional data is provided, append it to the message
        if additional_data is not None:
            # Convert additional data to a formatted string
            additional_info = " | ".join([f"{k}: {v}" for k, v in additional_data.items()])
            full_message += f" | {additional_info}"
        
        # Use Blynk's native notification method
        # Virtual pin V0 is typically used for notifications in Blynk
        blynk.virtual_write(0, full_message)
        
        # Optional: Send push notification
        try:
            blynk.notify(full_message)
        except Exception as notify_error:
            logger.warning(f"Could not send push notification: {notify_error}")
        
        # Optional: log event if supported
        try:
            blynk.log_event(event_code, full_message)
        except Exception as log_error:
            logger.warning(f"Could not log event: {log_error}")
        
        logger.info(f"Blynk notification triggered: {event_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to trigger Blynk notification: {e}")
        return False

def run_blynk_thread():
    """Run Blynk in a loop"""
    global blynk
    
    if not BLYNK_AVAILABLE or blynk is None:
        logger.warning("Blynk not available. Thread exiting.")
        return
        
    logger.info("Starting Blynk thread")
    while True:
        try:
            blynk.run()
        except Exception as e:
            logger.error(f"Error in Blynk thread: {e}")
            # Try to reconnect
            try:
                initialize_blynk()
            except:
                pass

def start_blynk_service():
    """Start the Blynk service in a background thread"""
    global blynk_thread
    
    if not initialize_blynk():
        logger.warning("Could not initialize Blynk. Service not started.")
        return False
        
    if blynk_thread is not None and blynk_thread.is_alive():
        logger.info("Blynk thread is already running")
        return True
        
    blynk_thread = threading.Thread(target=run_blynk_thread, daemon=True)
    blynk_thread.start()
    logger.info("Blynk service started in background thread")
    return True

def trigger_bee_event(bnb_result, qnq_result, toot_result=None, confidence_levels=None):
    """
    Comprehensive event triggering for bee behavior detection
    
    Args:
        bnb_result (str): Bee presence detection result
        qnq_result (str): Queen bee detection result
        toot_result (str, optional): Queen tooting detection result
        confidence_levels (dict, optional): Confidence levels for each detection
    
    Returns:
        dict: Summary of triggered notifications
    """
    # Log input parameters for traceability
    logger.info(f"Triggering bee event with parameters:")
    logger.info(f"BNB Result: {bnb_result}")
    logger.info(f"QNQ Result: {qnq_result}")
    logger.info(f"TOOT Result: {toot_result}")
    logger.info(f"Confidence Levels: {confidence_levels}")

    # Default confidence levels if not provided
    if confidence_levels is None:
        confidence_levels = {
            'BNB': 0.0,
            'QNQ': 0.0,
            'TOOT': 0.0
        }
    
    event_summary = {
        'bnb_notification': False,
        'qnq_notification': False,
        'toot_notification': False,
        'timestamp': datetime.now().isoformat()
    }
    
    # BNB (Bee Presence) Notifications
    try:
        if bnb_result == "No Bees Detected":
            logger.debug("Preparing No Bees Detected notification")
            notification_result = trigger_notification(
                event_name="Bee Absence Alert",
                event_code="NO_BEES_DETECTED",
                description="No buzzing detected inside the hive. Inspect immediately.",
                additional_data={
                    'Detection Type': 'BNB',
                    'Result': bnb_result,
                    'Confidence': f"{confidence_levels.get('BNB', 0.0):.2f}",
                    'Severity': 'high'
                }
            )
            event_summary['bnb_notification'] = notification_result
            logger.info(f"No Bees Detected notification sent: {notification_result}")
        
        elif bnb_result == "Bees Detected":
            logger.debug("Preparing Bees Detected notification")
            notification_result = trigger_notification(
                event_name="Hive Activity Confirmed",
                event_code="BEES_DETECTED",
                description="Buzzing activity detected. Hive appears active.",
                additional_data={
                    'Detection Type': 'BNB',
                    'Result': bnb_result,
                    'Confidence': f"{confidence_levels.get('BNB', 0.0):.2f}",
                    'Severity': 'normal'
                }
            )
            event_summary['bnb_notification'] = notification_result
            logger.info(f"Bees Detected notification sent: {notification_result}")
    
    except Exception as e:
        logger.error(f"Error in BNB event notification: {e}", exc_info=True)
        event_summary['bnb_error'] = str(e)
    
    # QNQ (Queen Presence) Notifications
    try:
        if qnq_result == "No Queen Detected":
            logger.debug("Preparing No Queen Detected notification")
            notification_result = trigger_notification(
                event_name="Queen Bee Absence Alert",
                event_code="NO_QUEEN_DETECTED",
                description="Chaotic buzzing suggests queen may be absent. Prepare for intervention.",
                additional_data={
                    'Detection Type': 'QNQ',
                    'Result': qnq_result,
                    'Confidence': f"{confidence_levels.get('QNQ', 0.0):.2f}",
                    'Severity': 'critical'
                }
            )
            event_summary['qnq_notification'] = notification_result
            logger.info(f"No Queen Detected notification sent: {notification_result}")
        
        elif qnq_result == "Queen Detected":
            logger.debug("Preparing Queen Detected notification")
            notification_result = trigger_notification(
                event_name="Queen Bee Presence Confirmed",
                event_code="QUEEN_DETECTED",
                description="Calm buzzing indicates queen is present. Hive appears stable.",
                additional_data={
                    'Detection Type': 'QNQ',
                    'Result': qnq_result,
                    'Confidence': f"{confidence_levels.get('QNQ', 0.0):.2f}",
                    'Severity': 'normal'
                }
            )
            event_summary['qnq_notification'] = notification_result
            logger.info(f"Queen Detected notification sent: {notification_result}")
    
    except Exception as e:
        logger.error(f"Error in QNQ event notification: {e}", exc_info=True)
        event_summary['qnq_error'] = str(e)
    
    # TOOT (Queen Tooting) Notifications
    try:
        if toot_result == "Tooting Detected":
            logger.debug("Preparing Tooting Detected notification")
            notification_result = trigger_notification(
                event_name="Queen Tooting Alert",
                event_code="QUEEN_TOOTING",
                description="Queen tooting sound detected. Potential queen emergence or competition.",
                additional_data={
                    'Detection Type': 'TOOT',
                    'Result': toot_result,
                    'Confidence': f"{confidence_levels.get('TOOT', 0.0):.2f}",
                    'Severity': 'high'
                }
            )
            event_summary['toot_notification'] = notification_result
            logger.info(f"Tooting Detected notification sent: {notification_result}")
    
    except Exception as e:
        logger.error(f"Error in TOOT event notification: {e}", exc_info=True)
        event_summary['toot_error'] = str(e)
    
    # Log comprehensive event summary
    logger.info(f"Bee Event Notification Summary: {json.dumps(event_summary, indent=2)}")
    
    return event_summary

def test_bee_event_notifications():
    """
    Test function to simulate different bee detection scenarios
    
    Returns:
        list: Results of test notification scenarios
    """
    logger.info("Starting Blynk notification test scenarios")
    
    test_scenarios = [
        {
            'bnb': 'No Bees Detected', 
            'qnq': 'No Queen Detected', 
            'toot': None,
            'confidence': {'BNB': 0.7, 'QNQ': 0.6, 'TOOT': 0.0}
        },
        {
            'bnb': 'Bees Detected', 
            'qnq': 'Queen Detected', 
            'toot': 'Tooting Detected',
            'confidence': {'BNB': 0.9, 'QNQ': 0.8, 'TOOT': 0.7}
        }
    ]
    
    results = []
    for scenario in test_scenarios:
        logger.info(f"Running test scenario: {scenario}")
        result = trigger_bee_event(
            scenario['bnb'], 
            scenario['qnq'], 
            scenario['toot'],
            scenario['confidence']
        )
        results.append(result)
        logger.info(f"Test scenario result: {result}")
    
    logger.info("Completed Blynk notification test scenarios")
    return results

# Initialize Blynk when the module is imported
safe_initialize_blynk()
