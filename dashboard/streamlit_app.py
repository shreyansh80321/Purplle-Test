import os

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Purplle Store Intelligence",
    layout="wide",
)

st.title("Purplle Store Intelligence Dashboard")
st.caption("CPU-first CCTV analytics with auto-calibration, semantic store zones, and structured events.")

st.sidebar.header("Video Processing")
uploaded_video = st.sidebar.file_uploader(
    "Upload raw CCTV footage",
    type=["mp4", "avi", "mov", "mkv"],
)
frame_skip = st.sidebar.slider(
    "Frame skip",
    min_value=1,
    max_value=20,
    value=3,
)
reset_before_processing = st.sidebar.checkbox(
    "Reset old events before processing",
    value=True,
)

if st.sidebar.button("Process Uploaded Video"):
    if uploaded_video is None:
        st.sidebar.error("Please upload a video first.")
    else:
        with st.spinner("Processing uploaded video on CPU..."):
            if reset_before_processing:
                requests.delete(f"{API_BASE_URL}/events/reset", timeout=30)

            files = {
                "file": (
                    uploaded_video.name,
                    uploaded_video.getvalue(),
                    uploaded_video.type,
                )
            }
            data = {
                "store_id": "brigade_bangalore",
                "frame_skip": str(frame_skip),
            }
            response = requests.post(
                f"{API_BASE_URL}/video/upload-process",
                files=files,
                data=data,
                timeout=900,
            )

            if response.status_code == 200:
                result = response.json()
                st.sidebar.success("Video uploaded and processed successfully.")
                st.sidebar.json(result)
                st.session_state["last_camera_role"] = result.get("result", {}).get("camera_role")
                st.rerun()
            else:
                st.sidebar.error(response.text)

try:
    metrics = requests.get(f"{API_BASE_URL}/metrics", timeout=5).json()
    funnel = requests.get(f"{API_BASE_URL}/funnel", timeout=5).json()
    events = requests.get(f"{API_BASE_URL}/events", timeout=5).json()
    anomalies = requests.get(f"{API_BASE_URL}/anomalies", timeout=5).json()
    layout_response = requests.get(f"{API_BASE_URL}/layout", timeout=5)
    layout_data = layout_response.json() if layout_response.ok else None

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Entries", metrics["total_entries"])
    col2.metric("Unique Visitors", metrics["unique_visitors"])
    col3.metric("Billing Visits", metrics["billing_visits"])
    col4.metric("Conversion Rate", f'{metrics["conversion_rate"]:.2f}%')

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Total Exits", metrics["total_exits"])
    col6.metric("Active Sessions", metrics["active_sessions"])
    col7.metric("Estimated Conversions", metrics["estimated_conversions"])
    col8.metric("Anomaly Count", metrics["anomaly_count"])

    if events["events"]:
        latest_camera_role = events["events"][0].get("meta", {}).get("camera_role")
        st.caption(f"Latest processed camera role: `{latest_camera_role or 'unknown'}`")

    st.subheader("Store Funnel")
    funnel_df = pd.DataFrame(
        [
            {"stage": "Entered Store", "count": funnel["entered_store"]},
            {"stage": "Visited Revenue Zone", "count": funnel["visited_revenue_zone"]},
            {"stage": "Joined Queue / Cash Counter", "count": funnel["joined_queue_or_visited_cash_counter"]},
            {"stage": "Converted", "count": funnel["converted"]},
        ]
    )
    st.bar_chart(funnel_df, x="stage", y="count")
    st.json(funnel["drop_offs"])

    st.subheader("Event Type Distribution")
    events_df = pd.DataFrame(events["events"])
    if not events_df.empty:
        distribution_df = (
            events_df["event_type"]
            .value_counts()
            .rename_axis("event_type")
            .reset_index(name="count")
        )
        st.bar_chart(distribution_df, x="event_type", y="count")
    else:
        st.info("No events available yet.")

    st.subheader("Recent Events")
    st.dataframe(events_df if not events_df.empty else pd.DataFrame())

    if layout_data:
        st.subheader("Semantic Layout Zones")
        st.caption(layout_data["description"])
        st.dataframe(pd.DataFrame(layout_data["zones"]))

    st.subheader("Anomalies")
    st.json(anomalies)

except Exception as exc:
    st.error("Could not connect to FastAPI backend.")
    st.exception(exc)
