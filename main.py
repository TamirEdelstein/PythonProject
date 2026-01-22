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

# --- 1. הגדרת עמוד רחב (חייב להיות הפקודה הראשונה ב-Streamlit) ---
st.set_page_config(layout="wide")

# (נניח שהדאטה-פריים 'rides' כבר טעון כאן)
# לצורך הדגמה, אם אין לך את הנתונים, הסרי את ההערה מהשורה הבאה:
# rides = px.data.tips().rename(columns={'day': 'day_of_week', 'size': 'duration_minutes', 'time': 'hour'})
# rides['hour'] = rides['hour'].map({'Dinner': 18, 'Lunch': 12}) # המרה פשוטה להדגמה

# --- פילטר עליון ---
# (בדוגמה שלך הפילטר היה בתוך הקונטיינר, כאן החזרתי אותו למעלה כפי שהיה בקוד הקודם לנוחות)
days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
selected_day = st.selectbox('Select a Day', options=days_order, index=0)

# סינון הנתונים
filtered_rides = rides[rides['day_of_week'] == selected_day]

# --- יצירת טורים רחבים ---
col1, col2 = st.columns(2)

# --- גרף 1 (שמאל) ---
with col1:
    with st.container(border=True):
        st.subheader("Average Duration")
        line_data = filtered_rides.groupby('hour')['duration_minutes'].mean().reset_index()
        fig_line = px.line(line_data, x='hour', y='duration_minutes',
                           line_shape='spline', render_mode='svg')
        fig_line.update_traces(mode='lines+markers')
        fig_line.update_layout(margin=dict(l=20, r=20, t=20, b=20))

        # --- 2. הגדרת גובה קבוע לקבלת מראה ריבועי ---
        # use_container_width=True דואג לרוחב, height=550 דואג לגובה
        st.plotly_chart(fig_line, use_container_width=True, height=550)

# --- גרף 2 (ימין) ---
with col2:
    with st.container(border=True):
        st.subheader("Ride Distribution")
        fig_hist = px.histogram(filtered_rides, x='hour', nbins=15,
                                color_discrete_sequence=['#ff4b4b'])
        fig_hist.update_layout(bargap=0.1, margin=dict(l=20, r=20, t=20, b=20))

        # --- 2. הגדרת גובה קבוע גם כאן ---
        st.plotly_chart(fig_hist, use_container_width=True, height=550)