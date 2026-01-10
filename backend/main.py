import os
import io
import torch
import shutil
import uvicorn
import numpy as np
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
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
    curve_val: float
    nodes: List[GaussianNode]
    # For preview, we might just need to find *one* clip that matches the current curve state?
    # Or does the user seek through the *timeline*?
    # "Find clip at this timestamp" implies we are previewing the EDL result at time T.
    # To do that, we need the full curve to generate EDL, OR we just simulate the logic for T.
    # Simulating logic for T is faster.

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

@app.post("/ingest")
def ingest_endpoint(file: UploadFile = File(...)):
    """
    Uploads a video and ingests it into the system.
    Runs in a threadpool to avoid blocking the event loop.
    """
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Trigger Ingest (Blocking for now, should be background task in prod)
    # We pass paths relative to our config
    try:
        # Note: ingest_video expects paths.
        ingest_video(file_location, DB_PATH, DATA_DIR, sample_interval_sec=1.0)

        # Reload DB to reflect changes
        state.db = VectorDB(dimension=512)
        state.db.load(DB_PATH)

        return {"status": "success", "message": f"Ingested {file.filename}", "frames": len(state.db.metadata)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/preview")
async def preview_endpoint(
    timestamp: float = Body(...),
    curve_val: float = Body(...),
    nodes: List[GaussianNode] = Body(...)
):
    """
    Real-time preview:
    1. Finds a clip based on `curve_val` (Similarity).
    2. Calculates `filter_weight` from `nodes` at `timestamp`.
    3. Perturbs latent.
    4. Returns JPEG image.
    """
    if not state.db or len(state.db.metadata) == 0:
        raise HTTPException(status_code=400, detail="Database empty. Ingest video first.")

    # 1. Similarity Logic (Simplified version of optimizer logic)
    # If we have no context (current_vector), we pick random or just based on query?
    # We don't have 'current_vector' in a stateless preview request unless passed.
    # Let's assume we pick a random one if curve_val is mid, or high sim to *something*?
    # Actually, the logic "High Curve = High Similarity" implies similarity to the *previous* clip.
    # Without previous context, this is ambiguous.
    # FOR PREVIEW: We might just pick a random clip from the DB to show *effect* application.
    # Or better, user might browse clips.
    # Let's just pick a random clip for now to demonstrate the *perturbation*.

    # Pick a random clip
    import random
    idx = random.randint(0, len(state.db.metadata) - 1)
    meta = state.db.metadata[idx]

    # 2. Filter Weight
    # We need to normalize timestamp if nodes use normalized time (0-1).
    # Assuming the UI passes normalized time for preview context?
    # Or passes absolute time and we normalize?
    # Let's assume timestamp is normalized (0.0 - 1.0) relative to timeline.
    from engine.optimizer import get_bell_shape_weight

    # Convert Pydantic models to dicts
    nodes_dicts = [n.model_dump() for n in nodes]
    weight = get_bell_shape_weight(timestamp, nodes_dicts)

    # 3. Load & Perturb
    latent_path = meta['latent_path']
    if not os.path.exists(latent_path):
         raise HTTPException(status_code=404, detail="Latent file not found.")

    latent = torch.load(latent_path, map_location=state.encoder.device)

    # Perturb
    # DiT perturbation is heavy, so it might take a second.
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
