from dotenv import load_dotenv
import os
import requests 

load_dotenv('.env')
url = 'https://api.ouraring.com/v2/usercollection/daily_activity' 
params={ 
    'start_date': '2021-11-01', 
    'end_date': '2021-12-01' 
}
headers = { 
  'Authorization': f'Bearer {os.getenv("TOKEN")}' 
}
response = requests.request('GET', url, headers=headers, params=params) 
print(response.text)