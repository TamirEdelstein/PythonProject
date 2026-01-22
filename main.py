import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")
st.title("מערכת ניתוח קווי תחבורה ציבורית")

# --- שלב 1: קלט מהמשתמש ---
col1, col2 = st.columns(2)
with col1:
    line_number = st.text_input("מספר קו (route_short_name):", placeholder="לדוגמה: 1")
with col2:
    city_name = st.text_input("עיר/תיאור (route_long_name_contains):", placeholder="לדוגמה: בת ים")

if st.button("טען נתונים"):
    if line_number and city_name:
        # --- שלב 2: קריאה ראשונה לזיהוי ה-line_ref ---
        url_gtfs = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
        params_gtfs = {
            'route_short_name': line_number,
            'route_long_name_contains': city_name,
            'date_from': '2023-01-01',
            'date_to': '2023-01-01'
        }

        try:
            res_gtfs = requests.get(url_gtfs, params=params_gtfs)
            if res_gtfs.status_code == 200:
                gtfs_data = res_gtfs.json()

                if gtfs_data:
                    # לקיחת ה-line_ref מהתוצאה הראשונה
                    line_ref = gtfs_data[0]['line_ref']
                    st.info(f"נמצא קו מתאים. מזהה מערכת (line_ref): {line_ref}")

                    # --- שלב 3: קריאה שנייה לקבלת הנסיעות (SIRI) ---
                    url_siri = "https://open-bus-stride-api.hasadna.org.il/siri_rides/list"
                    params_siri = {
                        'limit': -1,
                        'gtfs_route__date_from': '2024-01-14',
                        'gtfs_route__date_to': '2024-01-20',
                        'gtfs_route__line_refs': line_ref
                    }

                    res_siri = requests.get(url_siri, params=params_siri)
                    if res_siri.status_code == 200:
                        rides_data = res_siri.json()
                        rides = pd.DataFrame(rides_data)

                        if not rides.empty:
                            # --- שלב 4: עיבוד הנתונים לפי הבקשה ---
                            rides['scheduled_start_time'] = pd.to_datetime(rides['scheduled_start_time'])
                            rides['hour'] = rides['scheduled_start_time'].dt.hour
                            rides['day_of_week'] = rides['scheduled_start_time'].dt.day_name()

                            # סינון עמודות
                            rides_filtered = rides[
                                ['id', 'siri_route_id', 'scheduled_start_time', 'duration_minutes', 'hour',
                                 'day_of_week']]

                            # הצגת הטבלה
                            st.subheader(f"נתוני נסיעות עבור קו {line_number}")
                            st.dataframe(rides_filtered, use_container_width=True)
                        else:
                            st.warning("לא נמצאו נסיעות עבור ה-line_ref שהתקבל.")
                    else:
                        st.error(f"שגיאה בשליפת נסיעות: {res_siri.status_code}")
                else:
                    st.warning("לא נמצא קו תואם בחיפוש הראשוני. נסה לדייק את שם העיר.")
            else:
                st.error(f"שגיאה בחיפוש הקו: {res_gtfs.status_code}")

        except Exception as e:
            st.error(f"אירעה שגיאה בתהליך: {e}")
    else:
        st.info("אנא הזן מספר קו ושם עיר כדי להתחיל.")

        # (בדוגמה שלך הפילטר היה בתוך הקונטיינר, כאן החזרתי אותו למעלה כפי שהיה בקוד הקודם לנוחות)
        days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        selected_day = st.selectbox('Select a Day', options=days_order, index=0)

        # סינון הנתונים
        filtered_rides = rides[rides['day_of_week'] == selected_day]

        # --- יצירת טורים רחבים ---
        col1, col2 = st.columns(2)

        # --- גרף 1 (שמאל) ---
        with col1:
            with st.container(border=True):
                st.subheader("Average Duration")
                line_data = filtered_rides.groupby('hour')['duration_minutes'].mean().reset_index()
                fig_line = px.line(line_data, x='hour', y='duration_minutes',
                                   line_shape='spline', render_mode='svg')
                fig_line.update_traces(mode='lines+markers')
                fig_line.update_layout(margin=dict(l=20, r=20, t=20, b=20))

                # --- 2. הגדרת גובה קבוע לקבלת מראה ריבועי ---
                # use_container_width=True דואג לרוחב, height=550 דואג לגובה
                st.plotly_chart(fig_line, use_container_width=True, height=550)

        # --- גרף 2 (ימין) ---
        with col2:
            with st.container(border=True):
                st.subheader("Ride Distribution")
                fig_hist = px.histogram(filtered_rides, x='hour', nbins=15,
                                        color_discrete_sequence=['#ff4b4b'])
                fig_hist.update_layout(bargap=0.1, margin=dict(l=20, r=20, t=20, b=20))

                # --- 2. הגדרת גובה קבוע גם כאן ---
                st.plotly_chart(fig_hist, use_container_width=True, height=550)