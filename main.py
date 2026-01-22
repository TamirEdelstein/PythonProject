import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- הגדרות עמוד ---
st.set_page_config(layout="wide", page_title="Bus Route & Map Analysis")

st.title("מערכת ניתוח קווי תחבורה ציבורית - מסלול וזמני נסיעה")


# --- פונקציות שליפה מה-API ---

def get_route_geometry(internal_route_id):
    """שליפת נקודות המסלול המדויקות (Shapes) לפי ה-ID הפנימי של הקו"""
    url = "https://open-bus-stride-api.hasadna.org.il/gtfs_route_shapes/list"
    params = {'gtfs_route_id': internal_route_id}
    try:
        res = requests.get(url, params=params)
        if res.status_code == 200:
            data = res.json()
            if data:
                return pd.DataFrame(data)  # מחזיר טבלה עם עמודות lat ו-lon
    except Exception as e:
        st.error(f"שגיאה בשליפת המפה: {e}")
    return None


# --- שלב 1: ממשק קלט למשתמש ---
with st.container(border=True):
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        line_num = st.text_input("מספר קו (route_short_name):", placeholder="לדוגמה: 1")
    with col_in2:
        city_name = st.text_input("עיר (route_long_name_contains):", placeholder="לדוגמה: בת ים")

    fetch_btn = st.button("טען נתונים והצג מפה", use_container_width=True)

# לוגיקת שליפת הנתונים (Session State לשמירה על המידע)
if fetch_btn and line_num and city_name:
    # 1. מציאת ה-line_ref וה-internal_id ב-GTFS
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
            # עיבוד נתונים
            df_rides['scheduled_start_time'] = pd.to_datetime(df_rides['scheduled_start_time'])
            df_rides['hour'] = df_rides['scheduled_start_time'].dt.hour
            df_rides['day_of_week'] = df_rides['scheduled_start_time'].dt.day_name()

            st.session_state['rides_df'] = df_rides
            # 3. שליפת הגיאומטריה למפה
            st.session_state['geo_df'] = get_route_geometry(internal_id)
            st.success(f"הנתונים נטענו בהצלחה עבור קו {line_num}!")
    else:
        st.error("לא נמצא קו תואם. נסה לדייק את שם העיר.")

# --- שלב 2: תצוגת המפה והגרפים ---
if 'rides_df' in st.session_state:
    # בחירת יום
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    sel_day = st.selectbox('בחר יום להצגה:', options=days_order, index=0)

    filtered = st.session_state['rides_df'][st.session_state['rides_df']['day_of_week'] == sel_day]

    st.divider()

    # יצירת פריסה: מפה גדולה משמאל, גרפים מימין
    col_map, col_charts = st.columns([2, 1.5])

    with col_map:
        with st.container(border=True):
            st.subheader("📍 מפת מסלול הקו המדויק")
            if st.session_state.get('geo_df') is not None:
                df_geo = st.session_state['geo_df']
                # שימוש ב-line_mapbox לציור המסלול על הכבישים
                fig_map = px.line_mapbox(
                    df_geo, lat="lat", lon="lon",
                    zoom=12, height=830
                )
                # עיצוב הקו: עובי 8 ונקודות (markers) בולטות
                fig_map.update_traces(
                    line=dict(width=8, color="blue"),
                    mode="lines+markers",
                    marker=dict(size=10)
                )
                fig_map.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.warning("לא נמצאו נתונים גיאוגרפיים למסלול זה בטבלת route_shapes.")

    with col_charts:
        # גרף 1: משך נסיעה ממוצע
        with st.container(border=True):
            st.markdown("### Average Duration (min)")
            line_data = filtered.groupby('hour')['duration_minutes'].mean().reset_index()
            fig_l = px.line(line_data, x='hour', y='duration_minutes', line_shape='spline', markers=True)
            fig_l.update_layout(height=350)
            st.plotly_chart(fig_l, use_container_width=True)

        # גרף 2: התפלגות נסיעות
        with st.container(border=True):
            st.markdown("### Ride Distribution")
            fig_h = px.histogram(filtered, x='hour', nbins=15, color_discrete_sequence=['#ff4b4b'])
            fig_h.update_layout(height=350, bargap=0.1)
            st.plotly_chart(fig_h, use_container_width=True)

    # טבלה תחתונה
    with st.expander("צפה בטבלת הנתונים המלאה"):
        st.dataframe(filtered[['id', 'scheduled_start_time', 'duration_minutes', 'hour', 'day_of_week']],
                     use_container_width=True)