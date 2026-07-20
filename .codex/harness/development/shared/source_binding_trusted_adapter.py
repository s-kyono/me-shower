"""Sealed production composition boundary for source provenance authority."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Mapping

from source_binding import GenerationExecutionEvidence, SourceBindingAuthority


_FIXTURE_TOKEN = object()


class ProductionSourceProvenanceResolver(SourceBindingAuthority):
    """Production authority has no caller-supplied store or registration API.

    The future composition root will replace the empty installed index with its
    registered execution store. Until then production provenance fails closed.
    """

    __slots__ = ("__installed_index", "__generation_evidence")

    def __init__(self) -> None:
        self.__installed_index: Mapping[tuple[str, str, str], Mapping[str, Any]] = MappingProxyType({})
        self.__generation_evidence: Mapping[tuple[str, str, str], GenerationExecutionEvidence] = MappingProxyType({})

    @classmethod
    def _for_composition_test(cls, token, binding, evidence):
        if token is not _FIXTURE_TOKEN:
            raise TypeError("production source fixture is composition-root only")
        instance = cls()
        identity = binding["generator_identity"]
        key = identity["source_id"], identity["source_version"], binding["generator_execution_id"]
        instance.__installed_index = MappingProxyType({key: deepcopy(dict(binding))})
        instance.__generation_evidence = MappingProxyType({key: evidence})
        return instance

    def resolve_source_binding(self, generator_identity, generator_execution_id):
        key = (
            generator_identity.get("source_id", ""),
            generator_identity.get("source_version", ""),
            generator_execution_id,
        )
        return self.__installed_index.get(key)

    def supports_binding_type(self, binding_type: str) -> bool:
        return binding_type == "generated_only" and bool(self.__installed_index)

    def resolve_generation_execution_evidence(self, generator_identity, generator_execution_id):
        key = (
            generator_identity.get("source_id", ""),
            generator_identity.get("source_version", ""),
            generator_execution_id,
        )
        return self.__generation_evidence.get(key)


PRODUCTION_SOURCE_PROVENANCE_AUTHORITY = ProductionSourceProvenanceResolver()


@contextmanager
def _production_source_provenance_composition_fixture_for_test(
    binding, safe_input_hashes, *, generation_evidence=None,
):
    """Module-private fixture that exercises the real production source entrypoint."""
    global PRODUCTION_SOURCE_PROVENANCE_AUTHORITY
    previous = PRODUCTION_SOURCE_PROVENANCE_AUTHORITY
    identity = binding["generator_identity"]
    evidence = generation_evidence or GenerationExecutionEvidence(
        deepcopy(identity), binding["generator_execution_id"],
        binding["generation_input_fingerprint_schema_version"],
        binding["generation_input_policy_version"], binding["generation_input_domain"],
        tuple(safe_input_hashes),
    )
    PRODUCTION_SOURCE_PROVENANCE_AUTHORITY = ProductionSourceProvenanceResolver._for_composition_test(
        _FIXTURE_TOKEN, binding, evidence,
    )
    try:
        yield
    finally:
        PRODUCTION_SOURCE_PROVENANCE_AUTHORITY = previous
