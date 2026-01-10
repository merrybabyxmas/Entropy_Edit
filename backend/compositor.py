import os
import torch
import numpy as np
from typing import List, Dict, Any
from moviepy import *
from PIL import Image
from engine.encoder import VideoEncoder
from engine.perturbator import LatentPerturbator

def render_edl(
    edl: List[Dict[str, Any]],
    output_path: str,
    encoder: VideoEncoder,
    perturbator: LatentPerturbator,
    latent_dir: str
):
    """
    Renders the Edit Decision List to a video file using MoviePy.

    Args:
        edl: List of clip information.
        output_path: Destination file path.
        encoder: VideoEncoder instance (for decoding latents).
        perturbator: LatentPerturbator instance.
        latent_dir: Directory containing the .pt latent files.
    """

    main_clips = []
    overlay_clips = []

    print(f"Rendering {len(edl)} clips...")

    # Track current time for main channel to know where to place overlays?
    # Or does EDL have absolute timestamps?
    # optimizer.py sets 'timeline_start'.

    max_duration = 0.0

    for clip_info in edl:
        filename = clip_info["source_clip_id"]
        timestamp = clip_info["source_time"]

        # Construct path using parameterized directory
        latent_path = os.path.join(latent_dir, f"{filename}_{timestamp:.2f}.pt")

        if not os.path.exists(latent_path):
            print(f"Warning: Latent file {latent_path} not found. Skipping.")
            continue

        # Load Latent
        latent = torch.load(latent_path, map_location=encoder.device)

        # Apply Perturbation
        noise_level = clip_info.get("filter_weight", 0.0)
        perturbed_latent = perturbator.perturb(latent, noise_level=noise_level * 0.5)

        # Decode
        images = encoder.decode_latents(perturbed_latent)
        img = images[0]

        # Create MoviePy Clip
        clip_duration = clip_info["duration"]
        start_time = clip_info.get("timeline_start", 0.0)

        # Note: In MoviePy 2.x, ImageClip handles numpy arrays directly.
        mp_clip = ImageClip(np.array(img)).with_duration(clip_duration).with_start(start_time)

        is_overlay = clip_info.get("overlay", False)

        if is_overlay:
            # Overlay Logic:
            # Scale down and position?
            # Default to Picture-in-Picture logic if overlay
            # Position logic should come from EDL or default (e.g., bottom right)

            # Resize
            # MoviePy 2.x: .resized(new_size=0.4) for factor?
            # Signature: (self, new_size: Union[tuple, float, <built-in function callable>] = None, height: int = None, width: int = None, apply_to_mask: bool = True)
            # So `new_size` can be a float.
            mp_clip = mp_clip.resized(new_size=0.4)

            # Position
            # MoviePy 2.x: .with_position(...)
            pos_x = clip_info.get("pos_x", "right")
            pos_y = clip_info.get("pos_y", "bottom")
            mp_clip = mp_clip.with_position((pos_x, pos_y))

            overlay_clips.append(mp_clip)
        else:
            main_clips.append(mp_clip)

        end_time = start_time + clip_duration
        if end_time > max_duration:
            max_duration = end_time

    if not main_clips:
        print("No main clips to render.")
        return

    # In MoviePy 2.x, CompositeVideoClip works with a list of clips.
    # Main clips (background) need to be sequenced if they are just segments?
    # If they have 'start_time', we can just throw them all into CompositeVideoClip.
    # But usually, main channel is a sequence.
    # If optimizer sets 'timeline_start' correctly for a sequence, we can use CompositeVideoClip for everything.

    print("Compositing clips...")
    final_clip = CompositeVideoClip(main_clips + overlay_clips, size=main_clips[0].size)
    final_clip = final_clip.with_duration(max_duration)

    print(f"Writing to {output_path}...")
    final_clip.write_videofile(output_path, fps=24, codec="libx264")
    print("Render complete.")
