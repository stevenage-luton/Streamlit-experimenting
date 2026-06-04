import streamlit as st
import requests
import pandas as pd

import plotly.express as px
from datetime import datetime


APP_ID = "TfLInformation "
APP_KEY = "969a0c054c304a08a54ed17da6b5b4ca"



STATIONS = {
    "Oxford Circus": "940GZZLUOXC",
    "Waterloo": "940GZZLUWLO",
    "King's Cross St Pancras": "940GZZLUKSX",
    "Victoria": "940GZZLUVIC",
    "Liverpool Street": "940GZZLULVT",
    "Bank": "940GZZLUBNK",
    "West Ham": "940GZZLUWHM",
    "Stratford": "940GZZLUSTD",
}

station_name = st.selectbox(
    "Select Station",
    list(STATIONS.keys())
)

station_id = STATIONS[station_name]

crowding_url = (
    f"https://api.tfl.gov.uk/crowding/{station_id}"
)

live_crowding_url = (
    f"https://api.tfl.gov.uk/crowding/{station_id}/Live"
)


crowding = requests.get(crowding_url).json()



rows = []

for day_data in crowding["daysOfWeek"]:

    day = day_data["dayOfWeek"]

    for band in day_data["timeBands"]:
        rows.append({
            "day": day,
            "time": band["timeBand"].split("-")[0],
            "crowding": band["percentageOfBaseLine"] * 100
        })

df = pd.DataFrame(rows)

fig = px.line(
    df,
    x="time",
    y="crowding",
    color="day",
    title="Station Crowding by Day of Week",
    subtitle= station_name,
    labels={
        "crowding": "% of Baseline Demand",
        "time": "Time of Day"
    }
)

fig.update_layout(
    height=600,
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader(f"Live Crowding: {station_name}")

if st.button("Refresh live data"):
    st.rerun()

live_resp = requests.get(live_crowding_url, params={"app_id": APP_ID.strip(), "app_key": APP_KEY})
live_data = live_resp.json()

now = datetime.now()
current_day = now.strftime("%a").upper()
current_time_str = f"{now.hour:02d}:{(now.minute // 15) * 15:02d}"
expected_row = df[(df["day"] == current_day) & (df["time"] == current_time_str)]
expected_pct = expected_row["crowding"].iloc[0] if not expected_row.empty else None


if live_data.get("dataAvailable"):
    pct = live_data["percentageOfBaseline"] * 100
    if pct < 40:
        label = "Quiet"
    elif pct < 70:
        label = "Busy"
    elif pct < 100:
        label = "Very Busy"
    else:
        label = "Busier than it has ever been"
    col1, col2, col3 = st.columns(3)
    if expected_pct is not None:
        delta = pct - expected_pct
        col1.metric("Live crowding", f"{pct:.0f}%", delta=f"{delta:+.0f}% vs expected", delta_color="inverse")
        col2.metric(f"Expected ({current_day} {current_time_str})", f"{expected_pct:.0f}%")
    else:
        col1.metric("Live crowding", f"{pct:.0f}%")
        col2.metric("Expected", "No data for this time")
    col3.metric("Status", label)
    st.progress(min(pct / 100, 1.0))
else:
    st.info("Live crowding data is not currently available for this station.")
