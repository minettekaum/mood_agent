# Building an AI-Powered WhatsApp Mood Tracking Agent

In this tutorial, we'll build a WhatsApp agent that helps users track their mood by collecting sleep quality and stress level ratings. The agent uses Oura Ring data, OpenAI's API, and Twilio's WhatsApp API to create an interactive and personalized health tracking experience.

## Prerequisites

- Python 3.7+
- A Twilio account (sign up at [twilio.com](https://www.twilio.com))
- OpenAI API key
- Oura Ring account and API token
- ngrok for local development

## Setting Up the Environment

1. First, create a new directory for your project and set up a virtual environment:
```bash
mkdir mood_agent
cd mood_agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install the required packages:
```bash
pip install twilio python-dotenv requests openai
```

3. Create a `.env` file with your credentials:
```
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
WHATSAPP_TO_NUMBER=your_whatsapp_number_here
OPENAI_API_KEY=your_openai_api_key_here
OURA_TOKEN=your_oura_token_here
```

## 1. Fetching Health Data from Oura Ring

The first component of our system fetches health data from the Oura Ring API. This includes sleep, readiness, activity, and workout data from the past 4 days.

### Oura Data Fetcher (`fetch_oura_data.py`)

```python
from dotenv import load_dotenv
import os
import requests 
from datetime import datetime, timedelta

load_dotenv('.env')

def get_date_range():
    today = datetime.now().date()
    start_date = today - timedelta(days=4)
    return {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': today.strftime('%Y-%m-%d')
    }

def fetch_data(url):
    date_range = get_date_range()
    headers = {'Authorization': f'Bearer {os.getenv("TOKEN")}'}
    response = requests.request('GET', url, headers=headers, params=date_range)
    return response.json()

def get_all_oura_data():
    readiness_url = 'https://api.ouraring.com/v2/usercollection/daily_readiness'
    sleep_url = 'https://api.ouraring.com/v2/usercollection/daily_sleep'
    activity_url = 'https://api.ouraring.com/v2/usercollection/daily_activity'
    workout_url = 'https://api.ouraring.com/v2/usercollection/workout'
    
    return {
        "sleep": fetch_data(sleep_url),
        "readiness": fetch_data(readiness_url),
        "activity": fetch_data(activity_url),
        "workout": fetch_data(workout_url)
    }
```

This module:
- Fetches the last 4 days of health data
- Includes sleep, readiness, activity, and workout metrics
- Uses the Oura Ring API v2
- Handles authentication and date range management

## 2. AI-Powered Health Analysis

The second component processes the health data and user input using OpenAI's API to generate personalized insights.

### AI Model (`openai_model.py`)

```python
from dotenv import load_dotenv
import os
from openai import OpenAI
from fetch_oura_data import get_all_oura_data

load_dotenv('.env')

client = OpenAI(api_key=os.getenv("OPENAI"))

def generate_health_insights(oura_data, sleep_rating, stress_level):
    prompt = f"""
You are a helpful health coach writing personalized daily messages based on the following user data from the last 4 days:

- Sleep Data: {oura_data['sleep']}
- Readiness Data: {oura_data['readiness']}
- Activity Data: {oura_data['activity']}
- Workout Data: {oura_data['workout']}
- Today's Sleep Rating: {sleep_rating}/100
- Today's Stress Level: {stress_level}/100

Analyze the trends and provide personalized recommendations.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a health coach who provides motivational advice based on the user's data trends."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating insights: {e}"

def process_user_data(sleep_rating, stress_level):
    oura_data = get_all_oura_data()
    return generate_health_insights(oura_data, sleep_rating, stress_level)
```

This module:
- Takes user's sleep and stress ratings
- Combines them with Oura Ring data
- Uses GPT-4 to generate personalized health insights
- Provides actionable recommendations

## 3. WhatsApp Interface

The final component creates a WhatsApp interface for users to interact with the system.

### WhatsApp Handler (`whatsapp.py`)

```python
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

# Initialize Twilio client
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
to_number = os.getenv('WHATSAPP_TO_NUMBER')
twilio_client = Client(account_sid, auth_token)

user_responses = {
    "sleep_rating": None,
    "stress_level": None
}

def send_whatsapp_message(message):
    message = twilio_client.messages.create(
        from_='whatsapp:+14155238886',
        body=message,
        to=f'whatsapp:{to_number}'
    )
    time.sleep(2)
    message = twilio_client.messages(message.sid).fetch()
    return True

def process_message(message):
    if not message:
        if user_responses["sleep_rating"] is None:
            return "Please rate your sleep from 1-100 (1 = barely slept, 100 = slept better than sleeping beauty)"
        else:
            return "Please rate your stress level from 1-100 (1 = totally relaxed, 100 = being chased by a lion)"
    
    rating = int(message)
    if 1 <= rating <= 100:
        if user_responses["sleep_rating"] is None:
            user_responses["sleep_rating"] = rating
            return f"Thanks for your sleep rating of {rating}! How stressed do you feel today? (1-100, 1 = totally relaxed, 100 = being chased by a lion)"
        else:
            user_responses["stress_level"] = rating
            return process_user_data(user_responses["sleep_rating"], rating)
    
    if user_responses["sleep_rating"] is None:
        return "Please rate your sleep from 1-100 (1 = barely slept, 100 = slept better than sleeping beauty)"
    else:
        return "Please rate your stress level from 1-100 (1 = totally relaxed, 100 = being chased by a lion)"

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
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

def start_server():
    server = HTTPServer(('0.0.0.0', 5001), WebhookHandler)
    server.serve_forever()

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
```

This module:
- Handles WhatsApp communication via Twilio
- Manages the conversation flow
- Collects user ratings
- Integrates with the AI analysis

## Setting Up Twilio WhatsApp Sandbox

1. Go to your Twilio Console
2. Navigate to Messaging → Try it out → Send a WhatsApp message
3. You'll see a sandbox number and a code
4. Send "join <your-sandbox-code>" to the sandbox number from your WhatsApp
5. Note down the sandbox number for use in the code

## Running the Agent

1. Start ngrok to expose your local server:
```bash
ngrok http 5001
```

2. Copy the ngrok URL (e.g., https://xxxx-xx-xx-xxx-xx.ngrok-free.app)

3. In your Twilio Console:
   - Go to Messaging → Try it out → Send a WhatsApp message
   - Set the webhook URL to your ngrok URL
   - Make sure the HTTP method is set to POST

4. Run your Python script:
```bash
python whatsapp.py
```

## How It Works

1. The system starts by fetching the last 4 days of health data from Oura Ring
2. The WhatsApp agent sends an initial message asking about sleep quality
3. When the user responds with a number between 1-100:
   - If it's the first response, it's stored as the sleep rating
   - If it's the second response, it's stored as the stress level
4. The AI processes the responses along with Oura Ring data
5. Personalized insights and recommendations are sent back to the user

## Customization Ideas

1. Add more health metrics from Oura Ring
2. Implement data storage to track trends over time
3. Add visualization of health trends
4. Integrate with other health tracking APIs
5. Add more sophisticated AI analysis
6. Create personalized wellness plans
7. Add natural language processing for free-form responses

## Troubleshooting

Common issues and solutions:

1. **Oura Ring API issues**:
   - Verify your Oura token is correct
   - Check API rate limits
   - Ensure proper date formatting

2. **AI processing issues**:
   - Verify your OpenAI API key is correct
   - Check the API rate limits
   - Ensure proper error handling

3. **Message not received**: 
   - Check if you've joined the WhatsApp sandbox
   - Verify your phone number format in .env
   - Ensure Twilio credentials are correct

4. **Webhook not responding**:
   - Verify ngrok is running
   - Check if the webhook URL is correctly set in Twilio
   - Ensure the server is running on port 5001

## Conclusion

This tutorial showed you how to create an intelligent health tracking agent that combines:
- Oura Ring health data
- AI-powered analysis
- WhatsApp communication

The system demonstrates:
- Integration with multiple APIs
- AI-powered response processing
- Real-time health tracking
- Personalized insights generation

You can extend this implementation to create more sophisticated health and wellness applications.

## Resources

- [Twilio WhatsApp API Documentation](https://www.twilio.com/docs/whatsapp)
- [Oura Ring API Documentation](https://cloud.ouraring.com/docs)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [ngrok Documentation](https://ngrok.com/docs)
