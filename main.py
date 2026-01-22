import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- הגדרות עמוד ---
st.set_page_config(layout="wide", page_title="Bus Analysis System")

st.title("מערכת ניתוח תחבורה ציבורית - מפה מבוססת תאריכי הגעה")


# --- פונקציה לשליפת המפה לפי הפרמטרים שציינת ---
def get_map_data_fixed(line_ref):
    """שליפת מיקומי תחנות מתוך gtfs_ride_stops עם מסנני זמן"""
    url = "https://open-bus-stride-api.hasadna.org.il/gtfs_ride_stops/list"

    params = {
        'gtfs_route__line_refs': line_ref,
        # הפרמטרים שהגדרת שחובה להכניס:
        'arrival_time_from': '2023-01-22T12:31:08.469Z',
        'arrival_time_to': '2023-01-22T14:31:08.469Z',
        'limit': -1
    }

    try:
        res = requests.get(url, params=params)
        if res.status_code == 200:
            data = res.json()
            if data:
                stops = []
                for entry in data:
                    s_info = entry.get('gtfs_stop', {})
                    if s_info:
                        stops.append({
                            'lat': s_info.get('lat'),
                            'lon': s_info.get('lon'),
                            'name': s_info.get('name'),
                            'seq': entry.get('stop_sequence', 0)
                        })
                if stops:
                    # ניקוי כפילויות של תחנות ומיון לפי סדר הנסיעה
                    df = pd.DataFrame(stops).drop_duplicates(subset=['lat', 'lon'])
                    return df.sort_values('seq')
    except Exception as e:
        st.error(f"שגיאה בשליפת המפה: {e}")
    return None


# --- ממשק קלט ---
with st.container(border=True):
    c1, c2 = st.columns(2)
    line_num = c1.text_input("מספר קו:", value="1")
    city = c2.text_input("עיר:", value="בת ים")
    btn = st.button("טען נתונים וצייר מפה", use_container_width=True)

if btn:
    # 1. מציאת ה-line_ref ב-gtfs_routes
    url_gtfs = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    res_gtfs = requests.get(url_gtfs, params={
        'route_short_name': line_num,
        'route_long_name_contains': city,
        'date_from': '2023-01-01',
        'date_to': '2023-01-01'
    })

    if res_gtfs.status_code == 200 and res_gtfs.json():
        route = res_gtfs.json()[0]
        l_ref = route['line_ref']  # שליפת ה-line_ref לשימוש במפה
        st.session_state['route_name'] = route.get('route_long_name')
        st.session_state['agency'] = route.get('agency_name')

        # 2. שליפת המפה עם הפרמטרים החדשים
        st.session_state['map_df'] = get_map_data_fixed(l_ref)

        # 3. שליפת נתוני נסיעות לגרפים (SIRI)
        res_siri = requests.get("https://open-bus-stride-api.hasadna.org.il/siri_rides/list", params={
            'limit': -1,
            'gtfs_route__line_refs': l_ref,
            'gtfs_route__date_from': '2024-01-14',
            'gtfs_route__date_to': '2024-01-20'
        })
        if res_siri.status_code == 200:
            df_r = pd.DataFrame(res_siri.json())
            if not df_r.empty:
                df_r['scheduled_start_time'] = pd.to_datetime(df_r['scheduled_start_time'])
                df_r['day_of_week'] = df_r['scheduled_start_time'].dt.day_name()
                df_r['hour'] = df_r['scheduled_start_time'].dt.hour
                st.session_state['rides_df'] = df_r
                st.success("הנתונים נטענו!")
    else:
        st.error("הקו לא נמצא.")

# --- תצוגה ---
if 'rides_df' in st.session_state:
    st.divider()
    st.info(f"**מסלול:** {st.session_state.get('route_name')}")

    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    available = [d for d in days if d in st.session_state['rides_df']['day_of_week'].unique()]
    sel_day = st.selectbox("בחר יום:", options=available, index=0)

    filtered = st.session_state['rides_df'][st.session_state['rides_df']['day_of_week'] == sel_day]

    col_left, col_right = st.columns([2, 1.5])

    with col_left:
        with st.container(border=True):
            st.subheader("📍 מפת מסלול (gtfs_ride_stops)")
            if st.session_state.get('map_df') is not None and not st.session_state['map_df'].empty:
                fig = px.line_mapbox(st.session_state['map_df'], lat="lat", lon="lon",
                                     hover_name="name", zoom=12, height=700)
                fig.update_traces(line=dict(width=6, color="blue"), mode="lines+markers",
                                  marker=dict(size=10, color="red"))
                fig.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("לא חזרו נתונים גיאוגרפיים בטווח הזמן הזה. נסה קו אחר או בדוק את התאריכים.")

    with col_right:
        with st.container(border=True):
            avg = filtered.groupby('hour')['duration_minutes'].mean().reset_index()
            st.plotly_chart(px.line(avg, x='hour', y='duration_minutes', title="Average Duration"),
                            use_container_width=True)
        with st.container(border=True):
            st.plotly_chart(px.histogram(filtered, x='hour', title="Ride Distribution"), use_container_width=True)