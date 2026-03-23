import os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
TARGETS = ["formation_energy", "bulk_modulus", "shear_modulus"]


class MultiTaskNet(nn.Module if TORCH_AVAILABLE else object):
    def __init__(self, n_features, hidden=(120, 64, 32)):
        if not TORCH_AVAILABLE:
            raise ImportError("torch required: pip install torch")
        super().__init__()
        layers = []
        in_dim = n_features
        for h in hidden:
            layers += [nn.Linear(in_dim, h), nn.ReLU(), nn.Dropout(0.1)]
            in_dim = h
        self.encoder = nn.Sequential(*layers)
        self.heads = nn.ModuleDict({t: nn.Linear(in_dim, 1) for t in TARGETS})

    def forward(self, x):
        z = self.encoder(x)
        return {t: self.heads[t](z).squeeze(-1) for t in TARGETS}


def train_multitask_net(X, y_dict, epochs=80, batch_size=256, lr=1e-3):
    if not TORCH_AVAILABLE:
        print("  NN skipped: torch not installed")
        return None
    import torch
    n_features = X.shape[1]
    model = MultiTaskNet(n_features)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.MSELoss()

    Xt = torch.tensor(X, dtype=torch.float32)
    yt = {t: torch.tensor(y_dict[t], dtype=torch.float32) for t in TARGETS if t in y_dict}
    masks = {t: torch.isfinite(yt[t]) for t in yt}

    dataset = TensorDataset(Xt, *[yt[t] for t in yt])
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
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
                total_loss += loss.item()
        scheduler.step()
        if (epoch + 1) % 20 == 0:
            print(f"  NN epoch {epoch+1}/{epochs}  loss={total_loss/len(loader):.4f}")
    return model


def save_nn(model, name="multitask_nn.pt"):
    if model is None:
        return
    import torch
    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, name)
    torch.save(model.state_dict(), path)
    print(f"  Saved {path}")


def load_nn(n_features, name="multitask_nn.pt"):
    if not TORCH_AVAILABLE:
        return None
    import torch
    path = os.path.join(MODELS_DIR, name)
    if not os.path.exists(path):
        return None
    model = MultiTaskNet(n_features)
    model.load_state_dict(torch.load(path, map_location="cpu"))
    model.eval()
    return model


def predict_nn(model, X):
    if model is None:
        return {}
    import torch
    with torch.no_grad():
        Xt = torch.tensor(X.reshape(1, -1), dtype=torch.float32)
        preds = model(Xt)
    return {t: float(v.item()) for t, v in preds.items()}
