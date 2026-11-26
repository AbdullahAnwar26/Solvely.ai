"""Versioned, framework-free provider output schemas."""

import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core import limits

PROVISIONAL_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ElementData(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    type: str
    x: float | int
    y: float | int
    width: float | int
    height: float | int
    text: str | None = Field(default=None, max_length=limits.LESSON_ELEMENT_TEXT_MAX_LENGTH)
    strokeColor: str | None = Field(default=None, max_length=32)
    backgroundColor: str | None = Field(default=None, max_length=32)
    angle: float | int | None = None

    @field_validator("id")
    @classmethod
    def valid_provisional_id(cls, value: str) -> str:
        if not PROVISIONAL_ID_PATTERN.fullmatch(value) or value.startswith("ai:"):
            raise ValueError("Invalid provisional element id")
        return value


class AddElement(_StrictModel):
    type: Literal["add_element"]
    element: ElementData


class UpdateElement(_StrictModel):
    type: Literal["update_element"]
    element_id: str | None = Field(default=None, min_length=1, max_length=64)
    id: str | None = Field(default=None, min_length=1, max_length=64)
    changes: dict[str, object]

    @model_validator(mode="after")
    def target(self):
        if (self.element_id is None) == (self.id is None):
            raise ValueError("Exactly one of element_id or id is required")
        return self


class RemoveElement(_StrictModel):
    type: Literal["remove_element"]
    element_id: str | None = Field(default=None, min_length=1, max_length=64)
    id: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def target(self):
        if (self.element_id is None) == (self.id is None):
            raise ValueError("Exactly one of element_id or id is required")
        return self


class HighlightElement(_StrictModel):
    type: Literal["highlight_element"]
    element_id: str | None = Field(default=None, min_length=1, max_length=64)
    id: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def target(self):
        if (self.element_id is None) == (self.id is None):
            raise ValueError("Exactly one of element_id or id is required")
        return self


class Viewport(_StrictModel):
    type: Literal["set_viewport"]
    x: float | int
    y: float | int
    zoom: float | int

    @field_validator("x", "y")
    @classmethod
    def bounded_coordinates(cls, value: float | int) -> float | int:
        from math import isfinite

        if isinstance(value, bool) or not isfinite(value) or abs(value) > 1_000_000:
            raise ValueError("Viewport coordinate is out of range")
        return value

    @field_validator("zoom")
    @classmethod
    def bounded_zoom(cls, value: float | int) -> float | int:
        from math import isfinite

        if isinstance(value, bool) or not isfinite(value) or not 0.1 <= value <= 30:
            raise ValueError("Viewport zoom is out of range")
        return value


BoardOperation = Annotated[
    AddElement | UpdateElement | RemoveElement | HighlightElement | Viewport,
    Field(discriminator="type"),
]


class LessonStep(_StrictModel):
    schema_version: Literal[1] = 1
    step_id: UUID
    description: str = Field(min_length=1, max_length=2000)
    alt: str = Field(min_length=1, max_length=2000)
    completed: bool = False
    operations: list[BoardOperation] = Field(max_length=100)

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_schema_version(cls, value: object) -> object:
        if type(value) is not int or value != 1:
            raise ValueError("schema_version must be integer 1")
        return value
