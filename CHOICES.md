# Choices

## Model Selection Decision

The project uses CPU-only OpenCV motion detection plus centroid tracking instead of YOLO, Torch, Ultralytics, or GPU-bound detectors. This keeps Docker builds fast, avoids any GPU assumption during evaluation, and emphasizes the challenge goal of building an end-to-end system that runs reliably in constrained environments.

## Schema Design Decision

The event schema is designed to stay close to the sample-events JSONL style while remaining practical for SQLite storage. Rich optional fields are stored directly when they are broadly useful, and `meta` JSON is used as an extensibility valve for extra attributes that should not force a migration every time the event contract evolves.

## API Architecture Decision

FastAPI is used for the backend API and Streamlit is kept as a separate dashboard client. This separation keeps analytics logic centralized in the API while the dashboard remains a thin presentation layer that can evolve independently.

## Auto-Calibration Decision

The project deliberately avoids a `cameras.json` dependency. Instead, it infers a camera role from motion patterns so unknown CCTV footage can still be processed. The role classification remains intentionally narrow and interpretable:

- `entrance`
- `inside_store`
- `outside_passby`

## Store Layout Decision

The semantic layout uses approximate normalized camera-space rectangles inspired by the provided layout images. Exact CAD homography is not attempted because the challenge does not provide reliable camera geometry or blueprint correspondences, and pretending otherwise would create misleading precision.

## Metrics Decision

Raw events are allowed to be noisy because fragmented tracking is a realistic CCTV limitation. Business metrics therefore deduplicate visitor identities, exclude `outside_passby` and staff from customer KPIs, and cap conversion-related values so conversion rate never exceeds 100 percent.

## Production Readiness

For a challenge-scale system, production readiness is addressed through:

- Dockerfile and docker-compose support
- API and logic tests
- `.gitignore` and `.dockerignore` protection for videos, databases, and generated runtime data
- export and validation scripts for the required JSONL deliverable

## Limitations And Future Improvements

Current limitations:

- motion-based detection is less precise than a modern detector in crowded scenes
- demographic fields are placeholders unless upstream enrichment is added
- semantic zones are approximate camera-space regions
- queue semantics are inferred heuristically rather than from dedicated checkout sensors

Reasonable future improvements:

- more robust re-identification across fragmented tracks
- optional detector plug-in architecture for stronger crowded-scene performance
- store-specific calibration refinement tools
- richer anomaly analytics and longer-term trend dashboards
