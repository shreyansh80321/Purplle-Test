import streamlit as st
import requests
import pandas as pd

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Purplle Store Intelligence",
    layout="wide"
)

st.title("Purplle Store Intelligence Dashboard")
st.caption("CPU-first CCTV analytics system for entries, funnel, events, and anomalies.")

try:
    metrics_response = requests.get(f"{API_BASE_URL}/metrics", timeout=5)
    funnel_response = requests.get(f"{API_BASE_URL}/funnel", timeout=5)
    events_response = requests.get(f"{API_BASE_URL}/events", timeout=5)
    anomalies_response = requests.get(f"{API_BASE_URL}/anomalies", timeout=5)

    metrics = metrics_response.json()
    funnel = funnel_response.json()
    events = events_response.json()
    anomalies = anomalies_response.json()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Entries", metrics["total_entries"])
    col2.metric("Active Sessions", metrics["active_sessions"])
    col3.metric("Billing Visits", metrics["billing_visits"])
    col4.metric("Conversion Rate", f'{metrics["conversion_rate"]:.2f}%')

    st.subheader("Store Funnel")

    funnel_df = pd.DataFrame(
        [
            {"stage": "Entered Store", "count": funnel["entered_store"]},
            {"stage": "Visited Product Zone", "count": funnel["visited_product_zone"]},
            {"stage": "Visited Billing Zone", "count": funnel["visited_billing_zone"]},
            {"stage": "Converted", "count": funnel["converted"]},
        ]
    )

    st.bar_chart(funnel_df, x="stage", y="count")

    st.subheader("Recent Events")
    st.json(events)

    st.subheader("Anomalies")
    st.json(anomalies)

except Exception as e:
    st.error("Could not connect to FastAPI backend.")
    st.exception(e)