import argparse
import json
from pathlib import Path


ENTRY_EXIT_EVENTS = {"entry", "exit"}
ZONE_EVENTS = {"zone_entered", "zone_exited", "zone_visit"}
QUEUE_EVENTS = {"billing_visit", "queue_completed", "queue_abandoned"}


def _has_any(record, fields):
    return any(record.get(field) is not None for field in fields)


def _missing_fields(record, required_fields):
    missing = []
    for field in required_fields:
        if field not in record or record.get(field) is None:
            missing.append(field)
    return missing


def validate_events_jsonl(path: str = "outputs/event_log.jsonl"):
    target = Path(path)
    if not target.exists():
        print(f"Validation failed: file not found: {target}")
        return 1

    total = 0
    errors = []

    with target.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            total += 1

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                errors.append(f"Line {line_number}: invalid JSON ({exc})")
                continue

            event_type = record.get("event_type")
            if not event_type:
                errors.append(f"Line {line_number}: missing event_type")
                continue

            if event_type in ENTRY_EXIT_EVENTS:
                missing = _missing_fields(record, ["camera_id"])
                if not _has_any(record, ["store_code", "store_id"]):
                    missing.append("store_code|store_id")
                if not _has_any(record, ["event_timestamp", "timestamp"]):
                    missing.append("event_timestamp|timestamp")
                if not _has_any(record, ["id_token", "track_id"]):
                    missing.append("id_token|track_id")
                if missing:
                    errors.append(f"Line {line_number}: entry/exit missing {', '.join(missing)}")
            elif event_type in ZONE_EVENTS:
                missing = _missing_fields(
                    record,
                    ["track_id", "zone_id", "zone_name", "zone_type", "is_revenue_zone"],
                )
                if not _has_any(record, ["event_time", "timestamp"]):
                    missing.append("event_time|timestamp")
                if missing:
                    errors.append(f"Line {line_number}: zone event missing {', '.join(missing)}")
            elif event_type in QUEUE_EVENTS:
                missing = _missing_fields(
                    record,
                    ["track_id", "zone_id", "zone_name", "zone_type", "is_revenue_zone"],
                )
                if missing:
                    errors.append(f"Line {line_number}: queue event missing {', '.join(missing)}")

    if errors:
        print(f"Validation failed for {target}: {len(errors)} issue(s) across {total} event(s).")
        for error in errors:
            print(error)
        return 1

    print(f"Validation passed for {target}: {total} event(s) checked.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate exported store-intelligence JSONL events."
    )
    parser.add_argument(
        "--path",
        default="outputs/event_log.jsonl",
        help="Path to the JSONL file to validate.",
    )
    args = parser.parse_args()
    raise SystemExit(validate_events_jsonl(path=args.path))


if __name__ == "__main__":
    main()
