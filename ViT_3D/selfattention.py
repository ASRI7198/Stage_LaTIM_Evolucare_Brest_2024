# Copyright (c) MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import torch
import torch.nn as nn

from monai.utils import optional_import

Rearrange, _ = optional_import("einops.layers.torch", name="Rearrange")


class SABlock(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, dropout_rate: float = 0.0, qkv_bias: bool = False):
        super().__init__()

        if not (0 <= dropout_rate <= 1):
            raise ValueError("dropout_rate should be between 0 and 1.")

        if hidden_size % num_heads != 0:
            raise ValueError("hidden size should be divisible by num_heads.")

        self.num_heads = num_heads
        self.out_proj = nn.Linear(hidden_size, hidden_size)
        self.qkv = nn.Linear(hidden_size, hidden_size * 3, bias=qkv_bias)
        self.input_rearrange = Rearrange("b h (qkv l d) -> qkv b l h d", qkv=3, l=num_heads)
        self.out_rearrange = Rearrange("b h l d -> b l (h d)")
        self.drop_output = nn.Dropout(dropout_rate)
        self.drop_weights = nn.Dropout(dropout_rate)
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5

    def forward(self, x):
        output = self.input_rearrange(self.qkv(x))
        q, k, v = output[0], output[1], output[2]
        attention = (torch.einsum("blxd,blyd->blxy", q, k) * self.scale).softmax(dim=-1)
        attention = self.drop_weights(attention)
        x = torch.einsum("bhxy,bhyd->bhxd", attention, v)
        x = self.out_rearrange(x)
        x = self.out_proj(x)
        x = self.drop_output(x)
        return x, attention  # Retourner les poids d'attention
