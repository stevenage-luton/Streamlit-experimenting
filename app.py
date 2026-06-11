import streamlit as st
import requests
import pandas as pd
import html as html_lib

import plotly.express as px
from datetime import datetime



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


live_crowding = requests.get(live_crowding_url).json()

now = datetime.now()
current_day = now.strftime("%a").upper()
current_time_str = f"{now.hour:02d}:{(now.minute // 15) * 15:02d}"
expected_row = df[(df["day"] == current_day) & (df["time"] == current_time_str)]
expected_pct = expected_row["crowding"].iloc[0] if not expected_row.empty else None


if live_crowding.get("dataAvailable"):
    pct = live_crowding["percentageOfBaseline"] * 100
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

st.subheader("London Air Quality")

air_quality_data = requests.get("https://api.tfl.gov.uk/AirQuality/").json()

forecasts = {}

for f in air_quality_data["currentForecast"]:
    forecasts[f["forecastType"]] = f

BAND_EMOJI = {"Low": "🟢", "Moderate": "🟡", "High": "🟠", "Very High": "🔴"}
POLLUTANTS = [
    ("nO2Band", "NO₂"),
    ("o3Band", "O₃"),
    ("pM10Band", "PM10"),
    ("pM25Band", "PM2.5"),
    ("sO2Band", "SO₂"),
]

today_tab, tomorrow_tab = st.tabs(["Today", "Tomorrow"])

for tab, forecast_type in [(today_tab, "Current"), (tomorrow_tab, "Future")]:
    with tab:
        forecast = forecasts.get(forecast_type)
        if not forecast:
            st.info("No forecast available.")
            continue

        overall_band = forecast["forecastBand"]
        st.metric("Overall", f"{BAND_EMOJI.get(overall_band, '')} {overall_band}")

        pollutant_cols = st.columns(len(POLLUTANTS))
        for col, (key, name) in zip(pollutant_cols, POLLUTANTS):
            band = forecast[key]
            col.metric(name, f"{BAND_EMOJI.get(band, '')} {band}")

        forecast_text = html_lib.unescape(forecast["forecastText"])
        forecast_text = forecast_text.replace("<br/>", "\n").replace("<br />", "\n").strip()
        st.caption(forecast_text)
