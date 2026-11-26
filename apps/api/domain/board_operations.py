"""Atomic, framework-free validation for Lesson Board operations."""

import math
import re
from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from core import limits

from .lesson_schema import AddElement, LessonStep

COORDINATE_LIMIT = limits.BOARD_COORDINATE_LIMIT
NUMBER_LIMIT = limits.BOARD_NUMBER_ABS_MAX
MAX_OPERATIONS = limits.LESSON_MAX_OPERATIONS
MAX_TARGETS = limits.LESSON_MAX_TARGETS
MAX_ADDED_ELEMENTS = limits.LESSON_MAX_ADDED_ELEMENTS
ZOOM_MIN = limits.BOARD_ZOOM_MIN
ZOOM_MAX = limits.BOARD_ZOOM_MAX
PROVIDER_TYPES = limits.LESSON_PROVIDER_ELEMENT_TYPES
PROVISIONAL_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,64}$")
HEX_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")


class BoardOperationError(ValueError):
    """Stable domain error suitable for mapping to provider_invalid_output."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


class LessonStepValidationError(BoardOperationError):
    pass


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _finite(value: object, limit: float = NUMBER_LIMIT) -> bool:
    return _is_number(value) and math.isfinite(value) and abs(value) <= limit


def _custom_data(element: dict[str, Any]) -> dict[str, Any]:
    custom = element.get("customData", {})
    return custom if isinstance(custom, dict) else {}


def _element_id(element: dict[str, Any]) -> object:
    return element.get("id")


def _reject_unknown_operation(value: dict[str, Any]) -> None:
    if value.get("type") not in {
        "add_element",
        "update_element",
        "remove_element",
        "highlight_element",
        "set_viewport",
    }:
        raise BoardOperationError(
            "unknown_board_operation", "The Board operation is not supported."
        )


def _validate_colour(value: object) -> None:
    if not isinstance(value, str) or not (
        HEX_COLOUR.fullmatch(value) or value == "transparent"
    ):
        raise BoardOperationError("invalid_colour", "The element colour is invalid.")


def _validate_geometry(element: dict[str, Any]) -> None:
    for key in ("x", "y", "width", "height"):
        value = element.get(key)
        if not _finite(value, COORDINATE_LIMIT):
            raise BoardOperationError(
                "invalid_geometry", f"{key} must be finite and within board limits."
            )
    if element["width"] <= 0 or element["height"] <= 0:
        raise BoardOperationError("invalid_geometry", "Element dimensions must be positive.")


def _validate_changes(changes: dict[str, Any]) -> None:
    if not changes:
        raise BoardOperationError("partial_operation", "A partial operation is not allowed.")
    allowed = {
        "x", "y", "width", "height", "text", "strokeColor",
        "backgroundColor", "angle", "opacity", "id",
    }
    unknown = set(changes) - allowed
    if unknown:
        raise BoardOperationError("invalid_board_operation", "Unknown element changes.")
    for key in ("x", "y", "width", "height", "angle", "opacity"):
        if key in changes and not _finite(changes[key], COORDINATE_LIMIT):
            raise BoardOperationError("invalid_geometry", "Element geometry is invalid.")
    for key in ("width", "height"):
        if key in changes and changes[key] <= 0:
            raise BoardOperationError("invalid_geometry", "Element dimensions must be positive.")
    max_text = limits.LESSON_ELEMENT_TEXT_MAX_LENGTH
    if "text" in changes and (
        not isinstance(changes["text"], str) or len(changes["text"]) > max_text
    ):
        raise BoardOperationError("oversized_text", "Element text exceeds the fixed limit.")
    if "opacity" in changes and (
        not _finite(changes["opacity"], 1) or not 0 <= changes["opacity"] <= 1
    ):
        raise BoardOperationError("invalid_geometry", "Element opacity must be between 0 and 1.")
    for key in ("strokeColor", "backgroundColor"):
        if key in changes:
            _validate_colour(changes[key])
    if "id" in changes:
        raise BoardOperationError("provider_final_id", "Provider-selected ids are not allowed.")


def _target(op: Any) -> str:
    return op.element_id if op.element_id is not None else op.id


def _parse_step(payload: dict[str, Any], expected_step_id: str | None) -> LessonStep:
    try:
        step = LessonStep.model_validate(payload)
    except ValidationError as exc:
        raise LessonStepValidationError("invalid_lesson_step", str(exc)) from exc
    if expected_step_id is not None and str(step.step_id) != str(expected_step_id):
        raise LessonStepValidationError(
            "step_id_mismatch", "Provider output did not echo the server Step UUID."
        )
    return step


def _board_elements(board_state: object) -> list[dict[str, Any]]:
    if isinstance(board_state, dict):
        elements = board_state.get("elements", [])
    elif isinstance(board_state, Iterable) and not isinstance(board_state, (str, bytes)):
        elements = board_state
    else:
        elements = []
    if not isinstance(elements, list):
        raise BoardOperationError("invalid_board_state", "Board elements must be a list.")
    if not all(isinstance(element, dict) for element in elements):
        raise BoardOperationError("invalid_board_state", "Board elements must be objects.")
    return elements


def _ownership(element: dict[str, Any], element_id: str) -> tuple[str, str | None]:
    custom = _custom_data(element)
    origin = custom.get("origin")
    if origin == "learner" or (origin is None and not str(element_id).startswith("ai:")):
        # Unmarked learner elements are also immutable for Story 3.2.
        return "learner", None
    step_id = custom.get("stepId")
    if origin == "ai" and isinstance(step_id, str) and step_id:
        return "ai", step_id
    return "unowned", None


def validate_lesson_step(
    payload: dict[str, Any],
    board_state: object,
    step_id: str | None = None,
    expected_step_id: str | None = None,
) -> dict[str, Any]:
    """Validate provider output atomically and return the normalized result."""
    expected = expected_step_id if expected_step_id is not None else step_id
    step = _parse_step(payload, expected)
    return normalize_lesson_step(step, board_state)


def normalize_lesson_step(
    step: LessonStep | dict[str, Any],
    board_state: object,
) -> dict[str, Any]:
    if isinstance(step, dict):
        step = _parse_step(step, None)

    operations = step.operations
    if len(operations) > MAX_OPERATIONS:
        raise BoardOperationError("operation_limit", "Too many Board operations.")

    board_elements = _board_elements(board_state)
    existing_ids = [str(_element_id(element)) for element in board_elements]
    if len(existing_ids) != len(set(existing_ids)):
        raise BoardOperationError("invalid_board_state", "Board element ids must be unique.")
    existing = dict(zip(existing_ids, board_elements, strict=True))
    provisional_ids = [op.element.id for op in operations if isinstance(op, AddElement)]
    if len(provisional_ids) != len(set(provisional_ids)):
        raise BoardOperationError("repeated_operation", "A provisional id was reused.")
    provisional = set(provisional_ids)
    if provisional.intersection(existing):
        raise BoardOperationError("repeated_operation", "A provisional id collides with the Board.")
    targets: set[str] = set()
    added = 0
    seen_removes: set[str] = set()

    for op in operations:
        kind = op.type
        if isinstance(op, AddElement):
            added += 1
            element = op.element.model_dump(exclude_none=True)
            if added > MAX_ADDED_ELEMENTS:
                raise BoardOperationError("operation_limit", "Too many added elements.")
            if element["type"] == "frame" or element["type"] not in PROVIDER_TYPES:
                raise BoardOperationError(
                    "unsupported_element_type", "Element type is not allowed."
                )
            _validate_geometry(element)
            text = element.get("text")
            if text is not None and len(text) > limits.LESSON_ELEMENT_TEXT_MAX_LENGTH:
                raise BoardOperationError("oversized_text", "Element text exceeds the fixed limit.")
            for key in ("strokeColor", "backgroundColor"):
                if key in element:
                    _validate_colour(element[key])
            continue

        if kind == "set_viewport":
            # A viewport change targets no element, so there is nothing to look up or own.
            continue

        element_id = _target(op)
        if element_id in provisional and kind in {"remove_element"}:
            raise BoardOperationError("partial_operation", "A provisional reference is incomplete.")
        if kind == "remove_element":
            if element_id in seen_removes:
                raise BoardOperationError("repeated_operation", "An element was removed twice.")
            seen_removes.add(element_id)
        elif element_id in seen_removes:
            raise BoardOperationError("partial_operation", "An element was used after removal.")
        targets.add(element_id)
        if len(targets) > MAX_TARGETS:
            raise BoardOperationError("target_limit", "Too many Board targets.")

        if kind == "update_element":
            _validate_changes(op.changes)
            if element_id in provisional:
                continue
        if element_id in provisional and kind == "highlight_element":
            continue
        if element_id not in existing:
            raise BoardOperationError("unknown_element", "Board target does not exist.")
        origin, owner_step = _ownership(existing[element_id], element_id)
        if origin == "unowned":
            raise BoardOperationError(
                "unowned_ai_element", "AI elements require a valid Step namespace."
            )
        if origin == "learner":
            raise BoardOperationError("learner_target", "Learner elements cannot be modified.")
        if origin == "ai" and owner_step:
            expected_prefix = f"ai:{owner_step}:"
            if not element_id.startswith(expected_prefix):
                raise BoardOperationError(
                    "ownership_namespace_mismatch", "AI Step namespace mismatch."
                )

    # Constructing a normalized copy is deliberately separate from Board mutation.
    final_ids: dict[str, str] = {}
    step_id = str(step.step_id)
    next_number = 1
    for op in operations:
        if isinstance(op, AddElement):
            final_ids[op.element.id] = f"ai:{step_id}:{next_number}"
            next_number += 1

    normalized_operations = []
    for op in operations:
        dump = op.model_dump(exclude_none=True)
        if isinstance(op, AddElement):
            provisional_id = op.element.id
            final_id = final_ids[provisional_id]
            dump["element"]["id"] = final_id
            dump["element"]["customData"] = {"origin": "ai", "stepId": step_id}
        elif op.type != "set_viewport":
            target = _target(op)
            if target in final_ids:
                dump["element_id"] = final_ids[target]
                dump.pop("id", None)
        if not isinstance(op, AddElement) and op.type != "set_viewport":
            dump["origin"] = "ai"
        normalized_operations.append(dump)

    normalized = step.model_dump(mode="json", exclude={"operations"})
    normalized["operations"] = normalized_operations
    return normalized
