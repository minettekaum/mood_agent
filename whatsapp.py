from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import threading
import time
from openai_model import process_user_data

# Load environment variables
load_dotenv('.env')

# Twilio credentials from environment variables
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
to_number = os.getenv('WHATSAPP_TO_NUMBER')

twilio_client = Client(account_sid, auth_token)

# Store user's responses
user_responses = {
    "sleep_rating": None,
    "stress_level": None
}

def send_whatsapp_message(message):
    """Send a WhatsApp message using Twilio"""
    try:
        message = twilio_client.messages.create(
            from_='whatsapp:+14155238886',
            body=message,
            to=f'whatsapp:{to_number}'
        )
        print("WhatsApp message sent successfully!")
        return True
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        return False

def process_message(message):
    """Process incoming messages and generate appropriate responses"""
    print(f"\nProcessing message: '{message}'")
    print(f"Current state - Sleep rating: {user_responses['sleep_rating']}, Stress level: {user_responses['stress_level']}")
    
    # Handle empty messages
    if not message:
        print("Received empty message")
        if user_responses["sleep_rating"] is None:
            return "Please rate your sleep from 1-100 (1 = barely slept, 100 = slept better than sleeping beauty)"
        else:
            return "Please rate your stress level from 1-100 (1 = totally relaxed, 100 = being chased by a lion)"
    
    try:
        rating = int(message)
        if 1 <= rating <= 100:
            if user_responses["sleep_rating"] is None:
                # First question (sleep rating)
                print("Storing sleep rating and asking for stress level")
                user_responses["sleep_rating"] = rating
                response = f"Thanks for your sleep rating of {rating}! How stressed do you feel today? (1-100, 1 = totally relaxed, 100 = being chased by a lion)"
                print(f"Sending response: {response}")
                return response
            else:
                # Second question (stress level)
                print("Storing stress level and generating LLM response")
                user_responses["stress_level"] = rating
                # Generate health insights
                response = process_user_data(user_responses["sleep_rating"], rating)
                print(f"Generated health insights: {response}")
                return response
    except ValueError:
        print("Invalid input - not a number")
        pass
    
    # If not a number or out of range, ask for the current question again
    if user_responses["sleep_rating"] is None:
        response = "Please rate your sleep from 1-100 (1 = barely slept, 100 = slept better than sleeping beauty)"
    else:
        response = "Please rate your stress level from 1-100 (1 = totally relaxed, 100 = being chased by a lion)"
    print(f"Sending response: {response}")
    return response

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle incoming POST requests from Twilio"""
        try:
            # Get the raw POST data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Debug raw data
            print("\n=== Incoming Webhook ===")
            print(f"Raw POST data: {post_data.decode('utf-8')}")
            
            # Parse the form data
            form_data = parse_qs(post_data.decode('utf-8'))
            
            # Debug parsed data
            print(f"Parsed form data: {form_data}")
            
            # Get the message the user sent
            incoming_msg = form_data.get('Body', [''])[0].lower()
            print(f"Processing message: {incoming_msg}")
            
            # Process the message
            response_text = process_message(incoming_msg)
            print(f"Generated response: {response_text}")
            
            # Create TwiML response
            resp = MessagingResponse()
            resp.message(response_text)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/xml')
            self.end_headers()
            response_xml = str(resp)
            print(f"Sending TwiML response: {response_xml}")
            self.wfile.write(response_xml.encode())
            print("Response sent successfully")
            
        except Exception as e:
            print(f"Error in webhook handler: {e}")
            import traceback
            print(f"Full error: {traceback.format_exc()}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

def start_server():
    """Start the HTTP server"""
    try:
        server = HTTPServer(('0.0.0.0', 5001), WebhookHandler)
        print("\n=== WhatsApp Webhook Server Started ===")
        print("1. Server running at http://0.0.0.0:5001")
        print("2. Start ngrok with: ngrok http 5001")
        print("3. In Twilio Console:")
        print("   - Go to Messaging → Try it out → Send a WhatsApp message")
        print("   - Find 'Sandbox Settings'")
        print("   - Set 'WHEN A MESSAGE COMES IN' to your webhook URL")
        print("   - Make sure to select HTTP POST as the method")
        print("   (NOT GET or Status callback URL)")
        print("=======================================\n")
        server.serve_forever()
    except Exception as e:
        print(f"Error starting server: {e}")
        print("\nTroubleshooting steps:")
        print("1. Check if another instance is running:")
        print("   lsof -i :5001")
        print("2. Kill the process if needed:")
        print("   kill -9 <PID>")
        print("3. Or try running on a different port:")
        print("   python whatsapp.py --port 5002")

def send_initial_question():
    """Send the initial question to the user"""
    time.sleep(2)  # Wait for server to start
    initial_message = "How well did you sleep last night? (1-100, 1 = barely slept, 100 = slept better than sleeping beauty)"
    print(f"\nSending initial question: {initial_message}")
    if send_whatsapp_message(initial_message):
        print("Initial question sent successfully!")
    else:
        print("Failed to send initial question")

if __name__ == "__main__":
    # Start the server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Send the initial question
    send_initial_question()
    
    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server stopped")

