# Purplle Store Intelligence

## Project Overview

Purplle Store Intelligence is a CPU-first CCTV analytics project for the hiring challenge. It ingests uploaded or local store videos, auto-classifies the camera role, generates structured store events, and exposes business analytics through a FastAPI backend plus a Streamlit dashboard.

## What The System Does

- Processes CCTV footage with OpenCV background subtraction and centroid tracking
- Uses auto-calibration only to infer `entrance`, `inside_store`, or `outside_passby`
- Maps movement into semantic store zones inspired by the provided layout images
- Stores rich structured events in SQLite
- Computes `/metrics` and `/funnel` with deduplicated business-safe logic
- Exposes `/events`, `/layout`, `/zones`, and video processing APIs
- Exports event logs to JSONL for challenge submission

## Architecture Summary

- `app/vision/`: CPU-only video processing, tracking, and auto-calibration
- `app/core/`: semantic store layout definitions
- `app/db/`: SQLite model, session, and event writer
- `app/analytics/`: metrics, funnel, anomalies, and event semantics
- `app/api/`: upload and process endpoints
- `dashboard/`: Streamlit dashboard
- `scripts/`: CLI utilities for processing, exporting, and validating outputs
- `outputs/`: submission artifacts such as `event_log.jsonl`

## Docker Run

Run the full stack with:

```powershell
docker compose up --build
```

Available services:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8501`

Docker note: uploaded videos are mounted through `./data:/app/data` and are not baked into the image.

## Local Run

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the FastAPI backend:

```powershell
uvicorn app.main:app --reload
```

Start the Streamlit dashboard:

```powershell
streamlit run dashboard\streamlit_app.py
```

## Terminal Video Processing

```powershell
python -m scripts.process_video --video "data/raw/CAM 1 - zone.mp4" --frame-skip 3
```

## Event Log Export

```powershell
python -m scripts.export_events_jsonl --output outputs/event_log.jsonl
```

## Event Log Validation

```powershell
python -m scripts.validate_events_jsonl --path outputs/event_log.jsonl
```

## API Endpoints

- `/metrics`
- `/funnel`
- `/events`
- `/layout`
- `/zones`
- `/video/upload-process`

## Testing

```powershell
python -m pytest tests
```

## Data And Submission Notes

- Video files and datasets are excluded from GitHub.
- Raw uploads and processed SQLite files stay outside the committed deliverables.
- `outputs/event_log.jsonl` is intentionally kept as a tracked submission artifact.

## Semantic Layout Zones

The assessment layout images are represented as approximate normalized camera-space business zones:

- `entrance`
- `foh_customer_area`
- `boh_staff_area`
- `cash_counter`
- `wall_unit`
- `makeup_unit`
- `product_shelves`
- `outside_passby`

These are operational analytics zones, not exact CAD coordinates or blueprint-to-camera homographies.
