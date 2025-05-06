from dotenv import load_dotenv
import os
import requests 
from datetime import datetime, timedelta

today = datetime.now().date()
#yesterday = today - timedelta(days=1)
week_ago = today - timedelta(days=4)
today_str = today.strftime('%Y-%m-%d')
#yesterday_str = yesterday.strftime('%Y-%m-%d')
week_ago_str = week_ago.strftime('%Y-%m-%d')


load_dotenv('.env')


def fetch_data_sleep_readiness_workout(url):
    params={ 
    'start_date': week_ago_str, 
    'end_date': today_str 
    }
    headers = { 
  'Authorization': f'Bearer {os.getenv("TOKEN")}' 
    }
    response = requests.request('GET', url, headers=headers, params=params) 
    return response.json()

def fetch_data_activity(url):
    params={ 
    'start_date': week_ago_str, 
    'end_date': today_str
    }
    headers = { 
  'Authorization': f'Bearer {os.getenv("TOKEN")}' 
    }
    response = requests.request('GET', url, headers=headers, params=params) 
    return response.json()


    