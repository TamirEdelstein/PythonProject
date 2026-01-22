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


# --- 1. הגדרת הפילטר (מופיע פעם אחת בראש הדף) ---
days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
selected_day = st.selectbox('Select a Day', options=days_order, index=0)

# --- 2. סינון הנתונים (מתבצע פעם אחת עבור כל הגרפים) ---
filtered_rides = rides[rides['day_of_week'] == selected_day]

# --- 3. גרף 1: משך נסיעה ממוצע (Line Plot) ---
st.subheader(f"Average Ride Duration on {selected_day}")

# קיבוץ נתונים לממוצע לפי שעה כדי למנוע את הזיג-זג
line_data = filtered_rides.groupby('hour')['duration_minutes'].mean().reset_index()

fig_line = px.line(line_data, x='hour', y='duration_minutes',
                   line_shape='spline', render_mode='svg')
fig_line.update_traces(mode='lines+markers')
st.plotly_chart(fig_line)

# --- 4. גרף 2: התפלגות נסיעות (Histogram / Displot) ---
st.subheader(f"Distribution of Rides by Hour on {selected_day}")

fig_hist = px.histogram(filtered_rides, x='hour',
                        nbins=15,
                        title=None,
                        color_discrete_sequence=['#ff4b4b']) # צבע אדום-סטרימליט

# הוספת עיצוב לצירים
fig_hist.update_layout(bargap=0.1, xaxis_title="Hour of Day", yaxis_title="Number of Rides")

st.plotly_chart(fig_hist)