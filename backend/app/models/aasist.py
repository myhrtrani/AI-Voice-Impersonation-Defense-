"""
Standalone WavLM Neural Audio Spoof Detector Module.
Integrates Pretrained Microsoft WavLM-Base backbone with Attentive Statistics Pooling.
"""

import os
from typing import Dict, Any, Tuple, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from transformers import WavLMModel


class WavLMSoloModel(nn.Module):
    """
    Standalone WavLM-Base Neural Audio Spoof Detector.
    Uses frozen WavLM speech representations with Attentive Statistics Pooling (ASP)
    and a two-class classification head (bonafide vs. spoof).
    """

    def __init__(self, wavlm_name: str = "microsoft/wavlm-base"):
        super().__init__()
        self.wavlm = WavLMModel.from_pretrained(wavlm_name)
        for param in self.wavlm.parameters():
            param.requires_grad = False
        self.wavlm.eval()

        hidden_size = self.wavlm.config.hidden_size  # 768

        # Attentive Statistics Pooling (ASP) projection
        self.asp_att = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.Tanh(),
            nn.Linear(128, 1)
        )

        # Classification head: Linear -> SELU -> Dropout -> Linear (2 logits: bonafide vs. spoof)
        self.classifier = nn.Sequential(
            nn.LayerNorm(hidden_size * 2),
            nn.Linear(hidden_size * 2, 128),
            nn.SELU(inplace=True),
            nn.Dropout(0.1),
            nn.Linear(128, 2)
        )
        with torch.no_grad():
            self.classifier[-1].bias[0] = 0.8
            self.classifier[-1].bias[1] = -0.8

    @staticmethod
    def _standardize_audio(x: Tensor, target_length: int = 64600) -> Tensor:
        if x.ndim == 1:
            x = x.unsqueeze(0)
        elif x.ndim == 3 and x.size(1) == 1:
            x = x.squeeze(1)
        if x.ndim != 2:
            raise ValueError("Audio input must have shape (batch, samples)")

        sample_count = x.size(1)
        if sample_count == 0:
            raise ValueError("Audio input cannot be empty")
        if sample_count >= target_length:
            return x[:, :target_length]

        repeats = (target_length + sample_count - 1) // sample_count
        return x.repeat(1, repeats)[:, :target_length]

    def forward(self, x: Tensor, Freq_aug: bool = False) -> Tuple[Tensor, Tensor]:
        """
        Forward pass through frozen WavLM backbone, ASP pooling, and classifier head.

        Returns:
            Tuple of (pooled_embeddings [batch, 1536], logits [batch, 2])
            Logit index 0 = BONAFIDE (authentic human)
            Logit index 1 = SPOOF (synthetic / clone)
        """
        x = self._standardize_audio(x)
        with torch.no_grad():
            wavlm_output = self.wavlm(input_values=x)
            frame_embeddings = wavlm_output.last_hidden_state  # (B, T, D)

            # Attentive Statistics Pooling
            att_weights = F.softmax(self.asp_att(frame_embeddings), dim=1)  # (B, T, 1)
            mean_embeddings = torch.sum(frame_embeddings * att_weights, dim=1)  # (B, D)

            residuals = frame_embeddings - mean_embeddings.unsqueeze(1)
            std_embeddings = torch.sqrt(torch.sum(att_weights * (residuals ** 2), dim=1).clamp(min=1e-6))  # (B, D)

            pooled = torch.cat([mean_embeddings, std_embeddings], dim=-1)  # (B, 2*D)

        logits = self.classifier(pooled)
        return pooled, logits


def pad_to_aasist_length(x: np.ndarray, max_len: int = 64600) -> np.ndarray:
    """
    Standard variable-length input padding/truncation protocol.
    Repeats short chunks cyclically up to 64,600 samples; truncates longer audio.
    """
    x_len = x.shape[0]
    if x_len >= max_len:
        return x[:max_len]
    num_repeats = int(max_len / x_len) + 1
    padded_x = np.tile(x, num_repeats)[:max_len]
    return padded_x


def load_wavlm_solo_model(weights_path: str = None) -> Tuple[WavLMSoloModel, int, int]:
    """
    Instantiates the standalone WavLMSoloModel in eval mode.
    Returns (model, param_count, file_size).
    """
    model = WavLMSoloModel()
    file_size = 0
    if weights_path and os.path.exists(weights_path):
        state_dict = torch.load(weights_path, map_location="cpu", weights_only=True)
        cleaned_state = {k.replace("module.", ""): v for k, v in state_dict.items()}
        model.load_state_dict(cleaned_state, strict=False)
        file_size = os.path.getsize(weights_path)

    model.eval()
    param_count = sum(p.numel() for p in model.parameters())
    return model, param_count, file_size

