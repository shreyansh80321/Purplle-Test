import asyncio
import json

from scripts.export_events_jsonl import export_events_jsonl
from scripts.validate_events_jsonl import validate_events_jsonl


def request_json(method: str, path: str):
    from app.main import app

    async def run():
        body_chunks = []
        status = None

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
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
        return status, json.loads(body)

    return asyncio.run(run())


def reset_events():
    status, payload = request_json("DELETE", "/events/reset")
    assert status == 200
    assert payload["status"] == "success"


def test_export_events_jsonl_runs_on_empty_db(tmp_path):
    reset_events()
    output_path = tmp_path / "event_log.jsonl"

    count, exported_path = export_events_jsonl(str(output_path))

    assert count == 0
    assert exported_path == output_path
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == ""


def test_validate_events_jsonl_catches_invalid_json(tmp_path):
    invalid_path = tmp_path / "bad.jsonl"
    invalid_path.write_text('{"event_type": "entry"}\n{not-json}\n', encoding="utf-8")

    exit_code = validate_events_jsonl(str(invalid_path))

    assert exit_code == 1


def test_validate_events_jsonl_accepts_valid_entry(tmp_path):
    valid_path = tmp_path / "good.jsonl"
    record = {
        "event_type": "entry",
        "track_id": "T1",
        "store_id": "brigade_bangalore",
        "camera_id": "cam_test",
        "event_timestamp": "2026-06-04T12:00:00",
    }
    valid_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    exit_code = validate_events_jsonl(str(valid_path))

    assert exit_code == 0
