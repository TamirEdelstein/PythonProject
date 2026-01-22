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

# --- 1. פילטר עליון ---
days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
selected_day = st.selectbox('Select a Day', options=days_order, index=0)

# סינון הנתונים
filtered_rides = rides[rides['day_of_week'] == selected_day]

# --- 2. יצירת טורים (Columns) ---
col1, col2 = st.columns(2)

# --- 3. גרף ראשון: קו (בטור שמאל) ---
with col1:
    with st.container(border=True):  # הוספת המסגרת
        st.subheader("Average Duration")

        # עיבוד נתונים לגרף הקו
        line_data = filtered_rides.groupby('hour')['duration_minutes'].mean().reset_index()

        fig_line = px.line(line_data, x='hour', y='Average Ride Duration [min]',
                           line_shape='spline', render_mode='svg')
        fig_line.update_traces(mode='lines+markers')

        # התאמת הגודל כדי שישתלב יפה בטור
        fig_line.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_line, use_container_width=True)

# --- 4. גרף שני: התפלגות (בטור ימין) ---
with col2:
    with st.container(border=True):  # הוספת המסגרת
        st.subheader("Ride Distribution")

        fig_hist = px.histogram(filtered_rides, x='hour', nbins=15,
                                color_discrete_sequence=['#ff4b4b'])

        fig_hist.update_layout(bargap=0.1, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_hist, use_container_width=True)