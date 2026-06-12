import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional

from .Cross_Modal_Align import CrossModal

from .difusion_block import DifBlock
from .inherent_block import InhBlock
from .dynamic_graph_conv.dy_graph_conv import DynamicGraphConstructor
from .decouple.estimation_gate import EstimationGate


class DecoupleLayer(nn.Module):
    def __init__(self, hidden_dim, fk_dim=256, first=False, **model_args):
        super().__init__()
        self.spatial_gate = EstimationGate(
            model_args['node_hidden'], model_args['time_emb_dim'], 64, model_args['seq_length'])
        self.dif_layer = DifBlock(hidden_dim, fk_dim=fk_dim, **model_args)
        self.inh_layer = InhBlock(
            hidden_dim, fk_dim=fk_dim, first=first, **model_args)

    def forward(self, X: torch.Tensor, dynamic_graph: torch.Tensor, static_graph, E_u, E_d, T_D, D_W):
        """decouple layer

        Args:
            X (torch.Tensor): input data with shape (B, L, N, D)
            dynamic_graph (list of torch.Tensor): dynamic graph adjacency matrix with shape (B, N, k_t * N)
            static_graph (list of torch.Tensor): the self-adaptive transition matrix with shape (N, N)
            E_u (torch.Parameter): node embedding E_u
            E_d (torch.Parameter): node embedding E_d
            T_D (torch.Parameter): time embedding T_D
            D_W (torch.Parameter): time embedding D_W

        Returns:
            torch.Tensor: undecoupled signal X^{l+1}, shape [B, L', N, D].
            torch.Tensor: forecast branch of Diffusion Block, shape (B, L'', N, D).
            torch.Tensor: forecast branch of Inherent Block, shape (B, L'', N, D).
        """
        X_spa = self.spatial_gate(E_u, E_d, T_D, D_W, X)
        dif_backcast_seq_res, dif_forecast_hidden = self.dif_layer(
            X=X, X_spa=X_spa, dynamic_graph=dynamic_graph, static_graph=static_graph)
        inh_backcast_seq_res, inh_forecast_hidden = self.inh_layer(
            dif_backcast_seq_res)
        return inh_backcast_seq_res, dif_forecast_hidden, inh_forecast_hidden


class D2STGNN(nn.Module):
    """Full D2STGNN model with FUSE-Traffic cross-modal fusion.

    Implements the Spatial-Temporal Graph Encoder + Fusion & Alignment
    modules from the FUSE-Traffic paper (SIGSPATIAL 2025), without LLM/Gemini.

    The cross-attention fusion accepts either:
      - Learnable event_embeddings (nn.Parameter, default) — used when no
        external event embeddings are provided (e.g. during smoke tests).
      - External event_embeddings tensor [B, E, C] passed via forward() kwargs
        — used when the unstructured NLP pipeline provides encoded events from
        GDELT, news, or X (Twitter) sources.

    History tensor is expected to have shape [B, T, N, num_feat + 2] where
    the last two columns are time-of-day and day-of-week fractions in [0, 1).
    """

    def __init__(self, **model_args):
        super().__init__()
        # attributes
        self._in_feat = model_args['num_feat']
        self._hidden_dim = model_args['num_hidden']
        self._node_dim = model_args['node_hidden']
        self._forecast_dim = 256
        self._output_hidden = 512
        self._output_dim = model_args['seq_length']

        self._num_nodes = model_args['num_nodes']
        self._k_s = model_args['k_s']
        self._k_t = model_args['k_t']
        self._num_layers = 5
        self._time_in_day_size = model_args['time_in_day_size']
        self._day_in_week_size = model_args['day_in_week_size']

        model_args['use_pre'] = False
        model_args['dy_graph'] = True
        model_args['sta_graph'] = True

        self._model_args = model_args

        # Input embedding: traffic features → hidden_dim
        self.embedding = nn.Linear(self._in_feat, self._hidden_dim)

        # Time embedding lookup tables
        self.T_i_D_emb = nn.Parameter(
            torch.empty(288, model_args['time_emb_dim']))
        self.D_i_W_emb = nn.Parameter(
            torch.empty(7, model_args['time_emb_dim']))

        # Decoupled Spatial-Temporal Layers (5 layers as per D2STGNN paper)
        self.layers = nn.ModuleList([DecoupleLayer(
            self._hidden_dim, fk_dim=self._forecast_dim, first=True, **model_args)])
        for _ in range(self._num_layers - 1):
            self.layers.append(DecoupleLayer(
                self._hidden_dim, fk_dim=self._forecast_dim, **model_args))

        # Dynamic graph constructor
        if model_args['dy_graph']:
            self.dynamic_graph_constructor = DynamicGraphConstructor(**model_args)

        # Node embeddings for static graph construction
        self.node_emb_u = nn.Parameter(
            torch.empty(self._num_nodes, self._node_dim))
        self.node_emb_d = nn.Parameter(
            torch.empty(self._num_nodes, self._node_dim))

        # C dimension: actual last-dim of forecast_hidden after .view()
        # forecast_hidden shape after layers: [B, gap, N, fk_dim]
        # After transpose+view: [B, N, gap * fk_dim] = [B, N, 1 * 256] per seq
        # Empirically verified: gap=1, seq_length=2 → C = fk_dim * 2 = 512
        self._c_dim = self._forecast_dim * model_args['gap'] * model_args['seq_length']
        # E dimension: number of event embedding slots (K/V sequence length)
        self._e_dim = 384

        # Output decoder: [B, N, C] → [B, N, gap*4] → [B, gap*4, N, 1]
        self.out_fc_1 = nn.Linear(self._c_dim, self._output_hidden)
        self.out_fc_2 = nn.Linear(self._output_hidden, model_args['gap'] * 4)

        # Cross-Modal Attention (FUSE-Traffic Fusion & Alignment module)
        # Q: forecast_hidden [B, N, C]
        # K, V: event_embeddings [B, E, C]
        # Output: cross_out [B, N, C]
        self.cross = CrossModal(
            d_model=self._c_dim,
            n_heads=1,
            d_ff=32,
            norm='LayerNorm',
            attn_dropout=model_args['dropout'],
            dropout=model_args['dropout'],
            pre_norm=True,
            activation="gelu",
            res_attention=True,
            n_layers=1,
            store_attn=True,
        )

        # Learnable fallback event embeddings [1, E, C] — used when no
        # external NLP embeddings are injected via forward()
        self.event_embeddings = nn.Parameter(
            torch.empty(1, self._e_dim, self._c_dim))

        self.reset_parameter()

    def reset_parameter(self):
        nn.init.xavier_uniform_(self.node_emb_u)
        nn.init.xavier_uniform_(self.node_emb_d)
        nn.init.xavier_uniform_(self.T_i_D_emb)
        nn.init.xavier_uniform_(self.D_i_W_emb)
        nn.init.xavier_uniform_(self.event_embeddings)

    def _graph_constructor(self, **inputs):
        E_d = inputs['E_d']
        E_u = inputs['E_u']
        if self._model_args['sta_graph']:
            static_graph = [F.softmax(F.relu(torch.mm(E_d, E_u.T)), dim=1)]
        else:
            static_graph = []
        if self._model_args['dy_graph']:
            dynamic_graph = self.dynamic_graph_constructor(**inputs)
        else:
            dynamic_graph = []
        return static_graph, dynamic_graph

    def _prepare_inputs(self, X: torch.Tensor):
        """Split history tensor into traffic features and time embeddings.

        Expects X shape [B, T, N, num_feat + 2] where:
          cols 0..num_feat-1 : traffic features (speed, flow, density, flag)
          col  num_feat      : time_of_day fraction in [0, 1)
          col  num_feat + 1  : day_of_week fraction in [0, ~0.857]
        """
        num_feat = self._model_args['num_feat']
        node_emb_u = self.node_emb_u
        node_emb_d = self.node_emb_d

        # Clamp time indices to valid embedding table bounds
        tod_idx = (X[:, :, :, num_feat] * self._time_in_day_size).long().clamp(0, self._time_in_day_size - 1)
        dow_idx = (X[:, :, :, num_feat + 1] * self._day_in_week_size).long().clamp(0, self._day_in_week_size - 1)

        T_i_D = self.T_i_D_emb[tod_idx]
        D_i_W = self.D_i_W_emb[dow_idx]
        X = X[:, :, :, :num_feat]
        return X, node_emb_u, node_emb_d, T_i_D, D_i_W

    def forward(
        self,
        history_data: torch.Tensor,
        future_data: torch.Tensor,
        batch_seen: int,
        epoch: int,
        train: bool,
        event_embeddings: Optional[torch.Tensor] = None,
        **kwargs,
    ) -> torch.Tensor:
        """Forward pass with optional NLP event embeddings injection.

        Args:
            history_data:     [B, T, N, num_feat+2] — structured traffic tensor
            future_data:      [B, T', N, num_feat+2] — future window (for teacher forcing)
            batch_seen:       training step counter
            epoch:            training epoch counter
            train:            training mode flag
            event_embeddings: Optional [B, E, C] tensor from the unstructured NLP
                              pipeline (GDELT/news/X events encoded by fusion.py).
                              If None, falls back to learnable self.event_embeddings.

        Returns:
            forecast: [B, gap*4, N, 1]
        """
        X = history_data
        X, E_u, E_d, T_D, D_W = self._prepare_inputs(X)
        static_graph, dynamic_graph = self._graph_constructor(
            E_u=E_u, E_d=E_d, X=X, T_D=T_D, D_W=D_W)

        # Input projection: [B, T, N, num_feat] → [B, T, N, hidden_dim]
        X = self.embedding(X)

        # Run through 5 decoupled spatial-temporal layers
        spa_forecast_hidden_list = []
        tem_forecast_hidden_list = []
        tem_backcast_seq_res = X
        for layer in self.layers:
            tem_backcast_seq_res, spa_forecast_hidden, tem_forecast_hidden = layer(
                tem_backcast_seq_res, dynamic_graph, static_graph, E_u, E_d, T_D, D_W)
            spa_forecast_hidden_list.append(spa_forecast_hidden)
            tem_forecast_hidden_list.append(tem_forecast_hidden)

        # Aggregate forecast hidden states across layers
        spa_forecast_hidden = sum(spa_forecast_hidden_list)
        tem_forecast_hidden = sum(tem_forecast_hidden_list)
        forecast_hidden = spa_forecast_hidden + tem_forecast_hidden
        # forecast_hidden shape: [B, gap, N, fk_dim]

        # Reshape to [B, N, C] for cross-attention query
        B, gap, N, fk = forecast_hidden.shape
        forecast_hidden = forecast_hidden.transpose(1, 2).contiguous().view(B, N, gap * fk)
        # → [B, N, C]  where C = gap * fk_dim = _c_dim

        # Resolve event embeddings (K, V for cross-attention)
        # Priority: externally injected NLP embeddings > learnable fallback
        if event_embeddings is not None:
            # External: [B, E, C] from unstructured NLP pipeline
            emb = event_embeddings.to(forecast_hidden.device)
            # Project to C dim if shapes differ (graceful mismatch handling)
            if emb.shape[-1] != self._c_dim:
                # Linear interpolation along last dim to match C
                emb = F.interpolate(
                    emb.unsqueeze(1),
                    size=(emb.shape[1], self._c_dim),
                    mode='bilinear',
                    align_corners=False,
                ).squeeze(1)
        else:
            # Learnable fallback: expand [1, E, C] → [B, E, C]
            emb = self.event_embeddings.expand(B, -1, -1)

        # FUSE-Traffic Cross-Modal Fusion & Alignment (Section 2.4)
        # Q: forecast_hidden [B, N, C]
        # K, V: emb [B, E, C]
        # Output: cross_out [B, N, C]
        cross_out = self.cross(forecast_hidden, emb, emb)

        # Store attention maps for interpretability (detached, no grad)
        self.cross_attn_maps = []
        for layer in self.cross.layers:
            if hasattr(layer, 'attn') and layer.attn is not None:
                self.cross_attn_maps.append(layer.attn.detach().cpu())

        # Decode: [B, N, C] → [B, N, gap*4] → [B, gap*4, N, 1]
        forecast = self.out_fc_2(F.relu(self.out_fc_1(F.relu(cross_out))))
        forecast = forecast.transpose(1, 2).unsqueeze(-1)

        return forecast

