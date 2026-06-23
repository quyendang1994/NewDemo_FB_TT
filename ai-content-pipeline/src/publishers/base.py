"""Abstract base publisher interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from src.models.schemas import PublishResult


class BasePublisher(ABC):
    @abstractmethod
    def publish(self, content: dict) -> PublishResult:
        """Publish content. Returns PublishResult."""
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if real publishing is configured."""
        ...
