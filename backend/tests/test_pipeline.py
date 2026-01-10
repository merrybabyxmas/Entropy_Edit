import cv2
import numpy as np
import os
import pytest
from engine.encoder import VideoEncoder
from engine.database import VectorDB
from engine.optimizer import match_clips_to_curve
from engine.perturbator import LatentPerturbator
from ingest import ingest_video
from compositor import render_edl

# Setup paths
DATA_DIR = "backend/data_test"
VIDEO_PATH = os.path.join(DATA_DIR, "test_video.mp4")
DB_PATH = os.path.join(DATA_DIR, "test_db")
OUTPUT_VIDEO_PATH = os.path.join(DATA_DIR, "final_output.mp4")

@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    """Create dummy video and directories"""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Create a dummy video: moving square
    width, height = 256, 256
    fps = 24
    duration = 2 # seconds
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(VIDEO_PATH, fourcc, fps, (width, height))

    for i in range(fps * duration):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Moving blue square
        x = int((i / (fps * duration)) * width)
        cv2.rectangle(frame, (x, 100), (x+50, 150), (255, 0, 0), -1)
        out.write(frame)

    out.release()
    yield
    # Cleanup could go here, but useful to inspect artifacts

def test_pipeline_integration():
    """
    Tests the full pipeline: Ingest -> Optimize -> Perturb -> Render
    """

    # 1. Ingest
    print("\n--- Step 1: Ingestion ---")
    ingest_video(VIDEO_PATH, DB_PATH, DATA_DIR, sample_interval_sec=0.5)

    assert os.path.exists(DB_PATH + ".index")
    assert os.path.exists(DB_PATH + ".meta")
    latents_dir = os.path.join(DATA_DIR, "latents")
    assert os.path.exists(latents_dir)
    assert len(os.listdir(latents_dir)) > 0

    # 2. Optimize (Generate EDL)
    print("\n--- Step 2: Optimization ---")
    db = VectorDB(512)
    db.load(DB_PATH)

    # Define a simple curve: High similarity then low
    curve_data = [
        {'time': 0.0, 'value': 1.0},
        {'time': 0.5, 'value': 0.0},
        {'time': 1.0, 'value': 1.0}
    ]

    edl = match_clips_to_curve(
        curve_data=curve_data,
        vector_db=db,
        target_length_sec=2.0,
        clip_granularity_sec=0.5
    )

    # Add a fake overlay clip to test overlay logic
    edl.append({
        "time_start": 0.0,
        "timeline_start": 0.5, # Start overlay at 0.5s
        "duration": 1.0,
        "source_clip_id": edl[0]["source_clip_id"], # Reuse first clip
        "source_time": edl[0]["source_time"],
        "overlay": True,
        "pos_x": "center",
        "pos_y": "center"
    })

    assert len(edl) == 5 # 4 main + 1 overlay

    # 3. Render (Compositor + Perturbator)
    print("\n--- Step 3: Rendering ---")
    encoder = VideoEncoder() # Re-init encoder (ignoring singleton overhead for test)
    perturbator = LatentPerturbator()

    # Pass the correct latent_dir
    render_edl(edl, OUTPUT_VIDEO_PATH, encoder, perturbator, latent_dir=latents_dir)

    assert os.path.exists(OUTPUT_VIDEO_PATH)
    file_size = os.path.getsize(OUTPUT_VIDEO_PATH)
    print(f"Output video size: {file_size} bytes")
    assert file_size > 1000 # Should be substantial

if __name__ == "__main__":
    test_pipeline_integration()
