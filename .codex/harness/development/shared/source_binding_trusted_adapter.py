"""Sealed production composition boundary for source provenance authority."""
from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from source_binding import SourceBindingAuthority


class ProductionSourceProvenanceResolver(SourceBindingAuthority):
    """Production authority has no caller-supplied store or registration API.

    The future composition root will replace the empty installed index with its
    registered execution store. Until then production provenance fails closed.
    """

    __slots__ = ("__installed_index",)

    def __init__(self) -> None:
        self.__installed_index: Mapping[tuple[str, str, str], Mapping[str, Any]] = MappingProxyType({})

    def resolve_source_binding(self, generator_identity, generator_execution_id):
        key = (
            generator_identity.get("source_id", ""),
            generator_identity.get("source_version", ""),
            generator_execution_id,
        )
        return self.__installed_index.get(key)

    def supports_binding_type(self, binding_type: str) -> bool:
        return False

    def resolve_generation_execution_evidence(self, generator_identity, generator_execution_id):
        return None


PRODUCTION_SOURCE_PROVENANCE_AUTHORITY = ProductionSourceProvenanceResolver()
