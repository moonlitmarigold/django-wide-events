from wide_events.context import ContextEvent


def test_uninitialized_get_returns_empty_mapping():
    assert ContextEvent.get() == {}


def test_init_then_set_reflects_updates():
    ctx = ContextEvent.init()
    try:
        ContextEvent.set(request_id="abc")
        assert ContextEvent.get() == {"request_id": "abc"}
    finally:
        ctx.drop()


def test_nested_events_drop_restores_outer():
    outer = ContextEvent.init()
    try:
        ContextEvent.set(level="outer")
        inner = ContextEvent.init()
        try:
            ContextEvent.set(level="inner")
            assert ContextEvent.get() == {"level": "inner"}
        finally:
            inner.drop()
        assert ContextEvent.get() == {"level": "outer"}
    finally:
        outer.drop()