"""NeuroEventPublisherMixin 发布逻辑。"""

from unittest.mock import MagicMock, patch

from app.neuro_bus.event_publisher_mixin import NeuroEventPublisherMixin


class _Dummy(NeuroEventPublisherMixin):
    pass


def test_publish_event_returns_event_id_when_bus_ok():
    mock_bus = MagicMock()
    mock_event = MagicMock()
    mock_event.metadata.event_id = "evt-123"

    with (
        patch("app.neuro_bus.event_publisher_mixin.get_neuro_bus", return_value=mock_bus),
        patch("app.neuro_bus.event_publisher_mixin.NeuroEvent", return_value=mock_event),
    ):
        eid = _Dummy()._publish_event("test.event", {"k": 1})
    assert eid == "evt-123"
    mock_bus.publish.assert_called_once_with(mock_event)


def test_publish_event_returns_empty_string_on_failure():
    with patch(
        "app.neuro_bus.event_publisher_mixin.get_neuro_bus", side_effect=RuntimeError("no bus")
    ):
        eid = _Dummy()._publish_event("test.event", {})
    assert eid == ""
