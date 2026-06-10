from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional

# Graph Convolution with Adaptive Adjacency
class GraphConvolution(nn.Module):
    def __init__(
        self,
        in_features: int,
        out_features: int,
        num_nodes: int,
        embed_dim: int = 10,
        order: int = 2,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.order = order
        self.out_features = out_features

        # Learnable node embeddings for adaptive adjacency
        self.node_emb1 = nn.Embedding(num_nodes, embed_dim)
        self.node_emb2 = nn.Embedding(num_nodes, embed_dim)

        # Linear projection: (order + 1) supports (I, A, A^2)
        self.linear = nn.Linear(in_features * (order + 1), out_features)
        self.dropout = nn.Dropout(dropout)
        self.bn = nn.BatchNorm1d(out_features)

    def forward(
        self,
        x: torch.Tensor,                          
        adj_fixed: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        B, N, _ = x.shape
        device = x.device

        node_ids = torch.arange(N, device=device)
        e1 = self.node_emb1(node_ids)              
        e2 = self.node_emb2(node_ids)             
        adj_adaptive = F.softmax(F.relu(e1 @ e2.T), dim=-1)

        if adj_fixed is not None:
            adj = (adj_adaptive + adj_fixed.to(device)) / 2.0
        else:
            adj = adj_adaptive

        # Graph diffusion: collect [x, Ax, A^2x, ...]
        supports = [x]
        h = x
        for _ in range(self.order):
            h = torch.bmm(adj.unsqueeze(0).expand(B, -1, -1), h) 
            supports.append(h)

        out = torch.cat(supports, dim=-1)         
        out = self.linear(out)                  
        out = self.bn(out.reshape(-1, self.out_features)).reshape(B, N, self.out_features)
        return self.dropout(F.relu(out))

# Gated Temporal Convolution Block
class GatedTCN(nn.Module):
    def __init__(self, channels: int, kernel_size: int = 3, dilation: int = 1):
        super().__init__()
        pad = (kernel_size - 1) * dilation
        self.conv_tanh = nn.Conv1d(channels, channels, kernel_size, padding=pad, dilation=dilation)
        self.conv_sig = nn.Conv1d(channels, channels, kernel_size, padding=pad, dilation=dilation)
        self.causal_pad = pad

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B*N, C, T]
        gate = torch.tanh(self.conv_tanh(x)[..., : x.shape[-1]])
        sig = torch.sigmoid(self.conv_sig(x)[..., : x.shape[-1]])
        return gate * sig

# Graph WaveNet Block
class GWNBlock(nn.Module):
    def __init__(
        self,
        channels: int,
        num_nodes: int,
        kernel_size: int = 2,
        dilation: int = 1,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.tcn = GatedTCN(channels, kernel_size, dilation)
        self.gcn = GraphConvolution(channels, channels, num_nodes, dropout=dropout)
        self.residual = nn.Conv1d(channels, channels, 1) 

    def forward(
        self,
        x: torch.Tensor,                         
        adj: Optional[torch.Tensor] = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        B, N, C, T = x.shape

        # Temporal convolution
        h = x.reshape(B * N, C, T)
        h = self.tcn(h)                           
        h = h.reshape(B, N, C, T)

        # Spatial convolution at each timestep
        spatial_out = []
        for t in range(T):
            spatial_out.append(self.gcn(h[:, :, :, t], adj))  
        h = torch.stack(spatial_out, dim=-1)    

        # Skip + residual
        skip = self.residual(x.reshape(B * N, C, T)).reshape(B, N, C, T)
        return h + skip, h

# Full Graph WaveNet Model
class GraphWaveNet(nn.Module):
    def __init__(
        self,
        num_nodes: int,
        in_features: int = 3,         
        hidden_channels: int = 32,
        n_blocks: int = 8,
        kernel_size: int = 2,
        dropout: float = 0.3,
        seq_in: int = 12,              
        seq_out: int = 3,           
    ):
        super().__init__()
        self.num_nodes = num_nodes
        self.seq_out = seq_out

        # Input projection
        self.input_proj = nn.Conv2d(in_features, hidden_channels, kernel_size=1)

        # Stacked GWN blocks with exponential dilation
        self.blocks = nn.ModuleList()
        for i in range(n_blocks):
            dilation = 2 ** (i % 4)
            self.blocks.append(
                GWNBlock(hidden_channels, num_nodes, kernel_size, dilation, dropout)
            )

        # Output MLP: aggregated skip connections - forecast
        self.output = nn.Sequential(
            nn.ReLU(),
            nn.Conv2d(hidden_channels, hidden_channels, kernel_size=1),
            nn.ReLU(),
            nn.Conv2d(hidden_channels, seq_out, kernel_size=1),
        )

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Conv1d, nn.Conv2d, nn.Linear)):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(
        self,
        x: torch.Tensor,                         
        adj: Optional[torch.Tensor] = None,       
    ) -> torch.Tensor:                         
        B, N, T, F = x.shape

        # [B, F, N, T] for Conv2d
        h = x.permute(0, 3, 1, 2)
        h = self.input_proj(h)                   
        h = h.permute(0, 2, 1, 3)              

        skip_sum = torch.zeros(B, N, h.shape[2], T, device=x.device)
        for block in self.blocks:
            h, skip = block(h, adj)
            skip_sum = skip_sum + skip

        # [B, C, N, T] - output projection
        out = skip_sum.permute(0, 2, 1, 3)        
        out = self.output(out)                  

        # Take last timestep
        out = out[:, :, :, -1]                  
        return out.permute(0, 2, 1)

# Model Builder
def build_gwn_model(
    num_nodes: int,
    device: str = "cpu",
    checkpoint_path: Optional[str] = None,
    **kwargs,
) -> GraphWaveNet:
    model = GraphWaveNet(num_nodes=num_nodes, **kwargs).to(device)
    if checkpoint_path:
        state = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(state["model_state_dict"])
        model.eval()
    return model