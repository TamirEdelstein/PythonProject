import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import polyline  # ייבוא הספרייה בתחילת הקובץ

# הגדרת עמוד רחב
st.set_page_config(layout="wide")

st.title("ברוכים הבאים לאפליקציית ניתוח נתוני קווי התחבורה הציבורית בישראל")

# --- שלב 1: קלט מהמשתמש ---
with st.container(border=True):
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        line_number = st.text_input("מספר קו (route_short_name):", placeholder="לדוגמה: 1")
    with col_in2:
        city_name = st.text_input("עיר/תיאור (route_long_name_contains):", placeholder="לדוגמה: בת ים")

    fetch_button = st.button("טען נתונים ונתח", use_container_width=True)

# לוגיקת טעינת נתונים (Session State)
if fetch_button and line_number and city_name:
    # שאילתה 1: GTFS
    url_gtfs = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    params_gtfs = {'route_short_name': line_number, 'route_long_name_contains': city_name, 'date_from': '2023-01-01',
                   'date_to': '2023-01-01'}
    res_gtfs = requests.get(url_gtfs, params=params_gtfs)

    if res_gtfs.status_code == 200 and res_gtfs.json():
        route_info = res_gtfs.json()[0]
        line_ref = route_info['line_ref']

        # שאילתה 2: SIRI
        url_siri = "https://open-bus-stride-api.hasadna.org.il/siri_rides/list"
        params_siri = {'limit': -1, 'gtfs_route__date_from': '2024-01-14', 'gtfs_route__date_to': '2024-01-20',
                       'gtfs_route__line_refs': line_ref}
        res_siri = requests.get(url_siri, params=params_siri)

        if res_siri.status_code == 200:
            df = pd.DataFrame(res_siri.json())
            df['scheduled_start_time'] = pd.to_datetime(df['scheduled_start_time'])
            df['hour'] = df['scheduled_start_time'].dt.hour
            df['day_of_week'] = df['scheduled_start_time'].dt.day_name()
            st.session_state['rides_df'] = df
            st.session_state['route_info'] = route_info

# --- שלב 2: תצוגת המפה והגרפים בפריסה חדשה ---
if 'rides_df' in st.session_state:
    rides = st.session_state['rides_df']

    # בחירת יום
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    selected_day = st.selectbox('בחר יום להצגה:', options=days_order, index=0)
    filtered_rides = rides[rides['day_of_week'] == selected_day]

    st.divider()

    # יצירת שני טורים: שמאל למפה (רחב וגבוה), ימין לגרפים (אחד מעל השני)
    col_map, col_charts = st.columns([2, 1.5])

    import streamlit as st
    import requests
    import pandas as pd
    import plotly.express as px


    # פונקציה ייעודית לשליפת נקודות המסלול המדויקות
    def get_route_geometry(shape_id):
        if not shape_id:
            return None
        # פנייה ל-API של ה-Shapes
        url = "https://open-bus-stride-api.hasadna.org.il/gtfs_shapes/list"
        params = {'shape_id': shape_id}
        res = requests.get(url, params=params)
        if res.status_code == 200:
            data = res.json()
            # ה-API מחזיר רשימת נקודות (lat, lon, sequence)
            return pd.DataFrame(data).sort_values('shape_pt_sequence')
        return None


    # --- בתוך הלוגיקה של האפליקציה (אחרי הקריאה הראשונה ל-GTFS) ---
    if fetch_button:
        # ... (הקוד הקודם שלך לשליפת ה-line_ref) ...
        if res_gtfs.status_code == 200 and res_gtfs.json():
            route_info = res_gtfs.json()[0]
            shape_id = route_info.get('shape_id')  # כאן נמצא המפתח למפה

            # שליפת הגיאומטריה האמיתית
            shape_df = get_route_geometry(shape_id)
            st.session_state['shape_df'] = shape_df

    # --- בתוך תצוגת המפה (col_map) ---
    with col_map:
        if 'shape_df' in st.session_state and st.session_state['shape_df'] is not None:
            df_geo = st.session_state['shape_df']

            fig_map = px.line_mapbox(
                df_geo,
                lat="shape_pt_lat",
                lon="shape_pt_lon",
                zoom=12, height=830
            )
            # עיצוב הקו שיהיה עבה ובולט
            fig_map.update_traces(line=dict(width=6, color="blue"))
            fig_map.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("לא נמצאו נתוני מסלול מפורטים עבור קו זה.")

    with col_charts:
        # גרף 1: Average Duration
        with st.container(border=True):
            st.markdown("### Average Duration")
            line_data = filtered_rides.groupby('hour')['duration_minutes'].mean().reset_index()
            fig_l = px.line(line_data, x='hour', y='duration_minutes', line_shape='spline', markers=True)
            fig_l.update_layout(height=350)
            st.plotly_chart(fig_l, use_container_width=True)

        # גרף 2: Ride Distribution
        with st.container(border=True):
            st.markdown("### Ride Distribution")
            fig_h = px.histogram(filtered_rides, x='hour', nbins=15, color_discrete_sequence=['#ff4b4b'])
            fig_h.update_layout(height=350, bargap=0.1)
            st.plotly_chart(fig_h, use_container_width=True)

    # טבלת נתונים מתחת להכל
    with st.expander("צפה בטבלת הנתונים המלאה"):
        st.dataframe(filtered_rides[['id', 'scheduled_start_time', 'duration_minutes', 'hour', 'day_of_week']],
                     use_container_width=True)