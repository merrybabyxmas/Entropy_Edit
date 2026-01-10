import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import numpy as np
from typing import List, Union

class VideoEncoder:
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading encoder model {model_name} on {self.device}...")
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)

    def embed_frames(self, frames: List[Union[Image.Image, np.ndarray]]) -> np.ndarray:
        """
        Embeds a list of PIL Images or numpy arrays (frames) into vectors.
        Returns a numpy array of shape (num_frames, embedding_dim).
        """
        # Convert numpy arrays to PIL images if necessary
        pil_frames = []
        for frame in frames:
            if isinstance(frame, np.ndarray):
                pil_frames.append(Image.fromarray(frame))
            else:
                pil_frames.append(frame)

        if not pil_frames:
            return np.array([])

        # Process inputs (batch processing might be needed for large lists,
        # but for prototype we process all at once or let the caller handle batching)
        inputs = self.processor(images=pil_frames, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Get embeddings
        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)

        # Normalize embeddings
        embeddings = outputs / outputs.norm(p=2, dim=-1, keepdim=True)

        return embeddings.cpu().numpy()

    def embed_text(self, text: List[str]) -> np.ndarray:
        """
        Embeds a list of text strings.
        """
        if not text:
            return np.array([])

        inputs = self.processor(text=text, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.get_text_features(**inputs)

        embeddings = outputs / outputs.norm(p=2, dim=-1, keepdim=True)
        return embeddings.cpu().numpy()
