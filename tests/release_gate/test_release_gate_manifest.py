"""Release gate manifest test."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.release_gate


def test_release_gate_marker_is_registered(pytestconfig) -> None:
    markers = pytestconfig.getini("markers") or []
    joined = "\n".join(markers) if isinstance(markers, list) else str(markers)
    assert "release_gate" in joined
