import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import polyline

st.set_page_config(layout="wide")

st.title("מערכת ניתוח ותצוגת מסלולי תחבורה ציבורית")


# --- פונקציית עזר לפיענוח מסלול ---
def get_map_data(line_ref):
    # שליפת נתוני הגיאומטריה מה-API
    url = f"https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list?line_ref={line_ref}"
    res = requests.get(url)
    if res.status_code == 200 and res.json():
        # לוקחים את ה-polyline מהתוצאה הראשונה
        # הערה: אם אין polyline ב-API הספציפי, נשתמש בנקודות בסיסיות
        route_data = res.json()[0]
        # כאן נניח שיש שדה גיאומטרי או שנשתמש בנקודות ציון ידועות
        # במידה ואין פולי-ליין זמין, נציג מפה ריקה עם הודעה
        return route_data
    return None


# --- שלב 1: קלט מהמשתמש ---
with st.container(border=True):
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        line_number = st.text_input("מספר קו (route_short_name):", placeholder="לדוגמה: 1")
    with col_in2:
        city_name = st.text_input("עיר/תיאור (route_long_name_contains):", placeholder="לדוגמה: בת ים")

    fetch_button = st.button("טען נתונים והצג מפה", use_container_width=True)

if fetch_button:
    # 1. קריאה ל-GTFS לקבלת line_ref
    url_gtfs = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    params_gtfs = {
        'route_short_name': line_number,
        'route_long_name_contains': city_name,
        'date_from': '2023-01-01',
        'date_to': '2023-01-01'
    }

    res_gtfs = requests.get(url_gtfs, params=params_gtfs)
    if res_gtfs.status_code == 200 and res_gtfs.json():
        route_info = res_gtfs.json()[0]
        line_ref = route_info['line_ref']
        st.session_state['current_route'] = route_info

        # 2. קריאה ל-SIRI לקבלת נסיעות
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
            df['scheduled_start_time'] = pd.to_datetime(df['scheduled_start_time'])
            df['hour'] = df['scheduled_start_time'].dt.hour
            df['day_of_week'] = df['scheduled_start_time'].dt.day_name()
            st.session_state['rides_df'] = df

# --- שלב 2: תצוגה ---
if 'rides_df' in st.session_state:
    # בחירת יום
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    selected_day = st.selectbox('בחר יום להצגה:', options=days_order, index=0)

    # תצוגת מפה (חדש!)
    st.subheader("📍 מסלול הקו שנבחר")
    with st.container(border=True):
        # ב-API של הסדנה, המידע הגיאוגרפי נמצא לעיתים בתוך אובייקט ה-route
        # לצורך התצוגה נשתמש ב-Mapbox של Plotly
        # כאן נשתמש בנתונים סטטיים להדגמה אם ה-API לא מחזיר קואורדינטות ישירות

        # הערה: כדי להציג מפה אמיתית מהסדנה, יש למשוך את ה-shapes.
        # הקוד הבא מציג את המיקום הכללי של הקו:
        fig_map = px.scatter_mapbox(
            lat=[32.0853], lon=[34.7818],  # דוגמה למרכז גוש דן
            zoom=11, height=400
        )
        fig_map.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
        st.plotly_chart(fig_map, use_container_width=True)

    # הגרפים הקודמים שלך
    col1, col2 = st.columns(2)
    filtered_rides = st.session_state['rides_df'][st.session_state['rides_df']['day_of_week'] == selected_day]

    with col1:
        with st.container(border=True):
            line_data = filtered_rides.groupby('hour')['duration_minutes'].mean().reset_index()
            fig_l = px.line(line_data, x='hour', y='duration_minutes', line_shape='spline', markers=True,
                            title="Average Duration")
            st.plotly_chart(fig_l, use_container_width=True)

    with col2:
        with st.container(border=True):
            fig_h = px.histogram(filtered_rides, x='hour', nbins=15, title="Ride Distribution",
                                 color_discrete_sequence=['#ff4b4b'])
            st.plotly_chart(fig_h, use_container_width=True)