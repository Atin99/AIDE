import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from ml.multitask_net import MultiTaskNet, MODELS_DIR, TARGETS

EXP_TARGETS = ["yield_strength", "UTS"]


class TransferNet(nn.Module if TORCH_AVAILABLE else object):
    def __init__(self, pretrained_model, freeze_encoder=True):
        super().__init__()
        self.encoder = pretrained_model.encoder
        if freeze_encoder:
            for p in self.encoder.parameters():
                p.requires_grad = False
        in_dim = 32
        self.heads = nn.ModuleDict({t: nn.Linear(in_dim, 1) for t in EXP_TARGETS})

    def forward(self, x):
        z = self.encoder(x)
        return {t: self.heads[t](z).squeeze(-1) for t in EXP_TARGETS}


def fine_tune_on_mpea(pretrained_model, X_exp, y_exp_dict, epochs=100, lr=5e-4):
    if not TORCH_AVAILABLE or pretrained_model is None:
        print("  Transfer learning skipped: torch not available or no pretrained model")
        return None

    import torch
    model = TransferNet(pretrained_model, freeze_encoder=True)
    optimizer = torch.optim.Adam(
        [p for p in model.parameters() if p.requires_grad], lr=lr)
    criterion = nn.MSELoss()

    Xt = torch.tensor(X_exp, dtype=torch.float32)
    yt = {t: torch.tensor(y_exp_dict[t], dtype=torch.float32)
          for t in EXP_TARGETS if t in y_exp_dict}

    dataset = TensorDataset(Xt, *[yt[t] for t in yt])
    loader = DataLoader(dataset, batch_size=32, shuffle=True)

    model.train()
    for epoch in range(epochs):
        for batch in loader:
            xb = batch[0]
            preds = model(xb)
            
            loss = None
            for i, t in enumerate(yt.keys()):
                yb = batch[i + 1]
                m = torch.isfinite(yb)
                if m.sum() > 0:
                    l_target = criterion(preds[t][m], yb[m])
                    loss = l_target if loss is None else loss + l_target
            
            if loss is not None:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
        if (epoch + 1) % 25 == 0:
            print(f"  Transfer epoch {epoch+1}/{epochs}")

    print("  Transfer learning complete")
    return model


def save_transfer_model(model, name="transfer_yield.pt"):
    if model is None:
        return
    import torch
    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, name)
    torch.save(model.state_dict(), path)
    print(f"  Saved {path}")


def load_transfer_model(pretrained_model, name="transfer_yield.pt"):
    if not TORCH_AVAILABLE:
        return None
    import torch
    path = os.path.join(MODELS_DIR, name)
    if not os.path.exists(path) or pretrained_model is None:
        return None
    model = TransferNet(pretrained_model)
    model.load_state_dict(torch.load(path, map_location="cpu"))
    model.eval()
    return model


def predict_experimental(model, X):
    if model is None:
        return {}
    import torch
    with torch.no_grad():
        Xt = torch.tensor(X.reshape(1, -1), dtype=torch.float32)
        preds = model(Xt)
    return {t: float(v.item()) for t, v in preds.items()}
