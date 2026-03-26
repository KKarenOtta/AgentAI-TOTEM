from __future__ import annotations

from dataclasses import dataclass
from time import time


@dataclass(slots=True)
class SessionPresenceState:
    company_id: str
    device_id: str
    last_seen_ts: float
    active: bool = True


class SessionGuardianAgent:
    def should_end(self, state: SessionPresenceState, timeout_s: int = 15) -> bool:
        return (time() - state.last_seen_ts) > timeout_s
