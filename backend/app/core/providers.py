"""Shared exceptions for live external data providers."""


class ProviderUnavailableError(Exception):
    """Raised when a live provider cannot return real data (no fake fallback)."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(f"{provider}: {message}")
