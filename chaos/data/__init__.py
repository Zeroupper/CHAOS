"""Data module - data source management."""

from .base import BaseDataSource
from .registry import DataRegistry

__all__ = ["BaseDataSource", "DataRegistry"]
