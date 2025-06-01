"""
Vercel serverless function for Telegram Bot webhook.
Handles incoming messages and integrates with telegram_agent_core.
"""
import os
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import httpx
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from telegram_agent_core import process_telegram_message

# Initialize FastAPI app
app = FastAPI()

# Get environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ALLOWED_USER_ID = os.getenv('ALLOWED_USER_ID')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_telegram_message(chat_id: int, text: str) -> bool:
    """
    Send a message to Telegram chat.
    
    Args:
        chat_id: Telegram chat ID
        text: Message text to send
        
    Returns:
        True if successful, False otherwise
    """
    async with httpx.AsyncClient() as client:
        try:
            # Truncate message if too long
            if len(text) > 4096:
                text = text[:4093] + "..."
            
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                }
            )
            return response.is_success
        except Exception as e:
            print(f"Error sending message: {e}")
            return False


def validate_user(user_id: int) -> bool:
    """
    Validate if the user is allowed to use the bot.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        True if user is allowed, False otherwise
    """
    if not ALLOWED_USER_ID:
        # If no user ID is set, allow all (not recommended for production)
        return True
    
    return str(user_id) == ALLOWED_USER_ID


@app.post("/webhook")
async def webhook(request: Request) -> Response:
    """
    Handle incoming Telegram webhook updates.
    """
    try:
        # Parse the incoming update
        update = await request.json()
        
        # Extract message data
        message = update.get('message', {})
        if not message:
            # Could be an edited message or other update type
            message = update.get('edited_message', {})
            if not message:
                return JSONResponse({"ok": True})
        
        # Extract user and chat information
        user_id = message.get('from', {}).get('id')
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        
        # Validate user
        if not validate_user(user_id):
            # Silent rejection for unauthorized users
            print(f"Unauthorized access attempt from user {user_id}")
            return JSONResponse({"ok": True})
        
        # Process the message if it contains text
        if text and chat_id:
            # Get response from the agent
            response_text = await process_telegram_message(text)
            
            # Send the response back to Telegram
            await send_telegram_message(chat_id, response_text)
        
        return JSONResponse({"ok": True})
        
    except Exception as e:
        print(f"Webhook error: {e}")
        # Return ok to prevent Telegram from retrying
        return JSONResponse({"ok": True})


@app.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring.
    """
    return {
        "status": "healthy",
        "service": "telegram-bot-webhook",
        "bot_configured": bool(BOT_TOKEN),
        "auth_configured": bool(ALLOWED_USER_ID)
    }


@app.get("/webhook")
async def webhook_info() -> Dict[str, Any]:
    """
    Webhook info endpoint.
    """
    return {
        "status": "ready",
        "endpoint": "/webhook",
        "method": "POST"
    }


# For local testing
if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    
    # Load local environment for testing
    load_dotenv('local.env')
    
    # Update globals after loading env
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ALLOWED_USER_ID = os.getenv('ALLOWED_USER_ID')
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
    
    print("Starting local webhook server...")
    print(f"Bot configured: {bool(BOT_TOKEN)}")
    print(f"Auth configured: {bool(ALLOWED_USER_ID)}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)