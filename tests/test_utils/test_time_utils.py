"""app.utils.time — UTC 辅助函数。"""

from app.utils.time import utc_now_iso_z, utc_now_naive


def test_utc_now_naive_is_naive():
    dt = utc_now_naive()
    assert dt.tzinfo is None


def test_utc_now_iso_z_ends_with_z():
    s = utc_now_iso_z()
    assert s.endswith("Z")
    assert "+00:00" not in s
