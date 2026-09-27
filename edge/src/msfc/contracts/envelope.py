"""Envelope assembly (FR-COM-03) — the common wrapper every MQTT payload uses.

Building an envelope here only assembles the dict; it does not validate it against a JSON
Schema (that is :class:`msfc.contracts.validation.PayloadValidator`'s job, so there is one
source of truth for the shape: ``contracts/schemas/envelope.v1.json``). This module does
raise on the handful of things a caller can get wrong before the schema even sees the data
(negative counters, wrong types) so mistakes are caught close to where they happen.
"""

from __future__ import annotations

from msfc.core.errors import ContractError

SCHEMA_NAME = "envelope.v1"


def build_envelope(
    *,
    schema: str,
    device_id: str,
    seq: int,
    mono_ms: int,
    data: dict,
    boot_id: int | None = None,
    ts: str | None = None,
) -> dict:
    """Assemble one envelope dict, ready to JSON-encode and publish.

    Args:
        schema: name of the schema *data* conforms to, e.g. ``"product_detected.v1"``.
        device_id: sender's device id (``[a-z0-9-]{3,32}``, enforced by the schema).
        seq: this device's per-boot, strictly increasing message counter.
        mono_ms: sender's monotonic clock reading, in milliseconds, at send time.
        data: the payload; must independently validate against *schema*.
        boot_id: increments every device boot; required for embedded devices, omitted by
            services that have no concept of "boot" (e.g. the Edge Server itself may still
            set it to a process-start counter — callers decide).
        ts: ISO-8601 UTC timestamp, only when the sender has a synced wall clock.

    Raises:
        ContractError: a structurally invalid value (negative seq/mono_ms, wrong types).
            This is a cheap pre-check; the authoritative check is schema validation.
    """
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
        raise ContractError(f"seq must be a non-negative integer, got {seq!r}")
    if not isinstance(mono_ms, int) or isinstance(mono_ms, bool) or mono_ms < 0:
        raise ContractError(f"mono_ms must be a non-negative integer, got {mono_ms!r}")
    if not isinstance(data, dict):
        raise ContractError(f"data must be a dict, got {type(data).__name__}")

    envelope: dict = {
        "schema": schema,
        "device_id": device_id,
        "seq": seq,
        "mono_ms": mono_ms,
        "data": data,
    }
    if boot_id is not None:
        if not isinstance(boot_id, int) or isinstance(boot_id, bool) or boot_id < 0:
            raise ContractError(f"boot_id must be a non-negative integer, got {boot_id!r}")
        envelope["boot_id"] = boot_id
    if ts is not None:
        envelope["ts"] = ts
    return envelope


class SeqCounter:
    """Per-device monotonically increasing counter for the envelope's ``seq`` field.

    Not thread-safe by design: each simulated/real device owns exactly one counter and
    calls it from its own control loop, matching how a single-core embedded device works.
    """

    def __init__(self, start: int = 0) -> None:
        if start < 0:
            raise ContractError(f"start must be >= 0, got {start!r}")
        self._next = start

    def next(self) -> int:
        value = self._next
        self._next += 1
        return value

    def peek(self) -> int:
        return self._next
