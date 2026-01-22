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

# Create a dropdown in the sidebar
selected_day = st.sidebar.selectbox('Select a Day', rides['day_of_week'].unique())
# Filter data based on selection
filtered_rides = rides[rides['day_of_week'] == selected_day]
# Plot the dynamic data
fig = px.line(filtered_rides, x='hour', y='duration_minutes',
              title=f'Ride Duration by Hour on {selected_day}')
st.plotly_chart(fig)