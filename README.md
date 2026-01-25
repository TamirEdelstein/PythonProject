Here is the updated `README.md` including the official API documentation link and a visual representation of the data flow.

---

# Public Transport Data Analysis Dashboard (Israel)

## Overview

This project is an interactive data analysis tool designed to extract, process, and visualize public transportation data in Israel. By connecting to the **Open Bus Stride API** (provided by *The Public Knowledge Workshop* - "Hasadna"), the application allows users to analyze specific bus routes, visualize their geographical paths, and gain insights into travel durations and ride distributions.

**Live Data Tool:** [Open Bus Map Search](https://open-bus-map-search.hasadna.org.il/)

**Official API Documentation:** [Open Bus Stride API Docs](https://open-bus-stride-api.hasadna.org.il/docs#/)

---

## Features

* **Geographical Route Mapping:** Visualizes bus stops and the actual route path on an interactive map using coordinates.
* **Travel Duration Analysis:** Analyzes historical SIRI data to show average travel times across different hours of the day.
* **Ride Frequency Distribution:** Displays the density of bus departures to understand service frequency.
* **Day-of-Week Filtering:** Includes a persistent session state to allow users to compare performance across different days without data loss.

---

## Data Architecture & API Integration

The application integrates three distinct API endpoints to create a unified data model:

### 1. GTFS Routes (`gtfs_routes`)

* **Purpose:** Serves as the primary lookup for bus lines.
* **Function:** Filters the database by `route_short_name` and `route_long_name_contains`.
* **Key Output:** Retrieves the **`line_ref`**, which acts as the primary key for cross-referencing other datasets.

### 2. SIRI Rides (`siri_rides`)

* **Purpose:** Real-time and historical performance analysis.
* **Connection:** Uses the `line_ref` to fetch actual recorded trips.
* **Data Processing:** Calculates durations and departure hours. It generates:
* **Average Duration Chart:** A line graph depicting traffic trends.
* **Ride Distribution Chart:** A histogram showing service frequency.



### 3. GTFS Ride Stops (`gtfs_ride_stops`)

* **Purpose:** Geographical route reconstruction.
* **Connection:** Uses `line_ref` combined with ISO-formatted time filters (`arrival_time_from/to`).
* **Data Processing:** Maps the columns `gtfs_stop__lat` and `gtfs_stop__lon` to a Mapbox interface, ordered by `stop_sequence` to ensure a continuous path.

---

## Tech Stack

* **Language:** Python
* **Web Framework:** Streamlit 
* **Data Handling:** Pandas
* **Visualization:** Plotly Express (Mapbox & Interactive Charts)
* **API Communication:** Requests

---

## How to Run

1. Clone this repository.
2. Install dependencies:
```bash
pip install streamlit pandas plotly requests

```


3. Run the application:
```bash
streamlit run app.py

```



---

## License

This project is open-source and utilizes public data provided by the Ministry of Transport via the Open Bus Stride API project.

---


