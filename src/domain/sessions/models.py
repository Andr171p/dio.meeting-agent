from dataclasses import dataclass
from uuid import UUID

from ddf.domain.models import AggregateRoot

from .vo import SessionTimeline


@dataclass(kw_only=True)
class MeetingSession(AggregateRoot):
    """"""

    organization_id: UUID
    agent_profile_id: UUID
    communication_id: UUID | None = None

    url: str
    platform: str

    status: ...
    timeline: SessionTimeline
