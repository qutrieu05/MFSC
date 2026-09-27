"""Tests for msfc.comm.bus.InMemoryBus."""

from __future__ import annotations

from msfc.comm import InMemoryBus


def test_publish_delivers_to_matching_subscriber() -> None:
    bus = InMemoryBus()
    received = []
    bus.subscribe("factory/line01/conveyor/+/status", lambda t, e: received.append((t, e)))

    bus.publish("factory/line01/conveyor/esp32-cc01/status", {"data": {"online": True}})

    assert received == [("factory/line01/conveyor/esp32-cc01/status", {"data": {"online": True}})]


def test_publish_does_not_deliver_to_non_matching_subscriber() -> None:
    bus = InMemoryBus()
    received = []
    bus.subscribe("factory/line01/conveyor/+/state", lambda t, e: received.append((t, e)))

    bus.publish("factory/line01/conveyor/esp32-cc01/status", {"data": {}})

    assert received == []


def test_multiple_subscribers_all_receive_the_message() -> None:
    bus = InMemoryBus()
    a, b = [], []
    bus.subscribe("factory/line01/conveyor/+/status", lambda t, e: a.append(e))
    bus.subscribe("factory/+/+/+/status", lambda t, e: b.append(e))

    bus.publish("factory/line01/conveyor/esp32-cc01/status", {"n": 1})

    assert a == [{"n": 1}] and b == [{"n": 1}]


def test_retained_message_delivered_to_a_subscriber_that_joins_later() -> None:
    bus = InMemoryBus()
    bus.publish("factory/line01/conveyor/esp32-cc01/status", {"online": True}, retain=True)

    received = []
    bus.subscribe("factory/line01/conveyor/+/status", lambda t, e: received.append(e))

    assert received == [{"online": True}]


def test_non_retained_message_is_not_replayed_to_a_later_subscriber() -> None:
    bus = InMemoryBus()
    bus.publish("factory/line01/conveyor/esp32-cc01/status", {"online": True}, retain=False)

    received = []
    bus.subscribe("factory/line01/conveyor/+/status", lambda t, e: received.append(e))

    assert received == []


def test_published_records_every_message_with_qos_and_retain() -> None:
    bus = InMemoryBus()
    bus.publish("t1", {"a": 1}, qos=1, retain=True)
    bus.publish("t2", {"a": 2})

    assert [m.topic for m in bus.published] == ["t1", "t2"]
    assert bus.published[0].qos == 1 and bus.published[0].retain is True
    assert bus.published[1].qos == 0 and bus.published[1].retain is False


def test_clear_published_empties_the_log_but_keeps_subscriptions_and_retained() -> None:
    bus = InMemoryBus()
    bus.publish("t1", {"a": 1}, retain=True)
    bus.clear_published()

    assert bus.published == ()
    received = []
    bus.subscribe("t1", lambda t, e: received.append(e))
    assert received == [{"a": 1}]  # retained state survived clearing the publish log


def test_stop_clears_subscriptions() -> None:
    bus = InMemoryBus()
    received = []
    bus.subscribe("t1", lambda t, e: received.append(e))
    bus.stop()
    bus.publish("t1", {"a": 1})
    assert received == []


def test_handler_can_publish_reentrantly_without_infinite_recursion() -> None:
    """A handler publishing to a different topic must not corrupt the subscriber list
    being iterated for the original publish (bus.publish snapshots subscribers)."""
    bus = InMemoryBus()
    chain = []

    def on_a(topic, envelope):
        chain.append("a")
        bus.publish("b", {})

    def on_b(topic, envelope):
        chain.append("b")

    bus.subscribe("a", on_a)
    bus.subscribe("b", on_b)
    bus.publish("a", {})

    assert chain == ["a", "b"]
