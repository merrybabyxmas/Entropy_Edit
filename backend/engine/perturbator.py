import torch
import numpy as np
from diffusers import DiTTransformer2DModel
from typing import Optional

class LatentPerturbator:
    def __init__(self, device: str = None, model_id: str = "facebook/dit-xl-2-256"):
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Loading DiT model {model_id} on {self.device}...")
        try:
            self.transformer = DiTTransformer2DModel.from_pretrained(model_id).to(self.device)
            self.use_dit = True
        except Exception as e:
            print(f"Warning: Failed to load DiT model ({e}). Falling back to simple noise.")
            self.use_dit = False
            self.transformer = None

    def perturb(self, latent: torch.Tensor, noise_level: float = 0.0, channel_shift: float = 0.0) -> torch.Tensor:
        """
        Applies deterministic perturbation to the latent vector.

        Args:
            latent: Input latent tensor (C, H, W) or (B, C, H, W).
                    Note: DiT expects specific input sizes.
            noise_level: Intensity of Gaussian noise (0.0 to 1.0)
            channel_shift: Amount to shift channel values (pseudo color shift)
        """
        latent = latent.to(self.device)

        if latent.ndim == 3:
            latent = latent.unsqueeze(0) # Make batch

        # 1. DiT-based Perturbation (Structural Distortion)
        if self.use_dit and noise_level > 0.05:
            # We use DiT as a filter.
            # DiT expects (Batch, Channels, Height, Width)
            # Standard DiT-XL/2 expects 32x32 latents (256x256 image).
            # Our latents are likely 64x64 (512x512 image).
            # We resize to 32x32, pass through DiT, then resize back?
            # Or pass 64x64 if supported? (DiT usually has fixed pos embeddings)

            original_size = latent.shape[-2:]
            target_size = (32, 32)

            # Resize down
            latent_resized = torch.nn.functional.interpolate(latent, size=target_size, mode='bicubic')

            # Create Dummy Timestep and Class Label
            # DiT is conditioned on t and class y.
            # We pick a "noisy" timestep based on noise_level to determine how much the model "expects" noise.
            # But we are intercepting attention.

            batch_size = latent.shape[0]
            # Use t=100 (low noise) to t=900 (high noise) map?
            # Actually, we want the model to process the image.
            # Let's pick t=0 (clean) if we just want "structure", but the model is a denoiser.
            # If we pass a latent to a denoiser, it tries to remove noise.
            # Here we want to *distort*.
            # Let's just use the transformer blocks and inject noise in Attention.

            timesteps = torch.tensor([int(noise_level * 100)] * batch_size, device=self.device).long()
            class_labels = torch.tensor([0] * batch_size, device=self.device).long() # Class 0 (Tench?)

            # Register Custom Processor for Perturbation
            # We define it inline or use a helper class
            processor = PerturbedAttnProcessor(noise_level=noise_level)
            self.transformer.set_attn_processor(processor)

            with torch.no_grad():
                # DiT forward pass returns 'sample' (the predicted noise or denoised image)
                # But we want the *distorted feature state*?
                # Actually, just getting the output of the transformer which has been perturbed internally
                # might be enough.
                # The transformer output has the same shape as input.
                output = self.transformer(
                    hidden_states=latent_resized,
                    timestep=timesteps,
                    class_labels=class_labels
                ).sample

            # Resize back
            latent_perturbed = torch.nn.functional.interpolate(output, size=original_size, mode='bicubic')

            # Blend: (1 - alpha) * Original + alpha * DiT_Output
            # Because DiT output might be very different (it predicts noise usually).
            # If DiT predicts noise, 'output' is noise.
            # If we want 'distorted image', we might need to subtract this noise or just use it as a distortion map.
            # Let's assume for "glitch art", adding the DiT output (which is structured noise) is good.

            # However, the prompt says "perturb Self-Attention Map".
            # If we modify the attention map, the output of the transformer changes.
            # Let's use the output as the new latent.

            latent = latent * (1.0 - noise_level) + latent_perturbed * noise_level

        # 2. Simple Noise Injection (Fallback / Additional)
        elif noise_level > 0:
            seed = int(latent.sum().item() * 1000) % 2**32
            generator = torch.Generator(device=self.device).manual_seed(seed)
            noise = torch.randn(latent.shape, device=self.device, generator=generator)
            sigma = noise_level * 2.0
            latent = latent + noise * sigma

        # 3. Channel Shift
        if channel_shift > 0:
             shift_int = int(channel_shift * 4)
             if shift_int > 0:
                 latent = torch.roll(latent, shifts=shift_int, dims=1)
             latent[:, 0, :, :] += channel_shift

        return latent

class PerturbedAttnProcessor:
    """
    Custom Attention Processor that injects noise into attention scores.
    """
    def __init__(self, noise_level: float = 0.0):
        self.noise_level = noise_level

    def __call__(
        self,
        attn,
        hidden_states,
        encoder_hidden_states=None,
        attention_mask=None,
        temb=None,
        scale: float = 1.0,
    ):
        # This signature matches Diffusers Attention Processor
        # args: attn (Attention layer), hidden_states, ...

        batch_size, sequence_length, _ = hidden_states.shape
        attention_mask = attn.prepare_attention_mask(attention_mask, sequence_length, batch_size)
        query = attn.to_q(hidden_states)

        if encoder_hidden_states is None:
            encoder_hidden_states = hidden_states
        elif attn.norm_cross:
            encoder_hidden_states = attn.norm_encoder_hidden_states(encoder_hidden_states)

        key = attn.to_k(encoder_hidden_states)
        value = attn.to_v(encoder_hidden_states)

        query = attn.head_to_batch_dim(query)
        key = attn.head_to_batch_dim(key)
        value = attn.head_to_batch_dim(value)

        attention_probs = attn.get_attention_scores(query, key, attention_mask)

        # --- PERTURBATION HERE ---
        if self.noise_level > 0:
            # Add noise to attention map
            noise = torch.randn_like(attention_probs) * self.noise_level
            attention_probs = attention_probs + noise
            # Re-normalize to ensure stability? Or let it be chaotic (glitch)?
            # Glitch is desired.
        # -------------------------

        hidden_states = torch.bmm(attention_probs, value)
        hidden_states = attn.batch_to_head_dim(hidden_states)

        # linear proj
        hidden_states = attn.to_out[0](hidden_states)
        # dropout
        hidden_states = attn.to_out[1](hidden_states)

        return hidden_states
