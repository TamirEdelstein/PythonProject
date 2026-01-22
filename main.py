import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- הגדרות עמוד ---
st.set_page_config(layout="wide", page_title="Bus Analysis System")

st.title("מערכת ניתוח תחבורה ציבורית - מפה מבוססת gtfs_ride_stops")


# --- פונקציה לשליפת המפה מה-Endpoint הקיים אצלך ---
def get_map_data(internal_route_id):
    """שליפת מיקומי תחנות מתוך הטבלה gtfs_ride_stops"""
    url = "https://open-bus-stride-api.hasadna.org.il/gtfs_ride_stops/list"

    # חיפוש עצירות שמשויכות ל-ID של הקו
    params = {
        'gtfs_stop__gtfs_route_id': internal_route_id,
        'limit': 150
    }
    try:
        res = requests.get(url, params=params)
        if res.status_code == 200:
            data = res.json()
            if data:
                stops = []
                for entry in data:
                    # המידע הגיאוגרפי נמצא בתוך אובייקט gtfs_stop
                    s_info = entry.get('gtfs_stop', {})
                    if s_info:
                        stops.append({
                            'lat': s_info.get('lat'),
                            'lon': s_info.get('lon'),
                            'name': s_info.get('name'),
                            'seq': entry.get('stop_sequence', 0)
                        })
                if stops:
                    # ניקוי כפילויות ומיון לפי סדר התחנות
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
    # 1. מציאת הקו ב-gtfs_routes
    url_gtfs = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    res_gtfs = requests.get(url_gtfs, params={
        'route_short_name': line_num, 'route_long_name_contains': city,
        'date_from': '2023-01-01', 'date_to': '2023-01-01'
    })

    if res_gtfs.status_code == 200 and res_gtfs.json():
        route = res_gtfs.json()[0]
        internal_id = route['id']  # ה-ID מהטבלה שצילמת
        l_ref = route['line_ref']
        st.session_state['route_name'] = route.get('route_long_name')
        st.session_state['agency'] = route.get('agency_name')

        # 2. שליפת המפה מה-Endpoint החדש
        st.session_state['map_df'] = get_map_data(internal_id)

        # 3. שליפת נתוני נסיעות (SIRI)
        res_siri = requests.get("https://open-bus-stride-api.hasadna.org.il/siri_rides/list", params={
            'limit': -1, 'gtfs_route__line_refs': l_ref,
            'gtfs_route__date_from': '2024-01-14', 'gtfs_route__date_to': '2024-01-20'
        })
        if res_siri.status_code == 200:
            df_r = pd.DataFrame(res_siri.json())
            if not df_r.empty:
                df_r['scheduled_start_time'] = pd.to_datetime(df_r['scheduled_start_time'])
                df_r['day_of_week'] = df_r['scheduled_start_time'].dt.day_name()
                df_r['hour'] = df_r['scheduled_start_time'].dt.hour
                st.session_state['rides_df'] = df_r
                st.success("הנתונים נטענו בהצלחה!")
    else:
        st.error("לא נמצא קו תואם.")

# --- תצוגה ---
if 'rides_df' in st.session_state:
    st.divider()

    # כרטיס שם הקו
    col_head1, col_head2 = st.columns([3, 1])
    col_head1.info(f"**מסלול:** {st.session_state.get('route_name')}")
    col_head2.metric("מפעיל", st.session_state.get('agency'))

    # סינון ימים (ברירת מחדל יום ראשון)
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    available = [d for d in days if d in st.session_state['rides_df']['day_of_week'].unique()]
    sel_day = st.selectbox("בחר יום:", options=available, index=0)

    filtered = st.session_state['rides_df'][st.session_state['rides_df']['day_of_week'] == sel_day]

    col_left, col_right = st.columns([2, 1.5])

    with col_left:
        with st.container(border=True):
            st.subheader("📍 מפת מסלול (לפי תחנות)")
            if st.session_state.get('map_df') is not None:
                fig = px.line_mapbox(st.session_state['map_df'], lat="lat", lon="lon",
                                     hover_name="name", zoom=11, height=800)
                # עיצוב הקו - עבה מאוד (8) ונקודות (תחנות) בולטות
                fig.update_traces(line=dict(width=8, color="blue"), mode="lines+markers",
                                  marker=dict(size=12, color="red"))
                fig.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("לא נמצאו נתוני מיקום בטבלת gtfs_ride_stops.")

    with col_right:
        with st.container(border=True):
            st.markdown("### Average Duration")
            avg = filtered.groupby('hour')['duration_minutes'].mean().reset_index()
            st.plotly_chart(px.line(avg, x='hour', y='duration_minutes'), use_container_width=True)

        with st.container(border=True):
            st.markdown("### Ride Distribution")
            st.plotly_chart(px.histogram(filtered, x='hour', color_discrete_sequence=['#ff4b4b']),
                            use_container_width=True)