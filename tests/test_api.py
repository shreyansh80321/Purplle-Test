import asyncio
import json

from app.db.event_writer import save_event
from app.main import app


def request_json(method: str, path: str):
    async def run():
        body_chunks = []
        status = None
        headers = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            nonlocal status, headers
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                body_chunks.append(message.get("body", b""))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }

        await app(scope, receive, send)
        body = b"".join(body_chunks).decode("utf-8")
        return status, headers, json.loads(body)

    return asyncio.run(run())


def reset_events():
    status, _, payload = request_json("DELETE", "/events/reset")
    assert status == 200
    assert payload["status"] == "success"


def test_metrics_returns_200():
    reset_events()
    status, _, payload = request_json("GET", "/metrics")
    assert status == 200
    assert isinstance(payload, dict)


def test_events_returns_structured_events():
    reset_events()
    save_event(
        store_id="brigade_bangalore",
        camera_id="cam_test",
        event_type="entry",
        track_id="T1",
        id_token="visitor-1",
        zone="entrance",
        zone_id="entrance",
        zone_name="Entrance",
        zone_type="entrance",
    )

    status, _, payload = request_json("GET", "/events")
    assert status == 200
    assert payload["count"] >= 1
    event = payload["events"][0]
    assert event["event_type"] == "entry"
    assert "zone_id" in event
    assert "id_token" in event


def test_outside_passby_does_not_increase_total_entries():
    reset_events()
    save_event(
        store_id="brigade_bangalore",
        camera_id="cam_test",
        event_type="outside_passby",
        track_id="T-passby",
        zone="outside_passby",
        zone_id="outside_passby",
        zone_name="Outside Passby",
        zone_type="outside_passby",
    )

    status, _, payload = request_json("GET", "/metrics")
    assert status == 200
    assert payload["total_entries"] == 0


def test_staff_entry_does_not_increase_customer_entries():
    reset_events()
    save_event(
        store_id="brigade_bangalore",
        camera_id="cam_test",
        event_type="entry",
        track_id="T-staff",
        id_token="staff-1",
        zone="entrance",
        zone_id="entrance",
        zone_name="Entrance",
        zone_type="entrance",
        is_staff=True,
    )

    status, _, payload = request_json("GET", "/metrics")
    assert status == 200
    assert payload["total_entries"] == 0
    assert payload["unique_visitors"] == 0


def test_queue_completed_contributes_to_estimated_conversions():
    reset_events()
    save_event(
        store_id="brigade_bangalore",
        camera_id="cam_test",
        event_type="entry",
        track_id="T2",
        id_token="visitor-2",
        zone="entrance",
        zone_id="entrance",
        zone_name="Entrance",
        zone_type="entrance",
    )
    save_event(
        store_id="brigade_bangalore",
        camera_id="cam_test",
        event_type="queue_completed",
        track_id="T2",
        id_token="visitor-2",
        zone="cash_counter",
        zone_id="cash_counter",
        zone_name="Cash Counter",
        zone_type="billing_queue",
        is_revenue_zone=True,
        wait_seconds=42,
        abandoned=False,
    )

    status, _, payload = request_json("GET", "/metrics")
    assert status == 200
    assert payload["estimated_conversions"] == 1


def test_conversion_rate_never_exceeds_100_and_fragmented_billing_is_capped():
    reset_events()
    save_event(
        store_id="brigade_bangalore",
        camera_id="cam_test",
        event_type="entry",
        track_id="T-entry",
        id_token="visitor-1",
        zone="entrance",
        zone_id="entrance",
        zone_name="Entrance",
        zone_type="entrance",
    )

    for index in range(12):
        save_event(
            store_id="brigade_bangalore",
            camera_id="cam_test",
            event_type="billing_visit",
            track_id=f"T-frag-{index}",
            zone="cash_counter",
            zone_id="cash_counter",
            zone_name="Cash Counter",
            zone_type="billing_queue",
            is_revenue_zone=True,
        )

    save_event(
        store_id="brigade_bangalore",
        camera_id="cam_test",
        event_type="billing_visit",
        track_id="T-entry",
        id_token="visitor-1",
        zone="cash_counter",
        zone_id="cash_counter",
        zone_name="Cash Counter",
        zone_type="billing_queue",
        is_revenue_zone=True,
    )

    status, _, payload = request_json("GET", "/metrics")
    assert status == 200
    assert payload["total_entries"] == 1
    assert payload["billing_visits"] == 1
    assert payload["estimated_conversions"] == 1
    assert payload["conversion_rate"] == 100.0


def test_estimated_conversions_never_exceed_total_entries():
    reset_events()
    for visitor_id in ("visitor-1", "visitor-2"):
        save_event(
            store_id="brigade_bangalore",
            camera_id="cam_test",
            event_type="entry",
            track_id=visitor_id,
            id_token=visitor_id,
            zone="entrance",
            zone_id="entrance",
            zone_name="Entrance",
            zone_type="entrance",
        )

    for visitor_id in ("visitor-1", "visitor-2"):
        save_event(
            store_id="brigade_bangalore",
            camera_id="cam_test",
            event_type="queue_completed",
            track_id=visitor_id,
            id_token=visitor_id,
            zone="cash_counter",
            zone_id="cash_counter",
            zone_name="Cash Counter",
            zone_type="billing_queue",
            is_revenue_zone=True,
            abandoned=False,
        )

    for index in range(10):
        save_event(
            store_id="brigade_bangalore",
            camera_id="cam_test",
            event_type="zone_entered",
            track_id=f"T-noisy-{index}",
            zone="cash_counter",
            zone_id="cash_counter",
            zone_name="Cash Counter",
            zone_type="billing_queue",
            is_revenue_zone=True,
        )

    status, _, payload = request_json("GET", "/metrics")
    assert status == 200
    assert payload["total_entries"] == 2
    assert payload["billing_visits"] <= payload["total_entries"]
    assert payload["estimated_conversions"] <= payload["total_entries"]
    assert payload["conversion_rate"] <= 100.0


def test_funnel_stages_are_monotonic_with_fragmented_zone_events():
    reset_events()
    save_event(
        store_id="brigade_bangalore",
        camera_id="cam_test",
        event_type="entry",
        track_id="T1",
        id_token="visitor-1",
        zone="entrance",
        zone_id="entrance",
        zone_name="Entrance",
        zone_type="entrance",
    )
    save_event(
        store_id="brigade_bangalore",
        camera_id="cam_test",
        event_type="zone_visit",
        track_id="T1",
        id_token="visitor-1",
        zone="product_shelves",
        zone_id="product_shelves",
        zone_name="Product Shelves",
        zone_type="shelf",
        is_revenue_zone=True,
    )

    for index in range(8):
        save_event(
            store_id="brigade_bangalore",
            camera_id="cam_test",
            event_type="zone_entered",
            track_id=f"T-frag-zone-{index}",
            zone="cash_counter",
            zone_id="cash_counter",
            zone_name="Cash Counter",
            zone_type="billing_queue",
            is_revenue_zone=True,
        )

    status, _, payload = request_json("GET", "/funnel")
    assert status == 200
    assert payload["entered_store"] >= payload["visited_revenue_zone"]
    assert payload["visited_revenue_zone"] >= payload["joined_queue_or_visited_cash_counter"]
    assert payload["joined_queue_or_visited_cash_counter"] >= payload["converted"]
    assert all(value >= 0 for value in payload["drop_offs"].values())
