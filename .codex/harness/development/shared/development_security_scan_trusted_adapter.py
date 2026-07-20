"""Opaque production Security Scanner composition boundary."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Mapping


PRODUCTION_SCANNER_ADAPTER_IDENTITY = "development-security-scanner-adapter-v1"
_ATTESTATION_TOKEN = object()


class _ProductionSecurityScanExecutionAttestation:
    __slots__ = (
        "scanner_id", "scanner_version", "security_policy_version",
        "artifact_type_policy_version", "payload_hash", "scan_evidence_id",
        "scan_evidence_hash", "scan_started_at", "scan_completed_at",
        "adapter_identity", "__token",
    )

    def __init__(self, *, token, evidence: Mapping[str, Any], adapter_identity: str) -> None:
        if token is not _ATTESTATION_TOKEN:
            raise TypeError("production Scanner attestation must be adapter-issued")
        self.scanner_id = evidence["scanner_id"]
        self.scanner_version = evidence["scanner_version"]
        self.security_policy_version = evidence["security_policy_version"]
        self.artifact_type_policy_version = evidence["artifact_type_policy_version"]
        self.payload_hash = evidence["payload_hash"]
        self.scan_evidence_id = evidence["scan_evidence_id"]
        self.scan_evidence_hash = evidence["evidence_hash"]
        self.scan_started_at = evidence["scan_started_at"]
        self.scan_completed_at = evidence["scan_completed_at"]
        self.adapter_identity = adapter_identity
        self.__token = token

    def is_adapter_issued(self) -> bool:
        return self.__token is _ATTESTATION_TOKEN


class _InstalledProductionSecurityScanAuthority:
    __slots__ = ("records", "attestations")

    def __init__(self, records=None, attestations=None) -> None:
        self.records = MappingProxyType(dict(records or {}))
        self.attestations = MappingProxyType(dict(attestations or {}))


_INSTALLED_PRODUCTION_AUTHORITY = _InstalledProductionSecurityScanAuthority()


def _attestation_matches(evidence: Mapping[str, Any], attestation: Any) -> bool:
    return (
        type(attestation) is _ProductionSecurityScanExecutionAttestation
        and attestation.is_adapter_issued()
        and attestation.adapter_identity == PRODUCTION_SCANNER_ADAPTER_IDENTITY
        and attestation.scanner_id == evidence["scanner_id"]
        and attestation.scanner_version == evidence["scanner_version"]
        and attestation.security_policy_version == evidence["security_policy_version"]
        and attestation.artifact_type_policy_version == evidence["artifact_type_policy_version"]
        and attestation.payload_hash == evidence["payload_hash"]
        and attestation.scan_evidence_id == evidence["scan_evidence_id"]
        and attestation.scan_evidence_hash == evidence["evidence_hash"]
        and attestation.scan_started_at == evidence["scan_started_at"]
        and attestation.scan_completed_at == evidence["scan_completed_at"]
    )


def validate_installed_production_scan_evidence(evidence: Mapping[str, Any]) -> bool:
    evidence_id = evidence.get("scan_evidence_id")
    trusted = _INSTALLED_PRODUCTION_AUTHORITY.records.get(evidence_id)
    attestation = _INSTALLED_PRODUCTION_AUTHORITY.attestations.get(evidence_id)
    return trusted == evidence and _attestation_matches(evidence, attestation)


@contextmanager
def _production_scanner_composition_fixture_for_test(
    evidence: Mapping[str, Any], *, adapter_identity: str = PRODUCTION_SCANNER_ADAPTER_IDENTITY,
):
    """Module-private test composition fixture exercising the production adapter boundary.

    It does not expose the attestation type or accept a generic Scanner authority.
    """
    global _INSTALLED_PRODUCTION_AUTHORITY
    previous = _INSTALLED_PRODUCTION_AUTHORITY
    snapshot = deepcopy(dict(evidence))
    evidence_id = snapshot["scan_evidence_id"]
    attestation = _ProductionSecurityScanExecutionAttestation(
        token=_ATTESTATION_TOKEN, evidence=snapshot, adapter_identity=adapter_identity,
    )
    _INSTALLED_PRODUCTION_AUTHORITY = _InstalledProductionSecurityScanAuthority(
        {evidence_id: snapshot}, {evidence_id: attestation},
    )
    try:
        yield
    finally:
        _INSTALLED_PRODUCTION_AUTHORITY = previous
