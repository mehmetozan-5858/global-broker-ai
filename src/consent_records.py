"""Auditable consent records used by the private-room access gate."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable

VALID_PARTIES = {"buyer", "seller"}
VALID_ACTIONS = {"grant", "revoke"}


@dataclass(frozen=True)
class ConsentEvent:
    opportunity_id: str
    party: str
    actor_id: str
    action: str
    timestamp: str
    purpose: str = "contact_introduction"
    evidence_ref: str = ""

    def validate(self) -> "ConsentEvent":
        if not self.opportunity_id.strip():
            raise ValueError("opportunity_id_required")
        if self.party not in VALID_PARTIES:
            raise ValueError("invalid_party")
        if not self.actor_id.strip():
            raise ValueError("actor_id_required")
        if self.action not in VALID_ACTIONS:
            raise ValueError("invalid_action")
        if self.purpose != "contact_introduction":
            raise ValueError("invalid_purpose")
        try:
            parsed = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid_timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError("timezone_required")
        return self

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)


def new_event(opportunity_id: str, party: str, actor_id: str, action: str,
              *, evidence_ref: str = "", now: datetime | None = None) -> ConsentEvent:
    moment = now or datetime.now(timezone.utc)
    return ConsentEvent(
        opportunity_id=opportunity_id,
        party=party,
        actor_id=actor_id,
        action=action,
        timestamp=moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        evidence_ref=evidence_ref,
    ).validate()


def current_consent(events: Iterable[ConsentEvent], opportunity_id: str, party: str) -> bool:
    if party not in VALID_PARTIES:
        raise ValueError("invalid_party")
    relevant = []
    for event in events:
        event.validate()
        if event.opportunity_id == opportunity_id and event.party == party:
            relevant.append(event)
    if not relevant:
        return False
    latest = max(relevant, key=lambda e: datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")))
    return latest.action == "grant"


def mutual_consent(events: Iterable[ConsentEvent], opportunity_id: str) -> bool:
    snapshot = list(events)
    return current_consent(snapshot, opportunity_id, "buyer") and current_consent(snapshot, opportunity_id, "seller")
