import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from diffusers import AutoencoderKL
import numpy as np
from typing import List, Union

class VideoEncoder:
    def __init__(self, clip_model_name: str = "openai/clip-vit-base-patch32", vae_model_name: str = "stabilityai/sd-vae-ft-mse"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading CLIP model {clip_model_name} on {self.device}...")
        self.clip_model = CLIPModel.from_pretrained(clip_model_name).to(self.device)
        self.clip_processor = CLIPProcessor.from_pretrained(clip_model_name)

        print(f"Loading VAE model {vae_model_name} on {self.device}...")
        self.vae = AutoencoderKL.from_pretrained(vae_model_name).to(self.device)

    def embed_frames(self, frames: List[Union[Image.Image, np.ndarray]]) -> np.ndarray:
        """
        Embeds a list of PIL Images or numpy arrays (frames) into vectors using CLIP.
        Returns a numpy array of shape (num_frames, embedding_dim).
        """
        pil_frames = self._to_pil(frames)

        if not pil_frames:
            return np.array([])

        inputs = self.clip_processor(images=pil_frames, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.clip_model.get_image_features(**inputs)

        embeddings = outputs / outputs.norm(p=2, dim=-1, keepdim=True)
        return embeddings.cpu().numpy()

    def embed_text(self, text: List[str]) -> np.ndarray:
        """
        Embeds a list of text strings using CLIP.
        """
        if not text:
            return np.array([])

        inputs = self.clip_processor(text=text, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.clip_model.get_text_features(**inputs)

        embeddings = outputs / outputs.norm(p=2, dim=-1, keepdim=True)
        return embeddings.cpu().numpy()

    def encode_latents(self, frames: List[Union[Image.Image, np.ndarray]]) -> torch.Tensor:
        """
        Encodes frames into VAE latents.
        Returns a torch Tensor of shape (num_frames, channels, h, w).
        """
        pil_frames = self._to_pil(frames)
        if not pil_frames:
            return torch.empty(0)

        # Resize to 512x512 (or compatible size) for VAE if needed,
        # or assume inputs are correct. VAEs usually expect (B, C, H, W) normalized -1 to 1.

        # Preprocess for VAE
        # 1. Resize/Crop to multiple of 8 (VAE factor)
        # 2. To Tensor
        # 3. Normalize to [-1, 1]

        processed_tensors = []
        for img in pil_frames:
            # Simple resizing to 512x512 for now to ensure consistency
            img_resized = img.resize((512, 512))
            img_arr = np.array(img_resized).astype(np.float32) / 255.0
            img_arr = (img_arr * 2.0) - 1.0 # [0,1] -> [-1, 1]
            processed_tensors.append(torch.from_numpy(img_arr).permute(2, 0, 1)) # HWC -> CHW

        batch_input = torch.stack(processed_tensors).to(self.device)

        with torch.no_grad():
            latents = self.vae.encode(batch_input).latent_dist.sample()
            latents = latents * self.vae.config.scaling_factor

        return latents # Keep on device or cpu? Let's return on CPU for storage/passing

    def decode_latents(self, latents: torch.Tensor) -> List[Image.Image]:
        """
        Decodes VAE latents back to PIL Images.
        """
        latents = latents.to(self.device)
        latents = latents / self.vae.config.scaling_factor

        with torch.no_grad():
            images = self.vae.decode(latents).sample

        images = (images / 2 + 0.5).clamp(0, 1)
        images = images.cpu().permute(0, 2, 3, 1).numpy()
        images = (images * 255).astype(np.uint8)

        return [Image.fromarray(img) for img in images]

    def _to_pil(self, frames: List[Union[Image.Image, np.ndarray]]) -> List[Image.Image]:
        pil_frames = []
        for frame in frames:
            if isinstance(frame, np.ndarray):
                # Ensure RGB
                if frame.ndim == 3 and frame.shape[2] == 3: # RGB/BGR
                     # Assuming RGB input, if BGR (cv2) caller should convert.
                     # We'll assume RGB here to keep it clean.
                     pil_frames.append(Image.fromarray(frame))
                elif frame.ndim == 2: # Grayscale
                     pil_frames.append(Image.fromarray(frame).convert("RGB"))
            else:
                pil_frames.append(frame)
        return pil_frames
