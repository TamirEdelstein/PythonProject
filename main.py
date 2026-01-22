import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- הגדרות עמוד ---
st.set_page_config(layout="wide", page_title="Bus Route & Map Analysis")

st.title("מערכת ניתוח קווי תחבורה ציבורית - מסלול וזמני נסיעה")


# --- פונקציה אמינה לשליפת מפה לפי תחנות הקו ---
def get_route_stops_geometry(internal_route_id):
    """שליפת מיקומי התחנות של הקו - מקור הנתונים היציב ביותר במערכת"""
    url = "https://open-bus-stride-api.hasadna.org.il/gtfs_stop_times/list"
    params = {
        'gtfs_route_id': internal_route_id,
        'limit': 150  # כיסוי של כל התחנות במסלול
    }
    try:
        res = requests.get(url, params=params)
        if res.status_code == 200:
            data = res.json()
            if data:
                stops_list = []
                for entry in data:
                    stop_info = entry.get('gtfs_stop', {})
                    if stop_info:
                        stops_list.append({
                            'lat': stop_info.get('lat'),
                            'lon': stop_info.get('lon'),
                            'sequence': entry.get('stop_sequence'),
                            'stop_name': stop_info.get('name')
                        })
                if stops_list:
                    # יצירת DataFrame ומיון לפי סדר התחנות בקו
                    return pd.DataFrame(stops_list).sort_values('sequence')
    except Exception as e:
        st.error(f"שגיאה בגישה לנתוני המפה: {e}")
    return None


# --- שלב 1: ממשק קלט למשתמש ---
with st.container(border=True):
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        line_num = st.text_input("מספר קו (route_short_name):", placeholder="לדוגמה: 1")
    with col_in2:
        city_name = st.text_input("עיר (route_long_name_contains):", placeholder="לדוגמה: בת ים")

    fetch_btn = st.button("טען נתונים והצג מפה", use_container_width=True)

# לוגיקת שליפת הנתונים
if fetch_btn and line_num and city_name:
    # 1. חיפוש ראשוני ב-GTFS
    url_gtfs = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    params_gtfs = {
        'route_short_name': line_num,
        'route_long_name_contains': city_name,
        'date_from': '2023-01-01',
        'date_to': '2023-01-01'
    }

    res_gtfs = requests.get(url_gtfs, params=params_gtfs)
    if res_gtfs.status_code == 200 and res_gtfs.json():
        first_route = res_gtfs.json()[0]
        st.session_state['route_name'] = first_route.get('route_long_name', 'שם קו לא ידוע')
        st.session_state['agency_name'] = first_route.get('agency_name', '')

        internal_id = first_route['id']
        l_ref = first_route['line_ref']

        # 2. שליפת נתוני נסיעות (SIRI)
        url_siri = "https://open-bus-stride-api.hasadna.org.il/siri_rides/list"
        params_siri = {
            'limit': -1,
            'gtfs_route__date_from': '2024-01-14',
            'gtfs_route__date_to': '2024-01-20',
            'gtfs_route__line_refs': l_ref
        }
        res_siri = requests.get(url_siri, params=params_siri)

        if res_siri.status_code == 200:
            df_rides = pd.DataFrame(res_siri.json())
            if not df_rides.empty:
                df_rides['scheduled_start_time'] = pd.to_datetime(df_rides['scheduled_start_time'])
                df_rides['hour'] = df_rides['scheduled_start_time'].dt.hour
                df_rides['day_of_week'] = df_rides['scheduled_start_time'].dt.day_name()

                st.session_state['rides_df'] = df_rides
                # שליפת מפה מבוססת תחנות
                st.session_state['geo_df'] = get_route_stops_geometry(internal_id)
                st.success("הנתונים והמפה נטענו בהצלחה!")
            else:
                st.error("לא נמצאו נסיעות ב-SIRI עבור קו זה.")
    else:
        st.error("הקו לא נמצא ב-GTFS. וודא שמספר הקו והעיר נכונים.")

# --- שלב 2: תצוגה ---
if 'rides_df' in st.session_state:
    st.divider()

    # כרטיס מידע על הקו
    c1, c2 = st.columns([3, 1])
    with c1:
        st.info(f"**מסלול הקו:** {st.session_state['route_name']}")
    with c2:
        st.metric("מפעיל", st.session_state['agency_name'])

    # בחירת יום (ראשון כברירת מחדל)
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    actual_days = [day for day in days_order if day in st.session_state['rides_df']['day_of_week'].unique()]

    sel_day = st.selectbox('בחר יום להצגה:', options=actual_days, index=0)
    filtered = st.session_state['rides_df'][st.session_state['rides_df']['day_of_week'] == sel_day]

    # פריסת מפה וגרפים
    col_map, col_charts = st.columns([2, 1.5])

    with col_map:
        with st.container(border=True):
            st.subheader("📍 מפת תחנות ומסלול הקו")
            if st.session_state.get('geo_df') is not None:
                df_geo = st.session_state['geo_df']
                # יצירת מפה
                fig_map = px.line_mapbox(
                    df_geo, lat="lat", lon="lon",
                    hover_name="stop_name",
                    zoom=11, height=800
                )
                # עיצוב בולט
                fig_map.update_traces(
                    line=dict(width=6, color="blue"),
                    mode="lines+markers",
                    marker=dict(size=12, color="red")
                )
                fig_map.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.warning("לא נמצאו נתוני מיקום עבור תחנות הקו.")

    with col_charts:
        # גרף 1: משך נסיעה
        with st.container(border=True):
            st.markdown("### Average Duration (min)")
            if not filtered.empty:
                line_data = filtered.groupby('hour')['duration_minutes'].mean().reset_index()
                fig_l = px.line(line_data, x='hour', y='duration_minutes', line_shape='spline', markers=True)
                fig_l.update_layout(height=350)
                st.plotly_chart(fig_l, use_container_width=True)

        # גרף 2: התפלגות נסיעות
        with st.container(border=True):
            st.markdown("### Ride Distribution")
            if not filtered.empty:
                fig_h = px.histogram(filtered, x='hour', nbins=24, color_discrete_sequence=['#ff4b4b'])
                fig_h.update_layout(height=350, bargap=0.1, yaxis_title="מספר נסיעות")
                st.plotly_chart(fig_h, use_container_width=True)

    # טבלה מלאה
    with st.expander("צפה בטבלת הנתונים המלאה"):
        st.dataframe(filtered[['id', 'scheduled_start_time', 'duration_minutes', 'hour', 'day_of_week']],
                     use_container_width=True)