"""Duplicate-message suppression by (device_id, boot_id, seq) — MT-05.

QoS 1 guarantees *at-least-once* delivery: a retry after a lost ack can deliver the same
message twice. :class:`DedupeFilter` wraps a handler so callers see each (device, boot,
seq) at most once, without needing every handler to reimplement this.
"""

from __future__ import annotations

from collections import OrderedDict

from msfc.comm.bus import Handler
from msfc.core.errors import ContractError
from msfc.core.logging_setup import ctx, get_logger

log = get_logger("msfc.comm.dedupe")


class DedupeFilter:
    """Callable wrapper: ``bus.subscribe(filt, DedupeFilter(my_handler))``.

    Keeps a bounded, per-``(device_id, boot_id)`` set of recently seen ``seq`` values (an
    :class:`~collections.OrderedDict` used as an LRU set) so memory does not grow without
    bound over a long-running process (NFR-REL-01).
    """

    def __init__(self, handler: Handler, *, max_per_device: int = 256) -> None:
        if max_per_device < 1:
            raise ContractError(f"max_per_device must be >= 1, got {max_per_device!r}")
        self._handler = handler
        self._max = max_per_device
        self._seen: dict[tuple[str, int], "OrderedDict[int, None]"] = {}
        self.dropped_count = 0

    def __call__(self, topic: str, envelope: dict) -> None:
        device_id = envelope.get("device_id")
        seq = envelope.get("seq")
        if not isinstance(device_id, str) or not isinstance(seq, int):
            # Malformed envelopes are the validator's concern, not ours; pass through so a
            # downstream schema check can reject them with a proper E101, rather than us
            # silently swallowing a message we cannot identify.
            self._handler(topic, envelope)
            return

        boot_id = envelope.get("boot_id", 0)
        key = (device_id, boot_id)
        history = self._seen.setdefault(key, OrderedDict())
        if seq in history:
            self.dropped_count += 1
            log.debug("dropped duplicate message", extra=ctx(topic=topic, device_id=device_id,
                                                              boot_id=boot_id, seq=seq))
            return
        history[seq] = None
        if len(history) > self._max:
            history.popitem(last=False)
        self._handler(topic, envelope)
