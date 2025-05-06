from twilio.rest import Client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv('.env')

# Twilio credentials from environment variables
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
to_number = os.getenv('WHATSAPP_TO_NUMBER')  

def send_whatsapp_message(message):
    """Send a WhatsApp message using Twilio"""
    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_='whatsapp:+14155238886',  
            body=message,
            to=f'whatsapp:{to_number}'
        )
        print("WhatsApp message sent successfully!")
        return True
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        return False
