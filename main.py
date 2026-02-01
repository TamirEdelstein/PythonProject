import streamlit as st
import requests
import pandas as pd
import plotly.express as px


# --- פונקציית עזר לבדיקת תקינות תגובה ---
def check_response(response):
    if response.status_code == 503:
        st.error("❌ The server is currently unavailable. Please try again later (Error 503).")
        return False
    elif response.status_code != 200:
        st.error(f"❌ Server communication error (Status Code: {response.status_code})")
        return False
    return True


# --- הגדרות עמוד ---
st.set_page_config(layout="wide", page_title="Bus Analysis Dashboard")
st.title("Bus Line Analysis: Route and Performance")

# --- אתחול ה-Session State (הזיכרון של האפליקציה) ---
if 'data' not in st.session_state:
    st.session_state.data = None

# --- ממשק קלט ---
with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        line_num = st.text_input("Line No.:", value="1")
    with c2:
        city = st.text_input("City:", value="בת ים")

    submit = st.button("Load Data & Analyze", use_container_width=True)

# לוגיקת שליפת הנתונים (רצה רק בלחיצה על הכפתור)
if submit:
    with st.spinner("Connecting to Stride API and fetching bus data..."):
        try:
            url_routes = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
            params_routes = {'route_short_name': line_num, 'route_long_name_contains': city, 'date_from': '2023-01-22',
                             'date_to': '2023-01-22'}
            res_routes = requests.get(url_routes, params=params_routes, timeout=100)

            if check_response(res_routes):
                routes_json = res_routes.json()
                if routes_json:
                    line_ref = routes_json[0].get('line_ref')
                    route_name = routes_json[0].get('route_long_name', 'קו לא ידוע')

                    # שליפת נתוני מפה
                    url_stops = "https://open-bus-stride-api.hasadna.org.il/gtfs_ride_stops/list"
                    res_stops = requests.get(url_stops, params={'gtfs_route__line_refs': line_ref,
                                                                'arrival_time_from': '2023-01-22T12:31:08.469Z',
                                                                'arrival_time_to': '2023-01-22T14:31:08.469Z',
                                                                'limit': 300}, timeout=100)

                    # שליפת נתוני SIRI
                    url_siri = "https://open-bus-stride-api.hasadna.org.il/siri_rides/list"
                    res_siri = requests.get(url_siri, params={'limit': 1000, 'gtfs_route__line_refs': line_ref,
                                                              'gtfs_route__date_from': '2024-01-14',
                                                              'gtfs_route__date_to': '2024-01-20'}, timeout=100)

                    if check_response(res_stops) and check_response(res_siri):
                        # שמירת הכל בזיכרון של ה-Session
                        st.session_state.data = {
                            'route_name': route_name,
                            'line_ref': line_ref,
                            'stops_json': res_stops.json(),
                            'siri_json': res_siri.json()
                        }
                else:
                    st.error("לא נמצא קו תואם ב-GTFS.")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# --- חלק התצוגה (רץ תמיד אם יש נתונים בזיכרון) ---
if st.session_state.data:
    data = st.session_state.data
    st.info(f"**קו:** {data['route_name']} (Line Ref: {data['line_ref']})")

    df_siri = pd.DataFrame(data['siri_json'])
    if not df_siri.empty:
        df_siri['scheduled_start_time'] = pd.to_datetime(df_siri['scheduled_start_time'])
        df_siri['hour'] = df_siri['scheduled_start_time'].dt.hour
        df_siri['day_name'] = df_siri['scheduled_start_time'].dt.day_name()

        days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        available_days = [d for d in days_order if d in df_siri['day_name'].unique()]

        st.divider()
        # עכשיו שינוי היום לא ימחוק את הנתונים כי הם ב-session_state
        selected_day = st.selectbox("בחר יום בשבוע לניתוח הגרפים:", options=available_days)
        filtered_siri = df_siri[df_siri['day_name'] == selected_day]

        col_map, col_charts = st.columns([2, 1.5])

        with col_map:
            with st.container(border=True):
                st.subheader("📍 מסלול הקו")
                df_stops = pd.DataFrame(data['stops_json'])
                if not df_stops.empty:
                    df_map = df_stops.dropna(subset=['gtfs_stop__lat', 'gtfs_stop__lon']).drop_duplicates(
                        subset=['stop_sequence']).sort_values('stop_sequence')
                    fig_map = px.line_mapbox(df_map, lat='gtfs_stop__lat', lon='gtfs_stop__lon', zoom=12, height=750)
                    fig_map.update_traces(line=dict(width=6, color="blue"), mode="lines+markers",
                                          marker=dict(size=10, color="red"))
                    fig_map.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
                    st.plotly_chart(fig_map, use_container_width=True)

        with col_charts:
            with st.container(border=True):
                st.markdown(f"**Average Duration - {selected_day}**")
                avg_dur = filtered_siri.groupby('hour')['duration_minutes'].mean().reset_index()
                fig_line = px.line(avg_dur, x='hour', y='duration_minutes', markers=True)
                fig_line.update_layout(height=345, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_line, use_container_width=True)

            with st.container(border=True):
                st.markdown(f"**Ride Distribution - {selected_day}**")
                fig_hist = px.histogram(filtered_siri, x='hour', nbins=24, color_discrete_sequence=['#ff4b4b'])
                fig_hist.update_layout(height=345, bargap=0.1, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_hist, use_container_width=True)