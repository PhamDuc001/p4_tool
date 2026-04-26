"""
Shared service-layer models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OperationResult:
    success: bool
    message: str
    changelist_id: str | None = None
    changed_files: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfirmationRequest:
    title: str
    message: str
    options: list[str] = field(default_factory=list)


@dataclass
class TuningLoadResult:
    comparison_data: dict[str, Any]
    merged_properties: dict[str, Any]
