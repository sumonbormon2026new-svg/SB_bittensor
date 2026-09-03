import os


def get_network() -> str:
    return os.getenv("BT_API_NETWORK", "finney")


def get_mock() -> bool:
    return os.getenv("BT_API_MOCK", "0").lower() in ("1", "true", "yes", "on")


def get_default_host() -> str:
    return "0.0.0.0"


def get_default_port() -> int:
    return int(os.getenv("PORT") or os.getenv("BT_API_PORT", "8091"))


def get_port_from_settings() -> int:
    return get_default_port()
