# Design

## Problem Framing

The hiring challenge asks for a practical end-to-end store intelligence system rather than a model-heavy research stack. The project therefore focuses on reliable structured event generation, explainable analytics, submission-ready outputs, and deployability on ordinary CPU-only environments.

## System Architecture

The system is split into focused layers:

- FastAPI backend for metrics, funnel, events, layout, and video-processing APIs
- Streamlit dashboard for interactive review
- SQLite for challenge-scale persistence
- OpenCV plus centroid tracking for video understanding
- semantic store layout definitions for business zone labeling
- scripts for processing, exporting, and validating deliverables

## Video Processing Pipeline

The video pipeline uses OpenCV background subtraction to identify moving blobs, filters noise with morphology and size thresholds, and feeds valid detections into a centroid tracker. Track state is then converted into business-facing events such as `entry`, `zone_entered`, `zone_visit`, `billing_visit`, `queue_completed`, and `outside_passby`.

## Auto-Calibration Pipeline

The project intentionally uses auto-calibration only. It samples motion across the frame, estimates whether movement is edge-dominant or center-dominant, and assigns one of three camera roles:

- `entrance`
- `inside_store`
- `outside_passby`

This avoids any dependency on `cameras.json` and supports unknown CCTV footage uploaded during evaluation.

## Store Layout And Semantic Zones

The provided layout images inform a normalized semantic layout in camera space. Zones such as Entrance, FOH customer area, BOH staff area, Cash Counter, Wall Units, Makeup Unit, Product Shelves, and Outside Passby are represented as approximate rectangles. They are business-operational regions, not exact CAD-to-camera projections.

## Event Schema Design

The SQLite event schema stores a core event envelope plus rich optional attributes:

- identity fields such as `track_id`, `id_token`, `store_code`, `is_staff`
- demographic placeholders such as `gender`, `age`, `age_bucket`
- zone fields such as `zone_id`, `zone_name`, `zone_type`, `is_revenue_zone`
- queue fields such as `queue_event_id`, `wait_seconds`, `abandoned`, `queue_position_at_join`
- `meta` JSON for extra context without frequent schema churn

This design preserves backwards compatibility with earlier challenge iterations while aligning more closely with the sample-events style.

## Event Log JSONL Format

The submission includes an exporter that reads `StoreEvent` records and writes one JSON object per line to `outputs/event_log.jsonl`. The format mirrors the sample-events style:

- entry and exit events use `event_timestamp`
- zone events use `event_time`
- queue and billing events use queue-oriented fields such as `queue_join_ts`, `wait_seconds`, and `queue_position_at_join`
- optional values are left nullable rather than forcing synthetic defaults

## Analytics And Metrics

Raw events can be noisy because CCTV tracking may fragment identities. The analytics layer therefore deduplicates by `id_token` when available, otherwise `track_id`, and constrains business metrics to logically valid values:

- staff events do not contribute to customer metrics
- `outside_passby` does not contribute to entry or conversion
- conversion rate is capped at `<= 100%`
- billing and conversion counts are bounded by actual entered visitors

## API Architecture

FastAPI exposes a small challenge-focused surface area:

- `/metrics` for summary business KPIs
- `/funnel` for stage counts and drop-offs
- `/events` for raw structured events
- `/layout` and `/zones` for semantic layout metadata
- `/video/upload-process` for uploaded CCTV processing

This keeps the backend easy to test and easy for the Streamlit client to consume.

## Dashboard Architecture

The Streamlit dashboard is intentionally separate from the API layer. It fetches metrics, funnel data, recent events, anomaly data, and layout summaries from FastAPI and provides an upload-first operator workflow without duplicating analytics logic in the UI.

## Docker And Deployment

Docker Compose runs the API and dashboard together. Video files are mounted through `./data:/app/data`, which keeps large datasets and uploaded footage outside the image. This is important for reproducible builds and for keeping the repository lightweight.

## Testing Strategy

Tests focus on submission-critical behavior:

- API endpoints return structured JSON
- `outside_passby` does not count as entry
- staff entries do not inflate customer metrics
- conversion rate never exceeds 100
- JSONL export works on an empty database
- JSONL validation catches malformed content

Compile checks are also used to catch syntax regressions in analytics, API, and utility scripts.

## Edge Cases

- Staff exclusion: `is_staff=True` events are excluded from customer KPIs
- Re-entry: business metrics deduplicate by visitor identity instead of raw event count
- Outside passby: external walkway motion remains visible in raw events but excluded from conversions
- Fragmented tracks: noisy billing or cash-counter events do not inflate conversions beyond actual entries
- Duplicate suppression: processor-side spatial and temporal filters reduce repeated entry and passby emissions

## AI-Assisted Decisions

AI tools were used as implementation accelerators for scaffolding, debugging, tradeoff exploration, schema alignment, Docker setup guidance, and documentation drafting. They were especially helpful for iterating on event compatibility, metrics edge cases, and challenge deliverables such as JSONL export and validation.

Final engineering decisions were still grounded in the repository context, validated against the current codebase, and checked through targeted tests, compile checks, and manual sanity review. The goal was to use AI to move faster without outsourcing correctness.
