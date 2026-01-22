import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- הגדרות עמוד רחב ---
st.set_page_config(layout="wide", page_title="Israel Public Transport Analysis")

st.title("ברוכים הבאים לאפליקציית ניתוח נתוני קווי התחבורה הציבורית בישראל")

# --- שלב 1: קלט מהמשתמש ---
with st.container(border=True):
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        line_number = st.text_input("מספר קו (route_short_name):", placeholder="לדוגמה: 1")
    with col_in2:
        city_name = st.text_input("עיר/תיאור (route_long_name_contains):", placeholder="לדוגמה: בת ים")

    fetch_button = st.button("טען נתונים ונתח", use_container_width=True)

# לוגיקת טעינת נתונים ושמירה ב-Session State
if fetch_button and line_number and city_name:
    # שאילתה 1: שליפת line_ref מה-GTFS
    url_gtfs = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    params_gtfs = {
        'route_short_name': line_number,
        'route_long_name_contains': city_name,
        'date_from': '2023-01-01',
        'date_to': '2023-01-01'
    }

    try:
        res_gtfs = requests.get(url_gtfs, params=params_gtfs)
        if res_gtfs.status_code == 200 and res_gtfs.json():
            route_info = res_gtfs.json()[0]
            line_ref = route_info['line_ref']

            # שאילתה 2: שליפת נסיעות מה-SIRI לפי ה-line_ref שקיבלנו
            url_siri = "https://open-bus-stride-api.hasadna.org.il/siri_rides/list"
            params_siri = {
                'limit': -1,
                'gtfs_route__date_from': '2024-01-14',
                'gtfs_route__date_to': '2024-01-20',
                'gtfs_route__line_refs': line_ref
            }
            res_siri = requests.get(url_siri, params=params_siri)

            if res_siri.status_code == 200:
                df = pd.DataFrame(res_siri.json())
                # עיבוד נתונים
                df['scheduled_start_time'] = pd.to_datetime(df['scheduled_start_time'])
                df['hour'] = df['scheduled_start_time'].dt.hour
                df['day_of_week'] = df['scheduled_start_time'].dt.day_name()

                # שמירה ל-Session State כדי למנוע טעינה מחדש בשינוי פילטר
                st.session_state['rides_df'] = df
                st.session_state['route_info'] = route_info
                st.success(f"הנתונים נטענו עבור קו {line_number} (מזהה: {line_ref})")
            else:
                st.error("שגיאה בשליפת נתוני הנסיעות (SIRI).")
        else:
            st.error("לא נמצא קו תואם בחיפוש ה-GTFS.")
    except Exception as e:
        st.error(f"אירעה שגיאה: {e}")

# --- שלב 2: תצוגה (רק אם יש נתונים) ---
if 'rides_df' in st.session_state:
    rides = st.session_state['rides_df']

    # פילטר בחירת יום - ממוקם מעל הגרפים
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    selected_day = st.selectbox('בחר יום להצגה:', options=days_order, index=0)

    filtered_rides = rides[rides['day_of_week'] == selected_day]

    st.divider()

    # יצירת פריסה: טור מפה (שמאל) וטור גרפים (ימין)
    col_map, col_charts = st.columns([2, 1.5])

    with col_map:
        with st.container(border=True):
            st.subheader("📍 מפת מסלול הקו")

            #