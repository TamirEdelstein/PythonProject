import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- הגדרות עמוד ---
st.set_page_config(layout="wide", page_title="Bus Analysis Dashboard")

st.title("ניתוח קו אוטובוס: מסלול וביצועים")

# --- ממשק קלט ---
with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        line_num = st.text_input("מספר קו (למשל 1):", value="1")
    with c2:
        city = st.text_input("עיר (למשל בת ים):", value="בת ים")

    submit = st.button("טען נתונים ונתח", use_container_width=True)

if submit:
    # --- שלב 1: קבלת line_ref מ-gtfs_routes ---
    url_routes = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    params_routes = {
        'route_short_name': line_num,
        'route_long_name_contains': city,
        'date_from': '2023-01-22',
        'date_to': '2023-01-22'
    }

    res_routes = requests.get(url_routes, params=params_routes)

    if res_routes.status_code == 200 and res_routes.json():
        route_info = res_routes.json()[0]
        line_ref = route_info.get('line_ref')
        route_name = route_info.get('route_long_name', 'קו לא ידוע')

        st.info(f"**קו:** {route_name} (Line Ref: {line_ref})")

        # --- שלב 2: שליפת נתוני מפה (2023) מ-gtfs_ride_stops ---
        url_stops = "https://open-bus-stride-api.hasadna.org.il/gtfs_ride_stops/list"
        params_stops = {
            'gtfs_route__line_refs': line_ref,
            'arrival_time_from': '2023-01-22T12:31:08.469Z',
            'arrival_time_to': '2023-01-22T14:31:08.469Z',
            'limit': 300
        }
        res_stops = requests.get(url_stops, params=params_stops)

        # --- שלב 3: שליפת נתוני SIRI (2024) לגרפים ---
        url_siri = "https://open-bus-stride-api.hasadna.org.il/siri_rides/list"
        params_siri = {
            'limit': -1,
            'gtfs_route__line_refs': line_ref,
            'gtfs_route__date_from': '2024-01-14',
            'gtfs_route__date_to': '2024-01-20'
        }
        res_siri = requests.get(url_siri, params=params_siri)

        # --- עיבוד נתונים לגרפים ---
        if res_siri.status_code == 200:
            df_siri = pd.DataFrame(res_siri.json())
            if not df_siri.empty:
                df_siri['scheduled_start_time'] = pd.to_datetime(df_siri['scheduled_start_time'])
                df_siri['hour'] = df_siri['scheduled_start_time'].dt.hour
                df_siri['day_name'] = df_siri['scheduled_start_time'].dt.day_name()

                # הגדרת סדר ימים ובחירה בדיפולט
                days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                available_days = [d for d in days_order if d in df_siri['day_name'].unique()]

                # --- תצוגה ---
                st.divider()

                # פילטר יום (מחוץ לעמודות כדי שישפיע על הכל)
                selected_day = st.selectbox("בחר יום בשבוע לניתוח הגרפים:", options=available_days, index=0)

                filtered_siri = df_siri[df_siri['day_name'] == selected_day]

                col_map, col_charts = st.columns([2, 1.5])

                # חלק המפה
                with col_map:
                    with st.container(border=True):
                        st.subheader(f"📍 מסלול הקו (לפי עצירות)")
                        if res_stops.status_code == 200:
                            df_stops = pd.DataFrame(res_stops.json())
                            lat_col, lon_col = 'gtfs_stop__lat', 'gtfs_stop__lon'

                            if not df_stops.empty and lat_col in df_stops.columns:
                                df_map = df_stops.dropna(subset=[lat_col, lon_col]).drop_duplicates(
                                    subset=['stop_sequence'])
                                df_map = df_map.sort_values('stop_sequence')

                                fig_map = px.line_mapbox(
                                    df_map, lat=lat_col, lon=lon_col,
                                    hover_name="gtfs_stop__name" if "gtfs_stop__name" in df_map.columns else None,
                                    zoom=12, height=750
                                )
                                fig_map.update_traces(line=dict(width=6, color="blue"), mode="lines+markers",
                                                      marker=dict(size=10, color="red"))
                                fig_map.update_layout(mapbox_style="open-street-map",
                                                      margin={"r": 0, "t": 0, "l": 0, "b": 0})
                                st.plotly_chart(fig_map, use_container_width=True)
                            else:
                                st.warning("לא נמצאו נתונים גיאוגרפיים ב-gtfs_ride_stops.")

                # חלק הגרפים
                with col_charts:
                    # גרף 1
                    with st.container(border=True):
                        st.markdown(f"### Average Duration - {selected_day}")
                        avg_dur = filtered_siri.groupby('hour')['duration_minutes'].mean().reset_index()
                        fig_line = px.line(avg_dur, x='hour', y='duration_minutes', markers=True)
                        fig_line.update_layout(height=340)
                        st.plotly_chart(fig_line, use_container_width=True)

                    # גרף 2
                    with st.container(border=True):
                        st.markdown(f"### Ride Distribution - {selected_day}")
                        fig_hist = px.histogram(filtered_siri, x='hour', nbins=24, color_discrete_sequence=['#ff4b4b'])
                        fig_hist.update_layout(height=340, bargap=0.1, yaxis_title="כמות נסיעות")
                        st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.warning("לא נמצאו נתוני נסיעות (SIRI) לגרפים.")
    else:
        st.error("לא נמצא קו תואם ב-GTFS.")