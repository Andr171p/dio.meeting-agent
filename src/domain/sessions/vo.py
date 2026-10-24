from typing import Self

from dataclasses import dataclass
from datetime import datetime, timedelta

from ddf.domain.exceptions import InvalidStateError


@dataclass(frozen=True, slots=True)
class SessionTimeline:
    """Временной промежуток в котором проходит сессия."""

    started_at: datetime | None = None
    ended_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.ended_at and not self.started_at:
            raise ValueError("Session cannot end without having begun.")

        if self.started_at and self.ended_at and self.ended_at < self.started_at:
            raise ValueError("End date cannot be earlier than the start date.")

    @property
    def duration(self) -> timedelta | None:
        return self.ended_at - self.started_at if self.started_at and self.ended_at else None

    def start(self, now: datetime) -> Self:
        if self.started_at:
            raise InvalidStateError("Session already started.")

        return __class__(started_at=now)

    def end(self, now: datetime) -> Self:
        if not self.started_at:
            raise InvalidStateError("You cannot end a session that has not been started.")

        if self.ended_at:
            raise InvalidStateError("Session already end.")

        return __class__(started_at=self.started_at, ended_at=now)
