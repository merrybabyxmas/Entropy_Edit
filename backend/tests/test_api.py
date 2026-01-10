import os
import pytest
from fastapi.testclient import TestClient
import numpy as np
import cv2
from main import app, DATA_DIR, DB_PATH, UPLOAD_DIR, LATENTS_DIR
import shutil
from io import BytesIO

@pytest.fixture(scope="module", autouse=True)
def setup_test_data():
    # clear backend/data before tests to ensure clean state
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    os.makedirs(DATA_DIR)
    os.makedirs(LATENTS_DIR)
    os.makedirs(UPLOAD_DIR)

    # Create a dummy video
    video_path = "test_video_api.mp4"
    width, height = 256, 256
    fps = 24
    duration = 1
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
    for i in range(fps * duration):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(frame, (i, 100), (i+50, 150), (255, 0, 0), -1)
        out.write(frame)
    out.release()

    yield video_path

    # Cleanup
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)

def test_api_flow(setup_test_data):
    """
    Runs ingest, preview, and render in a single session to persist state.
    """
    video_path = setup_test_data

    # Use TestClient as context manager to trigger lifecycle events (startup)
    with TestClient(app) as client:

        # 1. Ingest
        with open(video_path, "rb") as f:
            response = client.post("/ingest", files={"file": ("test_video.mp4", f, "video/mp4")})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert os.path.exists(DB_PATH + ".index")

        # 2. Preview
        payload = {
            "timestamp": 0.5,
            "curve_val": 0.5,
            "nodes": [
                {"peak_t": 0.5, "sigma": 0.1, "amplitude": 1.0}
            ]
        }

        response = client.post("/preview", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"

        # 3. Render
        render_payload = {
            "curve_data": [
                {"time": 0.0, "value": 0.0},
                {"time": 1.0, "value": 1.0}
            ],
            "nodes": [
                {"peak_t": 0.5, "sigma": 0.1, "amplitude": 0.8}
            ],
            "target_length": 2.0,
            "output_filename": "api_test_output.mp4"
        }

        response = client.post("/render", json=render_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert os.path.exists(data["output_path"])
