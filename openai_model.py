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
- Today's Sleep Rating: {sleep_rating}/100 (100 = slept better than sleeping beauty, 1 = barely slept)
- Today's Stress Level: {stress_level}/100 (100 = being chased by a lion, 1 = totally relaxed)

Analyze the trends from the 4-day data. Focus on the sleep, readniess, activity and workout data. 
The difference between actitivty and workout data is that activity data shows my actitvity through out the day and gives a overall picture of my activity levels and wourkout is when I activily done a workout.
Today's Sleep Rating is based on how I'm feeling today, not on messured data. Compare the Today's Sleep Rating with the Sleep Data.
Today's Stress Level is based on how I'm feeling today, not on messured data.
Compare the data from the previous days with the current day.
Write 3 practical actions for today and end with a motivational message to help the user achieve their health goals.
Focus on improvements or changes needed based on the data trends. Add emojis to make the message more engaging. The message cannot be longer than 1500 characters.
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

