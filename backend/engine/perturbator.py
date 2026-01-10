import torch
import numpy as np

class LatentPerturbator:
    def __init__(self, device: str = None):
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")

    def perturb(self, latent: torch.Tensor, noise_level: float = 0.0, channel_shift: float = 0.0) -> torch.Tensor:
        """
        Applies deterministic perturbation to the latent vector.

        Args:
            latent: Input latent tensor (C, H, W) or (B, C, H, W)
            noise_level: Intensity of Gaussian noise (0.0 to 1.0)
            channel_shift: Amount to shift channel values (pseudo color shift)
        """
        latent = latent.to(self.device)

        if latent.ndim == 3:
            latent = latent.unsqueeze(0) # Make batch

        # 1. Noise Injection
        if noise_level > 0:
            # Deterministic noise based on latent content (to be stable across frames if needed)
            # Or truly random? The prompt says "Deterministic".
            # Let's use a generator seeded by the sum of the latent to make it 'content-aware' deterministic
            seed = int(latent.sum().item() * 1000) % 2**32
            generator = torch.Generator(device=self.device).manual_seed(seed)
            noise = torch.randn(latent.shape, device=self.device, generator=generator)

            # Mix: (1 - alpha) * Original + alpha * Noise
            # But usually we just add noise.
            # Let's Scale noise by sigma
            sigma = noise_level * 2.0 # Arbitrary scaling
            latent = latent + noise * sigma

        # 2. Channel Shift (Simulates glitch/color distortion)
        if channel_shift > 0:
             # Shift channels cyclically or add constant
             # Let's simply roll the channels if shift is high enough
             shift_int = int(channel_shift * 4) # 4 channels in VAE usually
             if shift_int > 0:
                 latent = torch.roll(latent, shifts=shift_int, dims=1)

             # Also add a bias to a specific channel based on shift float
             latent[:, 0, :, :] += channel_shift

        return latent
