from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
from openai import OpenAI
from fetch_data import fetch_data_sleep_readiness_workout, fetch_data_activity
import socket
import argparse

# Load environment variables
load_dotenv('.env')

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI"))

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

def get_oura_data():
    """Get the latest data from Oura Ring API"""
    readiness_url = 'https://api.ouraring.com/v2/usercollection/daily_readiness'
    sleep_url = 'https://api.ouraring.com/v2/usercollection/daily_sleep'
    activity_url = 'https://api.ouraring.com/v2/usercollection/daily_activity'
    workout_url = 'https://api.ouraring.com/v2/usercollection/daily_workout'
    
    readiness = fetch_data_sleep_readiness_workout(readiness_url)
    sleep = fetch_data_sleep_readiness_workout(sleep_url)
    workout = fetch_data_sleep_readiness_workout(workout_url)
    activity = fetch_data_activity(activity_url)
    
    return {
        "sleep": sleep,
        "readiness": readiness,
        "activity": activity,
        "workout": workout,
        "subjective_sleep": user_responses["sleep_rating"],
        "stress_level": user_responses["stress_level"]
    }

def generate_llm_response(data):
    """Generate response using GPT-4"""
    prompt = f"""
You are a helpful health coach writing personalized daily messages based on the following user data from the last 4 days:

- Sleep Data: {data['sleep']}
- Readiness Data: {data['readiness']}
- Activity Data: {data['activity']}
- Workout Data: {data['workout']}
- Today's Sleep Rating: {data['subjective_sleep']}/100 (100 = slept better than sleeping beauty, 1 = barely slept)
- Today's Stress Level: {data['stress_level']}/100 (100 = being chased by a lion, 1 = totally relaxed)

Analyze the trends from the 4-day data. Write 3 practical actions for today and end with a motivational message to help the user achieve their health goals.
Focus on improvements or changes needed based on the data trends. Add emojis to make the message more engaging. The message cannot be longer than 1500 characters.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a health coach who provides motivational advice based on data trends."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {e}"

class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - return a helpful message"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"This webhook only accepts POST requests from Twilio. Please configure your Twilio webhook to use HTTP POST.")

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
            from urllib.parse import parse_qs
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
                # Get Oura data and generate LLM response
                oura_data = get_oura_data()
                response = generate_llm_response(oura_data)
                print(f"Generated LLM response: {response}")
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

def verify_ngrok_setup():
    """Verify ngrok is running and show the URL"""
    try:
        import requests
        response = requests.get('http://localhost:4040/api/tunnels')
        if response.status_code == 200:
            tunnels = response.json()['tunnels']
            for tunnel in tunnels:
                if tunnel['proto'] == 'https':
                    print("\n=== Your ngrok URL ===")
                    print(f"HTTPS URL: {tunnel['public_url']}")
                    print(f"Webhook URL: {tunnel['public_url']}/webhook")
                    print("=====================\n")
                    return tunnel['public_url']
        print("Could not find ngrok URL. Make sure ngrok is running with: ngrok http 5000")
        return None
    except:
        print("Could not connect to ngrok. Make sure ngrok is running with: ngrok http 5000")
        return None

def find_available_port(start_port=5000, max_port=5010):
    """Find an available port to use"""
    for port in range(start_port, max_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available ports found between {start_port} and {max_port}")

def start_server():
    """Start the HTTP server"""
    try:
        # Find an available port
        port = find_available_port()
        server = HTTPServer(('0.0.0.0', port), WebhookHandler)
        print("\n=== WhatsApp Webhook Server Started ===")
        print(f"1. Server running at http://0.0.0.0:{port}")
        print(f"2. Start ngrok with: ngrok http {port}")
        print("3. In Twilio Console:")
        print("   - Go to Messaging → Try it out → Send a WhatsApp message")
        print("   - Find 'Sandbox Settings'")
        print("   - Set 'WHEN A MESSAGE COMES IN' to your webhook URL")
        print("   - Make sure to select HTTP POST as the method")
        print("   (NOT GET or Status callback URL)")
        print("=======================================\n")
        
        # Verify ngrok setup
        ngrok_url = verify_ngrok_setup()
        if ngrok_url:
            print("✅ Ngrok is running!")
            print(f"Use this webhook URL in Twilio: {ngrok_url}/webhook")
            print("Remember to set the method to HTTP POST")
        else:
            print("❌ Ngrok is not running. Please start it with: ngrok http {port}")
        
        server.serve_forever()
    except Exception as e:
        print(f"Error starting server: {e}")
        print("\nTroubleshooting steps:")
        print("1. Check if another instance is running:")
        print("   lsof -i :5000")
        print("2. Kill the process if needed:")
        print("   kill -9 <PID>")
        print("3. Or try running on a different port:")
        print("   python whatsapp.py --port 5001")

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
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    args = parser.parse_args()
    
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

