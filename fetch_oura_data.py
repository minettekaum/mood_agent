from dotenv import load_dotenv
import os
import requests 
from datetime import datetime, timedelta

load_dotenv('.env')

def get_date_range(days_back=4):
    today = datetime.now().date()
    start_date = today - timedelta(days=days_back)
    return {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': today.strftime('%Y-%m-%d')
    }

def fetch_data_sleep_readiness_workout(url):
    date_range = get_date_range()
    headers = {'Authorization': f'Bearer {os.getenv("TOKEN")}'}
    response = requests.request('GET', url, headers=headers, params=date_range)
    return response.json()

def fetch_data_activity(url):
    date_range = get_date_range()
    headers = {'Authorization': f'Bearer {os.getenv("TOKEN")}'}
    response = requests.request('GET', url, headers=headers, params=date_range)
    return response.json()

def get_all_oura_data():
    readiness_url = 'https://api.ouraring.com/v2/usercollection/daily_readiness'
    sleep_url = 'https://api.ouraring.com/v2/usercollection/daily_sleep'
    activity_url = 'https://api.ouraring.com/v2/usercollection/daily_activity'
    workout_url = 'https://api.ouraring.com/v2/usercollection/daily_workout'
    
    return {
        "sleep": fetch_data_sleep_readiness_workout(sleep_url),
        "readiness": fetch_data_sleep_readiness_workout(readiness_url),
        "activity": fetch_data_activity(activity_url),
        "workout": fetch_data_sleep_readiness_workout(workout_url)
    }


    