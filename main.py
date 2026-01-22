import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Bus Route Mapper")
st.title("מיפוי קו אוטובוס לפי gtfs_ride_stops")

# --- ממשק קלט ---
with st.sidebar:
    line_num = st.text_input("מספר קו:", value="1")
    city = st.text_input("עיר:", value="בת ים")
    submit = st.button("הפק מפה")

if submit:
    # שלב 1: קבלת line_ref מטבלת gtfs_routes
    url_routes = "https://open-bus-stride-api.hasadna.org.il/gtfs_routes/list"
    params_routes = {
        'route_short_name': line_num,
        'route_long_name_contains': city,
        'date_from': '2023-01-22',
        'date_to': '2023-01-22'
    }

    res_routes = requests.get(url_routes, params=params_routes)

    if res_routes.status_code == 200 and res_routes.json():
        route_data = res_routes.json()[0]
        line_ref = route_data.get('line_ref')
        st.success(f"נמצא line_ref: {line_ref}")

        # שלב 2: שליחת בקשה ל-gtfs_ride_stops עם הפרמטרים המדויקים
        url_stops = "https://open-bus-stride-api.hasadna.org.il/gtfs_ride_stops/list"
        params_stops = {
            'gtfs_route__line_refs': line_ref,
            'arrival_time_from': '2023-01-22T12:31:08.469Z',
            'arrival_time_to': '2023-01-22T14:31:08.469Z',
            'limit': 200  # הגדלנו כדי לוודא שכל המסלול נכנס
        }

        res_stops = requests.get(url_stops, params=params_stops)

        if res_stops.status_code == 200:
            data_stops = res_stops.json()
            df = pd.DataFrame(data_stops)

            if not df.empty:
                # שלב 3: הצגת המפה לפי העמודות gtfs_stop__lat ו- gtfs_stop__lon
                # הערה: אנחנו מוודאים שהעמודות קיימות ב-DataFrame
                lat_col = 'gtfs_stop__lat'
                lon_col = 'gtfs_stop__lon'

                if lat_col in df.columns and lon_col in df.columns:
                    # ניקוי ערכים ריקים ומיון לפי סדר תחנות (stop_sequence)
                    df_map = df.dropna(subset=[lat_col, lon_col])
                    if 'stop_sequence' in df_map.columns:
                        df_map = df_map.sort_values('stop_sequence')

                    # יצירת המפה
                    fig = px.line_mapbox(
                        df_map,
                        lat=lat_col,
                        lon=lon_col,
                        hover_name="gtfs_stop__name" if "gtfs_stop__name" in df.columns else None,
                        zoom=12,
                        height=800
                    )

                    # עיצוב ויזואלי של המסלול
                    fig.update_traces(
                        line=dict(width=6, color="blue"),
                        mode="lines+markers",
                        marker=dict(size=10, color="red")
                    )

                    fig.update_layout(
                        mapbox_style="open-street-map",
                        margin={"r": 0, "t": 0, "l": 0, "b": 0}
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # הצגת הנתונים הגולמיים לבדיקה
                    with st.expander("צפה בנתוני העמודות (Raw Data)"):
                        st.write(df[[lat_col, lon_col, 'stop_sequence']].head())
                else:
                    st.error(f"העמודות {lat_col} או {lon_col} לא נמצאו בנתונים שחזרו.")
            else:
                st.warning("לא חזרו נתונים בטווח הזמן הזה עבור ה-line_ref שנמצא.")
    else:
        st.error("לא נמצא קו תואם ב-gtfs_routes.")