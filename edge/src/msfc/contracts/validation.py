"""Payload validation against the JSON Schemas in ``contracts/schemas/`` (FR-COM-06).

A message that fails validation must be dropped, logged, and never crash the receiver
(MQTT_CONTRACT.md section 7, fault code E101 PAYLOAD_INVALID). This module is where that
rule is enforced; every other module that receives a message goes through
:class:`PayloadValidator` rather than trusting the payload.
"""

from __future__ import annotations

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from msfc.contracts.registry import ContractRegistry
from msfc.core.errors import ContractError, PayloadInvalidError


def _first_error_message(errors: list[ValidationError]) -> str:
    ordered = sorted(errors, key=lambda e: list(e.path))
    first = ordered[0]
    path = "/".join(str(p) for p in first.path) or "<root>"
    return f"{path}: {first.message}"


class PayloadValidator:
    """Validates envelopes (shape) and their ``data`` (topic-specific schema).

    One instance should be reused for the lifetime of a service: schemas are parsed once
    and cached, and :class:`jsonschema.Draft202012Validator` instances are reused per schema.
    """

    def __init__(self, registry: ContractRegistry) -> None:
        self._registry = registry
        self._envelope_validator = Draft202012Validator(registry.envelope_schema())
        self._data_validators: dict[str, Draft202012Validator] = {}

    def _data_validator(self, schema_name: str) -> Draft202012Validator:
        validator = self._data_validators.get(schema_name)
        if validator is None:
            validator = Draft202012Validator(self._registry.load_schema(schema_name))
            self._data_validators[schema_name] = validator
        return validator

    def validate_shape(self, envelope: dict, *, topic: str | None = None) -> None:
        """Validate only the envelope wrapper (schema/device_id/seq/mono_ms/data)."""
        if not isinstance(envelope, dict):
            raise PayloadInvalidError(f"envelope must be a JSON object, got {type(envelope).__name__}", topic=topic)
        errors = list(self._envelope_validator.iter_errors(envelope))
        if errors:
            raise PayloadInvalidError(f"envelope shape invalid: {_first_error_message(errors)}", topic=topic)

    def validate_data(self, data: object, *, schema_name: str, topic: str | None = None) -> None:
        """Validate ``data`` against the schema named *schema_name* (e.g. ``'fault.v1'``)."""
        try:
            validator = self._data_validator(schema_name)
        except ContractError as exc:
            raise PayloadInvalidError(f"schema {schema_name!r} unavailable: {exc}", topic=topic) from exc
        errors = list(validator.iter_errors(data))
        if errors:
            raise PayloadInvalidError(
                f"data invalid against {schema_name!r}: {_first_error_message(errors)}", topic=topic
            )

    def validate_for_topic(self, topic_key: str, envelope: dict) -> None:
        """Validate an envelope that is being published or received on *topic_key*.

        Checks, in order: envelope shape, that ``envelope['schema']`` matches what the
        registry says this topic carries, then the data against that schema. Raising early
        on a mismatched ``schema`` field catches a common mistake (encoding the wrong
        payload type for a topic) before jsonschema even looks at the data.
        """
        spec = self._registry.topic(topic_key)  # raises ContractError -> caller's problem, not E101
        self.validate_shape(envelope, topic=topic_key)
        declared = envelope.get("schema")
        if declared != spec.schema:
            raise PayloadInvalidError(
                f"envelope declares schema {declared!r}, topic {topic_key!r} expects {spec.schema!r}",
                topic=topic_key,
            )
        self.validate_data(envelope["data"], schema_name=spec.schema, topic=topic_key)

    def validate_unknown_topic(self, topic: str, envelope: dict) -> None:
        """Validate a message from a topic not looked up via a known key (e.g. a wildcard
        subscriber routing by matched topic string rather than by registry key).

        Only checks envelope shape and that the declared schema is loadable; the caller is
        responsible for deciding whether the *content* is expected on that topic.
        """
        self.validate_shape(envelope, topic=topic)
        declared = envelope.get("schema")
        if not isinstance(declared, str):
            raise PayloadInvalidError("envelope missing a string 'schema' field", topic=topic)
        self.validate_data(envelope["data"], schema_name=declared, topic=topic)
