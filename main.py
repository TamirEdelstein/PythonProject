import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# הגדרת עמוד רחב
st.set_page_config(layout="wide")

st.title("ברוכים הבאים לאפליקציית ניתוח נתוני קווי התחבורה הציבורית בישראל")

# --- שלב 1: קלט מהמשתמש בראש הדף ---
with st.container(border=True):
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        line_number = st.text_input("מספר קו (route_short_name):", placeholder="לדוגמה: 1")
    with col_in2:
        city_name = st.text_input("עיר/תיאור (route_long_name_contains):", placeholder="לדוגמה: בת ים")

    fetch_button = st.button("טען נתונים ונתח גרפים", use_container_width=True)

# שימוש ב-Session State כדי לשמור את הנתונים גם כשמשנים את הפילטר של הימים
if fetch_button:
    # קריאה ראשונה ל-GTFS
    url_gtfs = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    params_gtfs = {
        'route_short_name': line_number,
        'route_long_name_contains': city_name,
        'date_from': '2023-01-01',
        'date_to': '2023-01-01'
    }

    res_gtfs = requests.get(url_gtfs, params=params_gtfs)
    if res_gtfs.status_code == 200 and res_gtfs.json():
        line_ref = res_gtfs.json()[0]['line_ref']

        # קריאה שנייה ל-SIRI
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

            st.session_state['rides_df'] = df
            st.success(f"הנתונים נטענו בהצלחה עבור line_ref: {line_ref}")
        else:
            st.error("שגיאה בשליפת נתוני הנסיעות.")
    else:
        st.error("לא נמצא קו תואם. בדוק את מספר הקו ושם העיר.")

# --- שלב 2: הצגת הפילטר והגרפים (רק אם יש נתונים) ---
if 'rides_df' in st.session_state:
    rides = st.session_state['rides_df']

    # סלייסר בחירת יום (מעל הגרפים, דיפולט יום ראשון)
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    selected_day = st.selectbox('בחר יום להצגה:', options=days_order, index=0)

    # סינון לפי יום
    filtered_rides = rides[rides['day_of_week'] == selected_day]

    # הצגת הטבלה המעובדת (רק העמודות שביקשת)
    st.subheader(f"טבלת נסיעות - {selected_day}")
    display_df = filtered_rides[
        ['id', 'siri_route_id', 'scheduled_start_time', 'duration_minutes', 'hour', 'day_of_week']]
    st.dataframe(display_df, use_container_width=True)

    st.divider()

    # יצירת הטורים לגרפים
    col_graph1, col_graph2 = st.columns(2)

    # גרף 1: Average Duration (קו חלק)
    with col_graph1:
        with st.container(border=True):
            st.markdown("### Average Duration")
            line_data = filtered_rides.groupby('hour')['duration_minutes'].mean().reset_index()
            fig_line = px.line(line_data, x='hour', y='duration_minutes',
                               line_shape='spline', markers=True)
            fig_line.update_layout(height=500)
            st.plotly_chart(fig_line, use_container_width=True)

    # גרף 2: Ride Distribution (היסטוגרמה)
    with col_graph2:
        with st.container(border=True):
            st.markdown("### Ride Distribution")
            fig_hist = px.histogram(filtered_rides, x='hour', nbins=15,
                                    color_discrete_sequence=['#ff4b4b'])
            fig_hist.update_layout(height=500, bargap=0.1)
            st.plotly_chart(fig_hist, use_container_width=True)