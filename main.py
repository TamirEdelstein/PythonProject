import streamlit as st
import requests
import pandas as pd
import plotly.express as px


# --- פונקציות עזר ---
def get_route_geometry(internal_route_id):
    url = "https://open-bus-stride-api.hasadna.org.il/gtfs_route_shapes/list"
    params = {'gtfs_route_id': internal_route_id}
    try:
        res = requests.get(url, params=params)
        if res.status_code == 200:
            data = res.json()
            if data: return pd.DataFrame(data)
    except:
        return None
    return None


# --- ממשק משתמש ---
with st.container(border=True):
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        line_num = st.text_input("מספר קו:", value="1")
    with col_in2:
        city_name = st.text_input("עיר:", value="בת ים")
    fetch_btn = st.button("טען נתונים", use_container_width=True)

if fetch_btn:
    # 1. שליפת GTFS
    url_gtfs = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    res_gtfs = requests.get(url_gtfs, params={
        'route_short_name': line_num,
        'route_long_name_contains': city_name,
        'date_from': '2023-01-01', 'date_to': '2023-01-01'
    })

    if res_gtfs.status_code == 200 and res_gtfs.json():
        route = res_gtfs.json()[0]
        st.session_state['route_name'] = route.get('route_long_name')

        # 2. שליפת SIRI
        res_siri = requests.get("https://open-bus-stride-api.hasadna.org.il/siri_rides/list", params={
            'limit': -1,
            'gtfs_route__date_from': '2024-01-14',
            'gtfs_route__date_to': '2024-01-20',
            'gtfs_route__line_refs': route['line_ref']
        })

        if res_siri.status_code == 200:
            df = pd.DataFrame(res_siri.json())
            if not df.empty:
                df['scheduled_start_time'] = pd.to_datetime(df['scheduled_start_time'])
                df['hour'] = df['scheduled_start_time'].dt.hour
                # תיקון: מוודא ששמות הימים באנגלית תקינה לסינון
                df['day_of_week'] = df['scheduled_start_time'].dt.day_name()

                st.session_state['rides_df'] = df
                st.session_state['geo_df'] = get_route_geometry(route['id'])
            else:
                st.error("לא חזרו נסיעות (Rides) מה-API עבור הטווח המבוקש.")
    else:
        st.error("הקו לא נמצא ב-GTFS.")

# --- תצוגה ---
if 'rides_df' in st.session_state:
    df = st.session_state['rides_df']

    # בדיקה: אילו ימים קיימים בנתונים?
    available_days = df['day_of_week'].unique()

    st.info(f"**קו:** {st.session_state['route_name']}")

    # סלייסר שמתבסס רק על ימים שיש בהם נתונים בפועל
    sel_day = st.selectbox('בחר יום (מתוך הימים שנמצאו בנתונים):', options=available_days)

    filtered = df[df['day_of_week'] == sel_day]

    if not filtered.empty:
        col_map, col_charts = st.columns([2, 1.5])

        with col_map:
            if st.session_state.get('geo_df') is not None:
                fig_map = px.line_mapbox(st.session_state['geo_df'], lat="lat", lon="lon", zoom=11, height=700)
                fig_map.update_traces(line=dict(width=6, color="blue"), mode="lines+markers")
                fig_map.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
                st.plotly_chart(fig_map, use_container_width=True)

        with col_charts:
            # גרף 1: משך נסיעה
            avg_data = filtered.groupby('hour')['duration_minutes'].mean().reset_index()
            st.plotly_chart(px.line(avg_data, x='hour', y='duration_minutes', title="Average Duration"),
                            use_container_width=True)

            # גרף 2: התפלגות נסיעות - הוספת ציר Y ברור
            fig_h = px.histogram(filtered, x='hour', title="Ride Distribution", color_discrete_sequence=['#ff4b4b'])
            fig_h.update_layout(bargap=0.2, yaxis_title="מספר נסיעות")
            st.plotly_chart(fig_h, use_container_width=True)
    else:
        st.warning("אין נתונים להצגה עבור היום הנבחר.")