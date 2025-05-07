from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import threading
import time
from openai_model import process_user_data

load_dotenv('.env')

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
to_number = os.getenv('WHATSAPP_TO_NUMBER')

twilio_client = Client(account_sid, auth_token)

user_responses = {
    "sleep_rating": None,
    "stress_level": None
}

def send_whatsapp_message(message):
    try:
        message = twilio_client.messages.create(
            from_='whatsapp:+14155238886',
            body=message,
            to=f'whatsapp:{to_number}'
        )
        return True
    except Exception as e:
        return False

def process_message(message):
    if not message:
        if user_responses["sleep_rating"] is None:
            return "Please rate your sleep from 1-100 (1 = barely slept, 100 = slept better than sleeping beauty)"
        else:
            return "Please rate your stress level from 1-100 (1 = totally relaxed, 100 = being chased by a lion)"
    
    try:
        rating = int(message)
        if 1 <= rating <= 100:
            if user_responses["sleep_rating"] is None:
                user_responses["sleep_rating"] = rating
                return f"Thanks for your sleep rating of {rating}! How stressed do you feel today? (1-100, 1 = totally relaxed, 100 = being chased by a lion)"
            else:
                user_responses["stress_level"] = rating
                return process_user_data(user_responses["sleep_rating"], rating)
    except ValueError:
        pass
    
    if user_responses["sleep_rating"] is None:
        return "Please rate your sleep from 1-100 (1 = barely slept, 100 = slept better than sleeping beauty)"
    else:
        return "Please rate your stress level from 1-100 (1 = totally relaxed, 100 = being chased by a lion)"

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            form_data = parse_qs(post_data.decode('utf-8'))
            incoming_msg = form_data.get('Body', [''])[0].lower()
            response_text = process_message(incoming_msg)
            
            resp = MessagingResponse()
            resp.message(response_text)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/xml')
            self.end_headers()
            self.wfile.write(str(resp).encode())
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()

def start_server():
    try:
        server = HTTPServer(('0.0.0.0', 5001), WebhookHandler)
        server.serve_forever()
    except Exception as e:
        pass

def send_initial_question():
    time.sleep(2)
    initial_message = "How well did you sleep last night? (1-100, 1 = barely slept, 100 = slept better than sleeping beauty)"
    send_whatsapp_message(initial_message)

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    send_initial_question()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

