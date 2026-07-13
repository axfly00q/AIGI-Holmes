"""Small TextCNN used for optional news text classification comparison."""

from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F


class TextCNN(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        num_classes: int,
        embed_dim: int = 64,
        num_filters: int = 64,
        kernel_sizes: tuple[int, ...] = (2, 3, 4),
        dropout: float = 0.25,
    ) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.convs = nn.ModuleList(
            nn.Conv1d(embed_dim, num_filters, kernel_size=k) for k in kernel_sizes
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(num_filters * len(kernel_sizes), num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        emb = self.embedding(x).transpose(1, 2)
        pooled = []
        for conv in self.convs:
            feat = F.relu(conv(emb))
            pooled.append(F.max_pool1d(feat, feat.size(2)).squeeze(2))
        return self.fc(self.dropout(torch.cat(pooled, dim=1)))


def encode_chars(text: str, vocab: dict[str, int], max_len: int) -> list[int]:
    ids = [vocab.get(ch, 1) for ch in text[:max_len]]
    if len(ids) < max_len:
        ids.extend([0] * (max_len - len(ids)))
    return ids

