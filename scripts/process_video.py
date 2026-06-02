import argparse

from app.vision.processor import VideoProcessor


def main():
    parser = argparse.ArgumentParser(
        description="Process CCTV video and generate store intelligence events."
    )

    parser.add_argument("--video", required=True, help="Path to CCTV video file")
    parser.add_argument("--store-id", default="brigade_bangalore")
    parser.add_argument("--frame-skip", type=int, default=3)

    args = parser.parse_args()

    processor = VideoProcessor(
        video_path=args.video,
        store_id=args.store_id,
        camera_id="auto",
        frame_skip=args.frame_skip,
    )

    result = processor.process()
    print(result)


if __name__ == "__main__":
    main()