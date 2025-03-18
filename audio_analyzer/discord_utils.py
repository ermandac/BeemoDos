import discord
import asyncio
import logging
import os
from django.conf import settings

logger = logging.getLogger('audio_analyzer.discord_utils')

async def send_discord_message_async(message, image_path=None):
    """
    Send a message to a Discord channel without running a full bot.
    This function should be called from an async context or with asyncio.run()
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
                        await client.close()
                        return
                
                logger.info(f'Found channel: {channel.name}')
                
                # Send the message
                logger.info(f'Sending message: {message[:50]}...')
                await channel.send(message)
                
                # Send the image if provided
                if image_path and os.path.exists(image_path):
                    logger.info(f'Sending image: {image_path}')
                    await channel.send(file=discord.File(image_path))
                
                message_sent = True
                logger.info('Message sent successfully')
            except Exception as e:
                logger.error(f'Error sending message to Discord: {e}')
            finally:
                # Close the connection
                logger.info('Closing Discord connection')
                await client.close()
        
        # Connect to Discord
        logger.info(f'Starting Discord client with token starting with {token[:5]}...')
        await client.start(token)
        logger.info(f'Discord client stopped, message_sent={message_sent}')
        return message_sent
        
    except Exception as e:
        logger.error(f'Error in Discord connection: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return False

def send_discord_message(message, image_path=None):
    """
    Synchronous wrapper around send_discord_message_async for use in Django views
    """
    try:
        # Log the attempt
        logger.info(f"Attempting to send Discord message")
        logger.info(f"Discord token length: {len(settings.DISCORD_BOT_TOKEN) if settings.DISCORD_BOT_TOKEN else 0}")
        logger.info(f"Discord channel ID: {settings.DISCORD_CHANNEL_ID}")
        
        if not settings.DISCORD_BOT_TOKEN or settings.DISCORD_CHANNEL_ID == 0:
            logger.error("Discord configuration missing. Check DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID in settings.")
            return False
        
        if image_path:
            logger.info(f"Image path provided: {image_path}")
            logger.info(f"Image exists: {os.path.exists(image_path)}")
        
        # Run the async function in a new event loop
        return asyncio.run(send_discord_message_async(message, image_path))
    except Exception as e:
        logger.error(f"Error in send_discord_message: {e}")
        return False