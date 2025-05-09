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
