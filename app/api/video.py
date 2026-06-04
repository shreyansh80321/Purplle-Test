from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from pathlib import Path
import shutil
import uuid

from app.vision.processor import VideoProcessor
from scripts.export_events_jsonl import export_events_jsonl

router = APIRouter(prefix="/video", tags=["video-processing"])

UPLOAD_DIR = Path("data/raw/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EVENT_LOG_PATH = Path("outputs/event_log.jsonl")
EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class VideoProcessRequest(BaseModel):
    video_path: str
    store_id: str = "brigade_bangalore"
    frame_skip: int = 3


def _process_and_export(processor: VideoProcessor):
    result = processor.process()
    exported_count, exported_path = export_events_jsonl(str(EVENT_LOG_PATH))
    return result, exported_count, exported_path


@router.post("/process")
def process_video(request: VideoProcessRequest):
    path = Path(request.video_path)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Video file not found: {request.video_path}"
        )

    processor = VideoProcessor(
        video_path=request.video_path,
        store_id=request.store_id,
        camera_id="auto",
        frame_skip=request.frame_skip,
    )

    result, exported_count, exported_path = _process_and_export(processor)

    return {
        "status": "success",
        "message": "Video processed using auto-calibration.",
        "result": result,
        "event_log": {
            "path": str(exported_path),
            "event_count": exported_count,
        },
    }


@router.post("/upload-process")
def upload_and_process_video(
    file: UploadFile = File(...),
    store_id: str = Form("brigade_bangalore"),
    frame_skip: int = Form(3),
):
    allowed_extensions = {".mp4", ".avi", ".mov", ".mkv"}

    original_name = Path(file.filename).name
    extension = Path(original_name).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only video files are allowed: .mp4, .avi, .mov, .mkv"
        )

    safe_name = f"{uuid.uuid4()}{extension}"
    saved_path = UPLOAD_DIR / safe_name

    with saved_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    processor = VideoProcessor(
        video_path=str(saved_path),
        store_id=store_id,
        camera_id="auto",
        frame_skip=frame_skip,
    )

    result, exported_count, exported_path = _process_and_export(processor)

    return {
        "status": "success",
        "message": "Uploaded video processed using auto-calibration.",
        "original_filename": original_name,
        "saved_path": str(saved_path),
        "result": result,
        "event_log": {
            "path": str(exported_path),
            "event_count": exported_count,
        },
    }
