from enum import StrEnum


class ConnectionState(StrEnum):
    """Состояние подключения к встрече"""

    PREPARING = "preparing"
    JOINING = "joining"
    WAITING_FOR_ADMISSION = "waiting_for_admission"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ENDED = "ended"
    UNKNOWN = "unknown"
