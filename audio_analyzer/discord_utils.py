import discord
import asyncio
import logging
import os
import json
from django.conf import settings

logger = logging.getLogger('audio_analyzer.discord_utils')

def format_discord_notification(prediction_data, frequency_data=None):
    """
    Format a detailed Discord notification with prediction and frequency data
    
    :param prediction_data: Dictionary containing prediction information
    :param frequency_data: Dictionary containing frequency analysis information
    :return: Formatted notification message
    """
    # Prepare base prediction information
    notification = {
        "Prediction": {
            "Model": prediction_data.get('model', 'Unknown'),
            "Filename": prediction_data.get('filename', 'N/A'),
            "Result": prediction_data.get('prediction', 'N/A'),
            "Confidence": f"{prediction_data.get('confidence', 0):.2%}"
        }
    }
    
    # Add frequency data if available
    if frequency_data:
        notification["Frequency Analysis"] = {
            "Dominant Frequency": frequency_data.get('dominant_frequency', 'N/A'),
            "Frequency Range": frequency_data.get('frequency_range', 'N/A'),
            "Spectral Centroid": frequency_data.get('spectral_centroid', 'N/A'),
            "Spectral Bandwidth": frequency_data.get('spectral_bandwidth', 'N/A'),
            "Spectral Rolloff": frequency_data.get('spectral_rolloff', 'N/A')
        }
    
    # Convert to formatted JSON-like string
    formatted_message = "🐝 BeemoDos Analysis Report 🐝\n"
    formatted_message += "```json\n"
    formatted_message += json.dumps(notification, indent=2)
    formatted_message += "\n```"
    
    return formatted_message

async def send_discord_message_async(message, image_path=None, prediction_data=None, frequency_data=None):
    """
    Send a message to a Discord channel without running a full bot.
    This function should be called from an async context or with asyncio.run()
    
    :param message: Optional custom message
    :param image_path: Optional path to an image to attach
    :param prediction_data: Optional prediction data for detailed notification
    :param frequency_data: Optional frequency analysis data
    """
    try:
        # Get Discord configuration from settings
        token = settings.DISCORD_BOT_TOKEN
        channel_id = settings.DISCORD_CHANNEL_ID
        
        logger.info(f"Discord async function called with token length {len(token) if token else 0} and channel ID {channel_id}")
        
        if not token or channel_id == 0:
            logger.error("Discord configuration missing. Set DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID in settings.")
            return False
        
        # Create a Discord client
        logger.info("Creating Discord client with intents")
        intents = discord.Intents.default()
        intents.message_content = True  # Explicitly enable message content intent
        client = discord.Client(intents=intents)
        
        # Flag to track successful message sending
        message_sent = False
        
        # Define what happens when the client is ready
        @client.event
        async def on_ready():
            nonlocal message_sent
            logger.info(f'Connected to Discord as {client.user}')
            
            try:
                # Get the channel
                channel = client.get_channel(channel_id)
                if not channel:
                    logger.error(f'Could not find channel with ID {channel_id}')
                    # Try to fetch the channel directly
                    try:
                        logger.info(f'Attempting to fetch channel directly with ID {channel_id}')
                        channel = await client.fetch_channel(channel_id)
                        logger.info(f'Successfully fetched channel: {channel.name}')
                    except Exception as fetch_error:
                        logger.error(f'Error fetching channel: {fetch_error}')
                        return
                
                # Prepare the message
                if prediction_data:
                    # Use formatted notification if prediction data is provided
                    discord_message = format_discord_notification(
                        prediction_data, 
                        frequency_data
                    )
                else:
                    # Use default or custom message
                    discord_message = message or "No message provided"
                
                # Send the message
                await channel.send(discord_message)
                
                # Send image if provided
                if image_path and os.path.exists(image_path):
                    await channel.send(file=discord.File(image_path))
                
                message_sent = True
                logger.info("Discord message sent successfully")
            
            except Exception as e:
                logger.error(f"Error sending Discord message: {e}")
            finally:
                await client.close()
        
        # Run the client
        await client.start(token)
        
        return message_sent
    
    except Exception as e:
        logger.error(f"Unexpected error in send_discord_message_async: {e}")
        return False

def send_discord_message(message, image_path=None, prediction_data=None, frequency_data=None):
    """
    Synchronous wrapper for async Discord message sending
    
    :param message: Optional custom message
    :param image_path: Optional path to an image to attach
    :param prediction_data: Optional prediction data for detailed notification
    :param frequency_data: Optional frequency analysis data
    :return: Boolean indicating message sending success
    """
    try:
        return asyncio.run(
            send_discord_message_async(
                message, 
                image_path, 
                prediction_data, 
                frequency_data
            )
        )
    except Exception as e:
        logger.error(f"Error running async Discord message: {e}")
        return False