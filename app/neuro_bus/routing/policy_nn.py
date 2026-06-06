"""Small MLP routing policy (PyTorch)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
except ImportError:  # pragma: no cover
    torch = None  # type: ignore
    nn = None  # type: ignore


FEATURE_DIM = 16
NUM_ACTIONS = 3


class RoutingMLP(nn.Module):  # type: ignore[misc]
    def __init__(self, in_dim: int = FEATURE_DIM, hidden: int = 32, out_dim: int = NUM_ACTIONS):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


_policy: RoutingMLP | None = None
_policy_device: str = "cpu"


def _manifest_path() -> Path:
    return Path(__file__).resolve().parents[3] / "resources" / "routing_policies" / "manifest.json"


def load_active_policy() -> RoutingMLP | None:
    global _policy, _policy_device
    if torch is None or nn is None:
        return None
    manifest_file = _manifest_path()
    if not manifest_file.is_file():
        return None
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("routing manifest read failed: %s", e)
        return None
    ver = (manifest.get("active_version") or "0").strip()
    import os

    override = (os.environ.get("XCAGI_ROUTING_POLICY_VERSION") or "").strip()
    if override:
        ver = override
    weights = None
    for p in manifest.get("policies") or []:
        if str(p.get("version")) == ver:
            rel = p.get("path") or f"policy_v{ver}.pt"
            weights = Path(__file__).resolve().parents[3] / "resources" / "routing_policies" / rel
            break
    if weights is None or not weights.is_file():
        logger.debug("routing policy weights not found for version=%s", ver)
        return None
    model = RoutingMLP()
    try:
        state = torch.load(weights, map_location="cpu")
        model.load_state_dict(state)
        model.eval()
        _policy = model
        _policy_device = "cuda" if torch.cuda.is_available() else "cpu"
        _policy.to(_policy_device)
        logger.info("loaded routing policy v%s from %s", ver, weights)
        return _policy
    except Exception as e:
        logger.warning("failed to load routing policy: %s", e)
        return None


def get_policy() -> RoutingMLP | None:
    global _policy
    if _policy is None:
        _policy = load_active_policy()
    return _policy


def predict_action_index(features: list[float], mask: list[bool] | None = None) -> int:
    pol = get_policy()
    if pol is None or torch is None:
        return -1
    x = torch.tensor([features], dtype=torch.float32, device=_policy_device)
    with torch.no_grad():
        logits = pol(x)[0]
        if mask is not None and len(mask) == NUM_ACTIONS:
            for i, m in enumerate(mask):
                if not m:
                    logits = logits.clone()
                    logits[i] = float("-inf")
        return int(torch.argmax(logits).item())


def save_policy_state_dict(path: Path, model: RoutingMLP) -> None:
    if torch is None:
        raise RuntimeError("torch not installed")
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), path)
