# DeepSeek WhatsApp Bot
# Main application file

from flask import Flask, request
import requests
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# WhatsApp API Configuration
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "deepseek-bot")

def send_whatsapp_message(to, message):
    """Send a text message via WhatsApp Cloud API"""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        logger.error("WhatsApp credentials not configured!")
        return False
    
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            logger.info(f"Message sent successfully to {to}")
            return True
        else:
            logger.error(f"Failed to send message: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def get_deepseek_reply(user_message):
    """Call DeepSeek API and return its response"""
    if not DEEPSEEK_API_KEY:
        return "DeepSeek API key not configured!"
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": user_message}],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
            return "Sorry, I'm having trouble processing your request right now."
    except Exception as e:
        logger.error(f"Error calling DeepSeek: {e}")
        return "Sorry, I encountered an error while processing your message."

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Verification step for WhatsApp webhook
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        logger.info(f"Webhook verification: mode={mode}, token={token}")
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logger.info("Webhook verified successfully!")
            return challenge, 200
        else:
            logger.error("Webhook verification failed!")
            return "Verification failed", 403

    if request.method == "POST":
        data = request.get_json()
        logger.info(f"Received webhook data: {data}")
        
        try:
            # Extract message from webhook data
            entry = data.get("entry", [])
            if entry:
                changes = entry[0].get("changes", [])
                if changes:
                    value = changes[0].get("value", {})
                    messages = value.get("messages", [])
                    
                    if messages:
                        message = messages[0]
                        from_number = message.get("from")
                        message_type = message.get("type")
                        
                        if message_type == "text":
                            user_text = message.get("text", {}).get("body", "")
                            logger.info(f"Received message from {from_number}: {user_text}")
                            
                            # Get AI response
                            ai_response = get_deepseek_reply(user_text)
                            logger.info(f"AI response: {ai_response}")
                            
                            # Send response back
                            send_whatsapp_message(from_number, ai_response)
                        else:
                            logger.info(f"Received non-text message type: {message_type}")
                            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
        
        return "OK", 200

@app.route("/", methods=["GET"])
def home():
    """Simple home page to verify the server is running"""
    return """
    <h1>DeepSeek WhatsApp Bot</h1>
    <p>Bot is running! Webhook endpoint: /webhook</p>
    <p>Make sure to:</p>
    <ul>
        <li>Configure your .env file with proper credentials</li>
        <li>Set up ngrok to expose this server</li>
        <li>Configure WhatsApp webhook URL</li>
    </ul>
    """

def check_configuration():
    """Check if all required environment variables are set"""
    missing_vars = []
    
    if not WHATSAPP_TOKEN:
        missing_vars.append("WHATSAPP_TOKEN")
    if not WHATSAPP_PHONE_ID:
        missing_vars.append("WHATSAPP_PHONE_ID")
    if not DEEPSEEK_API_KEY:
        missing_vars.append("DEEPSEEK_API_KEY")
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please configure your .env file with the required credentials.")
        return False
    
    logger.info("All required environment variables are configured!")
    return True

if __name__ == "__main__":
    print("DeepSeek WhatsApp Bot Starting...")
    
    if not check_configuration():
        print("❌ Configuration incomplete. Please check your .env file.")
        exit(1)
    
    print("✅ Configuration verified!")
    print("🌐 Starting Flask server on http://localhost:5000")
    print("📱 Webhook endpoint: http://localhost:5000/webhook")
    print("🔗 Use ngrok to expose this server: ngrok http 5000")
    print("🤖 Bot is ready!")
    
    app.run(host="0.0.0.0", port=5000, debug=True) 