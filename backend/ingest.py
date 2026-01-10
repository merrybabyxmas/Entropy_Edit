import cv2
import os
import numpy as np
import torch
import argparse
from typing import List
from engine.encoder import VideoEncoder
from engine.database import VectorDB

def ingest_video(
    video_path: str,
    db_path: str,
    output_dir: str,
    sample_interval_sec: float = 2.0
):
    """
    Ingests a video:
    1. Reads video
    2. Extracts frames
    3. Encodes CLIP embeddings -> DB
    4. Encodes VAE latents -> Disk
    """
    if not os.path.exists(video_path):
        print(f"Error: Video file {video_path} not found.")
        return

    os.makedirs(output_dir, exist_ok=True)
    latents_dir = os.path.join(output_dir, "latents")
    os.makedirs(latents_dir, exist_ok=True)

    print(f"Initializing Encoder...")
    encoder = VideoEncoder()

    # Initialize DB (dimension 512 for CLIP ViT-B/32)
    # If DB exists, load it? For now, we assume we append or create new.
    print(f"Initializing Database...")
    db = VectorDB(dimension=512)
    if os.path.exists(db_path + ".index"):
         db.load(db_path)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    interval_frames = int(fps * sample_interval_sec)

    frames_batch = []
    metadata_batch = []
    frame_indices = []

    print(f"Processing video: {video_path} ({duration:.2f}s)")

    count = 0
    saved_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if count % interval_frames == 0:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames_batch.append(frame_rgb)

            timestamp = count / fps
            filename = os.path.basename(video_path)
            latent_filename = f"{filename}_{timestamp:.2f}.pt"

            metadata = {
                "filename": filename,
                "timestamp": timestamp,
                "latent_path": os.path.join(latents_dir, latent_filename),
                "original_width": frame.shape[1],
                "original_height": frame.shape[0]
            }
            metadata_batch.append(metadata)
            frame_indices.append(count)
            saved_count += 1

        count += 1

    cap.release()

    if not frames_batch:
        print("No frames extracted.")
        return

    # Process in batches if memory is an issue, but for prototype do all
    print(f"Encoding {len(frames_batch)} frames...")

    # 1. CLIP Embeddings
    embeddings = encoder.embed_frames(frames_batch)
    db.add(embeddings, metadata_batch)
    db.save(db_path)

    # 2. VAE Latents
    print(f"Encoding Latents...")
    latents = encoder.encode_latents(frames_batch) # Returns Tensor (N, 4, 64, 64) approx

    # Save latents individually
    for i, latent in enumerate(latents):
        # Save as torch tensor
        torch.save(latent.clone(), metadata_batch[i]["latent_path"])

    print(f"Ingestion complete. {saved_count} clips saved.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, required=True, help="Path to input video")
    parser.add_argument("--db", type=str, default="backend/data/vector_db", help="Path to VectorDB prefix")
    parser.add_argument("--out", type=str, default="backend/data", help="Output directory for data")
    args = parser.parse_args()

    ingest_video(args.video, args.db, args.out)
