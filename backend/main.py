import os
import io
import torch
import shutil
import uvicorn
import numpy as np
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from PIL import Image

from engine.encoder import VideoEncoder
from engine.database import VectorDB
from engine.optimizer import match_clips_to_curve
from engine.perturbator import LatentPerturbator
from ingest import ingest_video
from compositor import render_edl

# Configuration
DATA_DIR = os.getenv("DATA_DIR", "backend/data")
DB_PATH = os.path.join(DATA_DIR, "vector_db")
LATENTS_DIR = os.path.join(DATA_DIR, "latents")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LATENTS_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# App Initialization
app = FastAPI(title="Entropy Edit API", description="Parametric Data Orchestrator Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
class EngineState:
    encoder: Optional[VideoEncoder] = None
    db: Optional[VectorDB] = None
    perturbator: Optional[LatentPerturbator] = None
    ingest_status: Dict[str, str] = {} # task_id -> status

state = EngineState()

@app.on_event("startup")
async def startup_event():
    print("Initializing Engines...")
    state.encoder = VideoEncoder() # CLIP + VAE
    state.perturbator = LatentPerturbator() # DiT
    state.db = VectorDB(dimension=512)

    # Load DB if exists
    if os.path.exists(DB_PATH + ".index"):
        print("Loading existing VectorDB...")
        state.db.load(DB_PATH)
    else:
        print("Created new VectorDB.")

# Models
class GaussianNode(BaseModel):
    peak_t: float
    sigma: float
    amplitude: float

class CurvePoint(BaseModel):
    time: float
    value: float

class PreviewRequest(BaseModel):
    timestamp: float
    curve_data: List[CurvePoint]
    nodes: List[GaussianNode]
    duration: float = 100.0

class RenderRequest(BaseModel):
    curve_data: List[CurvePoint]
    nodes: List[GaussianNode]
    target_length: float
    time_scaling: Dict[str, Any] = {}
    output_filename: str = "output.mp4"

# Endpoints

@app.get("/assets")
async def get_assets():
    """
    Returns a list of all ingested video clips (metadata).
    Groups them by source filename.
    """
    if not state.db or len(state.db.metadata) == 0:
        return {"assets": []}

    # Group by filename
    assets = {}
    for meta in state.db.metadata:
        filename = meta.get('filename', 'unknown')
        if filename not in assets:
            assets[filename] = []
        assets[filename].append(meta)

    return {"assets": assets, "total_clips": len(state.db.metadata)}

def run_ingest(file_path: str, filename: str):
    try:
        state.ingest_status[filename] = "processing"
        # Note: ingest_video expects paths.
        ingest_video(file_path, DB_PATH, DATA_DIR, sample_interval_sec=1.0)

        # Reload DB to reflect changes - naive lock-less reload
        state.db = VectorDB(dimension=512)
        state.db.load(DB_PATH)
        state.ingest_status[filename] = "completed"
    except Exception as e:
        print(f"Ingest failed: {e}")
        state.ingest_status[filename] = f"failed: {e}"

@app.post("/ingest")
async def ingest_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Uploads a video and ingests it into the system via background task.
    """
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    state.ingest_status[file.filename] = "queued"
    background_tasks.add_task(run_ingest, file_location, file.filename)

    return {"status": "queued", "task_id": file.filename}

@app.get("/ingest/status/{filename}")
async def get_ingest_status(filename: str):
    status = state.ingest_status.get(filename, "unknown")
    return {"filename": filename, "status": status}

@app.post("/edl")
def edl_endpoint(request: RenderRequest):
    """
    Simulates the EDL without rendering.
    Returns the list of clips with their start/end times.
    """
    if not state.db or len(state.db.metadata) == 0:
        return {"edl": []}

    curve_data_dicts = [c.model_dump() for c in request.curve_data]
    nodes_dicts = [n.model_dump() for n in request.nodes]

    # For EDL simulation, we reset random seed to ensure consistency with preview
    np.random.seed(42)

    edl = match_clips_to_curve(
        curve_data=curve_data_dicts,
        vector_db=state.db,
        target_length_sec=request.target_length,
        clip_granularity_sec=2.0,
        time_scaling_options=request.time_scaling,
        filter_nodes=nodes_dicts
    )
    return {"edl": edl}

@app.post("/preview")
def preview_endpoint(request: PreviewRequest):
    """
    Real-time preview:
    1. Replays optimizer logic to find EXACT clip at `timestamp`.
    2. Calculates `filter_weight`.
    3. Perturbs latent.
    4. Returns JPEG image.
    """
    if not state.db or len(state.db.metadata) == 0:
        raise HTTPException(status_code=400, detail="Database empty. Ingest video first.")

    from engine.optimizer import get_bell_shape_weight
    from engine.simulator import find_clip_at_time

    curve_dicts = [c.model_dump() for c in request.curve_data]
    nodes_dicts = [n.model_dump() for n in request.nodes]

    # 1. Find the clip deterministically
    meta = find_clip_at_time(
        timestamp=request.timestamp, # Normalized
        curve_data=curve_dicts,
        vector_db=state.db,
        duration=request.duration,
        granularity=2.0
    )

    if not meta:
        raise HTTPException(status_code=404, detail="No clip found for this time.")

    # 2. Filter Weight
    weight = get_bell_shape_weight(request.timestamp, nodes_dicts)

    # 3. Load & Perturb
    latent_path = meta['latent_path']
    if not os.path.exists(latent_path):
         # Fallback if specific file missing
         raise HTTPException(status_code=404, detail=f"Latent file {latent_path} not found.")

    latent = torch.load(latent_path, map_location=state.encoder.device)

    # Perturb
    perturbed_latent = state.perturbator.perturb(latent, noise_level=weight)

    # Decode
    images = state.encoder.decode_latents(perturbed_latent)
    img = images[0]

    # Convert to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    return StreamingResponse(img_byte_arr, media_type="image/jpeg")

@app.post("/render")
def render_endpoint(request: RenderRequest):
    """
    Full Render:
    1. Generate EDL from curve & nodes.
    Runs in a threadpool to avoid blocking.
    2. Render video.
    """
    if not state.db or len(state.db.metadata) == 0:
        raise HTTPException(status_code=400, detail="Database empty.")

    # Convert Pydantic to Dicts
    curve_data_dicts = [c.model_dump() for c in request.curve_data]
    nodes_dicts = [n.model_dump() for n in request.nodes]

    # Generate EDL
    edl = match_clips_to_curve(
        curve_data=curve_data_dicts,
        vector_db=state.db,
        target_length_sec=request.target_length,
        clip_granularity_sec=2.0, # Fixed for now or param
        time_scaling_options=request.time_scaling,
        filter_nodes=nodes_dicts
    )

    output_path = os.path.join(DATA_DIR, request.output_filename)

    # Render
    try:
        render_edl(edl, output_path, state.encoder, state.perturbator, latent_dir=LATENTS_DIR)

        return {"status": "success", "output_path": output_path}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
