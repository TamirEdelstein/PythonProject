import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.express as px

st.write("Welcome to the Israel Public Transit Analytics App 📊 !")

url = "https://open-bus-stride-api.hasadna.org.il/siri_rides/list"
response = requests.get(url, params={
    'limit': -1,
    'gtfs_route__date_from': '2024-01-14',
    'gtfs_route__date_to': '2024-01-20',
    'gtfs_route__line_refs': '13428',
})

if response.status_code == 200:
    data = response.json()
    rides = pd.DataFrame(data)
else:
    rides = pd.DataFrame() # Ensure rides is defined even on error

rides['scheduled_start_time'] = pd.to_datetime(rides['scheduled_start_time'])
rides['hour'] = rides['scheduled_start_time'].dt.hour
rides['day_of_week'] = rides['scheduled_start_time'].dt.day_name()
rides = rides[['id', 'siri_route_id', 'scheduled_start_time', 'duration_minutes', 'hour', 'day_of_week']]

st.dataframe(rides)


# 1. הגדרת רשימת הימים וקביעת "Sunday" כדיפולט
days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

# 2. מיקום הסליידר מעל הגרף (פשוט מסירים את ה-sidebar)
selected_day = st.selectbox('Select a Day', options=days_order, index=0)

# 3. סינון הנתונים
filtered_rides = rides[rides['day_of_week'] == selected_day]

# 4. החלקת הגרף (Aggregation)
# אנחנו מחשבים את ממוצע משך הנסיעה לכל שעה כדי שתהיה נקודה אחת בלבד בשעה
chart_data = filtered_rides.groupby('hour')['duration_minutes'].mean().reset_index()

# 5. יצירת הגרף עם קו מעוגל (spline)
fig = px.line(chart_data, x='hour', y='duration_minutes',
              title=f'Average Ride Duration by Hour on {selected_day}',
              line_shape='spline', # הופך את הקו למעוגל ולא שבור
              render_mode='svg')

# שיפור נראות - הוספת נקודות על הקו
fig.update_traces(mode='lines+markers')

st.plotly_chart(fig)