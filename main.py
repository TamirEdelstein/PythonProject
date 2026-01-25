import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- הגדרות עמוד ---
st.set_page_config(layout="wide", page_title="Bus Analysis Dashboard")

st.title("Bus Analysis Dashboard")

# --- ממשק קלט ---
with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        line_num = st.text_input("Route Num:", value="1")
    with c2:
        city = st.text_input("City:", value="בת ים")

    submit = st.button("Load data and analyse", use_container_width=True)

# --- לוגיקת שליפת נתונים ושמירה ב-Session State ---
if submit:
    # 1. קבלת line_ref
    url_routes = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    res_routes = requests.get(url_routes, params={
        'route_short_name': line_num,
        'route_long_name_contains': city,
        'date_from': '2023-01-22', 'date_to': '2023-01-22'
    })

    if res_routes.status_code == 200 and res_routes.json():
        route_info = res_routes.json()[0]
        line_ref = route_info.get('line_ref')
        st.session_state['line_ref'] = line_ref
        st.session_state['route_name'] = route_info.get('route_long_name', 'קו לא ידוע')

        # 2. שליפת מפה (2023)
        res_stops = requests.get("https://open-bus-stride-api.hasadna.org.il/gtfs_ride_stops/list", params={
            'gtfs_route__line_refs': line_ref,
            'arrival_time_from': '2023-01-22T12:31:08.469Z',
            'arrival_time_to': '2023-01-22T14:31:08.469Z',
            'limit': 300
        })
        if res_stops.status_code == 200:
            st.session_state['map_data'] = res_stops.json()

        # 3. שליפת נתוני SIRI (2024)
        res_siri = requests.get("https://open-bus-stride-api.hasadna.org.il/siri_rides/list", params={
            'limit': -1, 'gtfs_route__line_refs': line_ref,
            'gtfs_route__date_from': '2024-01-14', 'gtfs_route__date_to': '2024-01-20'
        })
        if res_siri.status_code == 200:
            df_siri = pd.DataFrame(res_siri.json())
            if not df_siri.empty:
                df_siri['scheduled_start_time'] = pd.to_datetime(df_siri['scheduled_start_time'])
                df_siri['hour'] = df_siri['scheduled_start_time'].dt.hour
                df_siri['day_name'] = df_siri['scheduled_start_time'].dt.day_name()
                st.session_state['df_siri'] = df_siri
    else:
        st.error("לא נמצא קו תואם ב-GTFS.")

# --- תצוגת התוצאות (מחוץ לבלוק ה-submit) ---
if 'df_siri' in st.session_state:
    df_siri = st.session_state['df_siri']

    st.divider()
    st.info(f"**קו:** {st.session_state['route_name']} (Line Ref: {st.session_state['line_ref']})")

    # פילטר יום - נשאר פעיל גם אחרי שינוי
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    available_days = [d for d in days_order if d in df_siri['day_name'].unique()]

    selected_day = st.selectbox("בחר יום בשבוע לניתוח הגרפים:", options=available_days, index=0)
    filtered_siri = df_siri[df_siri['day_name'] == selected_day]

    col_map, col_charts = st.columns([2, 1.5])

    # חלק המפה
    with col_map:
        with st.container(border=True):
            st.subheader("Line Route📍")
            if 'map_data' in st.session_state:
                df_stops = pd.DataFrame(st.session_state['map_data'])
                lat_col, lon_col = 'gtfs_stop__lat', 'gtfs_stop__lon'
                if not df_stops.empty and lat_col in df_stops.columns:
                    df_map = df_stops.dropna(subset=[lat_col, lon_col]).drop_duplicates(subset=['stop_sequence'])
                    df_map = df_map.sort_values('stop_sequence')

                    fig_map = px.line_mapbox(df_map, lat=lat_col, lon=lon_col, zoom=12, height=750)
                    fig_map.update_traces(line=dict(width=6, color="blue"), mode="lines+markers",
                                          marker=dict(size=10, color="red"))
                    fig_map.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
                    st.plotly_chart(fig_map, use_container_width=True)

    # חלק הגרפים
    with col_charts:
        with st.container(border=True):
            st.markdown(f"### Average Duration - {selected_day}")
            avg_dur = filtered_siri.groupby('hour')['duration_minutes'].mean().reset_index()
            fig_line = px.line(avg_dur, x='hour', y='duration_minutes', markers=True)
            fig_line.update_layout(height=340)
            st.plotly_chart(fig_line, use_container_width=True)

        with st.container(border=True):
            st.markdown(f"### Ride Distribution - {selected_day}")
            fig_hist = px.histogram(filtered_siri, x='hour', nbins=24, color_discrete_sequence=['#ff4b4b'])
            fig_hist.update_layout(height=340, bargap=0.1, yaxis_title="כמות נסיעות")
            st.plotly_chart(fig_hist, use_container_width=True)