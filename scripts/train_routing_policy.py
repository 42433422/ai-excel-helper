#!/usr/bin/env python3
"""
Offline training for routing MLP from JSONL logs (features + action index + reward).

Usage:
  python scripts/train_routing_policy.py --init-only
  python scripts/train_routing_policy.py --data resources/routing_policies/routing_decisions.jsonl --epochs 20
"""

from __future__ import annotations

import argparse
import sys
import hashlib
import json
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.neuro_bus.routing.policy_nn import (
    FEATURE_DIM,
    NUM_ACTIONS,
    RoutingMLP,
    save_policy_state_dict,
)


def _action_to_idx(action: str) -> int:
    m = {"reflex": 0, "subconscious": 1, "conscious": 2}
    return m.get(str(action).lower(), -1)


def load_rows(path: Path) -> list[dict]:
    rows = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def train(data: Path, out: Path, epochs: int, lr: float) -> None:
    rows = load_rows(data)
    xs: list[list[float]] = []
    ys: list[int] = []
    for r in rows:
        feats = r.get("features")
        if not feats or len(feats) != FEATURE_DIM:
            continue
        aid = r.get("action_idx")
        if aid is None:
            aid = _action_to_idx(r.get("action", ""))
        if aid is None or int(aid) < 0:
            continue
        reward = float(r.get("reward", 1.0) or 1.0)
        if reward <= 0:
            continue
        xs.append([float(x) for x in feats])
        ys.append(int(aid))

    if len(xs) < 4:
        print(f"[train_routing_policy] not enough rows ({len(xs)}), writing init model only")
        model = RoutingMLP()
        save_policy_state_dict(out, model)
        return

    x_t = torch.tensor(xs, dtype=torch.float32)
    y_t = torch.tensor(ys, dtype=torch.long)
    model = RoutingMLP()
    opt = optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()
    model.train()
    for ep in range(epochs):
        opt.zero_grad()
        logits = model(x_t)
        loss = loss_fn(logits, y_t)
        loss.backward()
        opt.step()
        if ep % 5 == 0:
            print(f"epoch {ep} loss={loss.item():.4f}")

    model.eval()
    save_policy_state_dict(out, model)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"[train_routing_policy] saved {out} sha256={digest[:16]}...")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init-only", action="store_true", help="Write random init policy_v0.pt")
    ap.add_argument(
        "--data", type=Path, default=Path("resources/routing_policies/routing_decisions.jsonl")
    )
    ap.add_argument("--out", type=Path, default=Path("resources/routing_policies/policy_v1.pt"))
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=1e-2)
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    data = root / args.data if not args.data.is_absolute() else args.data
    out = root / args.out if not args.out.is_absolute() else args.out

    if args.init_only:
        out0 = root / "resources/routing_policies/policy_v0.pt"
        model = RoutingMLP()
        save_policy_state_dict(out0, model)
        print(f"[train_routing_policy] init weights -> {out0}")
        return

    train(data, out, epochs=args.epochs, lr=args.lr)
    manifest = root / "resources/routing_policies/manifest.json"
    if manifest.is_file():
        m = json.loads(manifest.read_text(encoding="utf-8"))
        ver = str(int(time.time()) % 100000)
        rel = out.name
        digest = hashlib.sha256(out.read_bytes()).hexdigest()
        m.setdefault("policies", []).append(
            {
                "version": ver,
                "path": rel,
                "sha256": digest,
                "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        m["active_version"] = ver
        manifest.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[train_routing_policy] manifest active_version={ver}")


if __name__ == "__main__":
    main()
