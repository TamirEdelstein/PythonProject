import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# הגדרות עמוד
st.set_page_config(layout="wide", page_title="Bus Route Analysis")

st.title("ניתוח מסלול ותפוסת קווי אוטובוס")


# --- פונקציה לשליפת ה-Shape (המסלול הגיאוגרפי) ---
def get_route_shape(shape_id):
    if not shape_id:
        return None
    url = "https://open-bus-stride-api.hasadna.org.il/gtfs_shapes/list"
    params = {'shape_id': shape_id}
    res = requests.get(url, params=params)
    if res.status_code == 200:
        data = res.json()
        if data:
            # מיון הנקודות לפי הסדר הנכון של המסלול
            df_shape = pd.DataFrame(data).sort_values('shape_pt_sequence')
            return df_shape
    return None


# --- שלב 1: קלט מהמשתמש ---
with st.container(border=True):
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        line_num = st.text_input("מספר קו (route_short_name):", placeholder="לדוגמה: 1")
    with col_in2:
        city = st.text_input("עיר (route_long_name_contains):", placeholder="לדוגמה: בת ים")

    fetch_data = st.button("טען נתונים וצייר מפה", use_container_width=True)

# לוגיקת שליפת נתונים
if fetch_data and line_num and city:
    # 1. שליפה מ-gtfs_routes
    url_gtfs = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    params_gtfs = {
        'route_short_name': line_num,
        'route_long_name_contains': city,
        'date_from': '2023-01-01',
        'date_to': '2023-01-01'
    }

    res_gtfs = requests.get(url_gtfs, params=params_gtfs)
    if res_gtfs.status_code == 200 and res_gtfs.json():
        route_data = res_gtfs.json()[0]
        line_ref = route_data['line_ref']
        shape_id = route_data.get('shape_id')

        # 2. שליפה מ-siri_rides (נסיעות)
        url_siri = "https://open-bus-stride-api.hasadna.org.il/siri_rides/list"
        params_siri = {
            'limit': -1,
            'gtfs_route__date_from': '2024-01-14',
            'gtfs_route__date_to': '2024-01-20',
            'gtfs_route__line_refs': line_ref
        }
        res_siri = requests.get(url_siri, params=params_siri)

        if res_siri.status_code == 200:
            rides_df = pd.DataFrame(res_siri.json())
            rides_df['scheduled_start_time'] = pd.to_datetime(rides_df['scheduled_start_time'])
            rides_df['hour'] = rides_df['scheduled_start_time'].dt.hour
            rides_df['day_of_week'] = rides_df['scheduled_start_time'].dt.day_name()

            st.session_state['rides_df'] = rides_df
            st.session_state['shape_df'] = get_route_shape(shape_id)
            st.success(f"נמצא קו {line_num}. מזהה Shape: {shape_id}")
    else:
        st.error("לא נמצאו נתונים עבור הקלט שהוזן.")

# --- שלב 2: תצוגה ---
if 'rides_df' in st.session_state:
    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    selected_day = st.selectbox('בחר יום:', options=days_order)

    filtered_rides = st.session_state['rides_df'][st.session_state['rides_df']['day_of_week'] == selected_day]

    st.divider()

    # פריסת מפה משמאל וגרפים מימין
    col_map, col_charts = st.columns([2, 1.5])

    with col_map:
        with st.container(border=True):
            st.subheader("📍 מסלול הקו האמיתי")
            if st.session_state.get('shape_df') is not None:
                df_geo = st.session_state['shape_df']
                fig_map = px.line_mapbox(
                    df_geo,
                    lat="shape_pt_lat",
                    lon="shape_pt_lon",
                    zoom=11,
                    height=800
                )
                # קו כחול עבה ובולט
                fig_map.update_traces(line=dict(width=6, color="blue"))
                fig_map.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 0, "l": 0, "b": 0})
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.warning("לא נמצאו נתוני מסלול גיאוגרפיים (Shapes).")

    with col_charts:
        with st.container(border=True):
            st.markdown("### Average Duration")
            avg_data = filtered_rides.groupby('hour')['duration_minutes'].mean().reset_index()
            fig_l = px.line(avg_data, x='hour', y='duration_minutes', line_shape='spline', markers=True)
            fig_l.update_layout(height=370)
            st.plotly_chart(fig_l, use_container_width=True)

        with st.container(border=True):
            st.markdown("### Ride Distribution")
            fig_h = px.histogram(filtered_rides, x='hour', nbins=15, color_discrete_sequence=['#ff4b4b'])
            fig_h.update_layout(height=370, bargap=0.1)
            st.plotly_chart(fig_h, use_container_width=True)