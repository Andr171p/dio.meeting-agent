from typing import Protocol

from .types import ConnectionState


class BaseConnector(Protocol):
    async def connect(self) -> ...:
        """Выполняет гостевой сценарий подключения."""

    async def get_state(self) -> ConnectionState:
        """Проверяет реальное состояние участия."""

    async def get_participants(self) -> ...:
        """Получает наблюдаемых участников, если возможно."""

    async def disconnect(self) -> ...:
        """Корректно завершает участие."""
