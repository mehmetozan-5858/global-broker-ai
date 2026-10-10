from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RecoveryState:
    email_verified: bool
    phone_verified: bool
    sms_provider_verified: bool
    aal2: bool

    @property
    def ready(self) -> bool:
        return all((self.email_verified, self.phone_verified, self.sms_provider_verified, self.aal2))

    def as_dict(self) -> dict[str, Any]:
        blockers: list[str] = []
        if not self.email_verified:
            blockers.append("email_verification")
        if not self.phone_verified:
            blockers.append("phone_verification")
        if not self.sms_provider_verified:
            blockers.append("sms_provider")
        if not self.aal2:
            blockers.append("aal2_session")
        return {
            "ready": self.ready,
            "email_verified": self.email_verified,
            "phone_verified": self.phone_verified,
            "sms_provider_verified": self.sms_provider_verified,
            "aal2": self.aal2,
            "blockers": blockers,
            "rule": "Admin recovery and privileged access require independently verified email and phone factors plus an AAL2 session. No single-channel bypass is allowed.",
        }


def evaluate_enrollment(record: dict[str, Any] | None, *, jwt_aal: str | None) -> dict[str, Any]:
    record = record or {}
    state = RecoveryState(
        email_verified=bool(record.get("email_verified_at")),
        phone_verified=bool(record.get("phone_verified_at") and record.get("phone_factor_id")),
        sms_provider_verified=record.get("sms_provider_verified") is True,
        aal2=(jwt_aal or "").lower() == "aal2",
    )
    return state.as_dict()


def can_grant_admin(record: dict[str, Any] | None) -> bool:
    record = record or {}
    return bool(
        record.get("enabled") is True
        and record.get("email_verified_at")
        and record.get("phone_verified_at")
        and record.get("phone_factor_id")
        and record.get("sms_provider_verified") is True
    )
