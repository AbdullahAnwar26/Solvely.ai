"""Strict validation of a Board payload (Story 2.3, AD-4).

The payload is what the web app serializes from Excalidraw:

    {"schema_version": 1, "elements": [...], "app_state": {...}}

Elements are checked against a closed type set and fixed limits (`core.limits`). Any problem
rejects the whole payload: nothing is partially saved. Element keys are not whitelisted (the
Excalidraw element shape evolves), but every value inside an element is bounded: strings by
length, lists by length, objects by key count, numbers by finiteness and magnitude, and nesting
by depth.
"""
import math

from rest_framework.exceptions import ValidationError

from core import limits
from core.errors import ApiError

BOARD_KEYS = frozenset({"schema_version", "elements", "app_state"})
APP_STATE_KEYS = frozenset({"viewBackgroundColor", "scrollX", "scrollY", "zoom"})

# Strings with their own length caps; every other string uses BOARD_STRING_MAX_LENGTH.
_TEXT_KEYS = frozenset({"text", "originalText"})
_BOUNDED_GEOMETRY = ("x", "y", "width", "height")


class RevisionConflict(ApiError):
    """409: the save was based on an older revision; nothing was written."""

    status_code = 409
    default_code = "revision_conflict"
    default_detail = "This lesson was changed elsewhere. Load the latest version to continue."

    def __init__(self, current_revision):
        super().__init__()
        self.extra = {"current_revision": current_revision}


def empty_board():
    return {"schema_version": limits.BOARD_SCHEMA_VERSION, "elements": []}


def _fail(field, message):
    raise ValidationError({field: [message]})


def _is_number(value):
    # bool is an int subclass in Python; JSON booleans are not numbers here.
    return isinstance(value, int | float) and not isinstance(value, bool)


def _finite(value):
    return _is_number(value) and math.isfinite(value)


def validate_board(board):
    """Return `board` unchanged when valid; raise ValidationError (400) otherwise."""
    if not isinstance(board, dict):
        _fail("board", "Must be an object.")
    unknown = set(board) - BOARD_KEYS
    if unknown:
        _fail("board", f"Unknown keys: {', '.join(sorted(map(str, unknown)))}.")
    version = board.get("schema_version")
    if not _is_number(version) or version != limits.BOARD_SCHEMA_VERSION:
        _fail("schema_version", f"Must be {limits.BOARD_SCHEMA_VERSION}.")

    elements = board.get("elements")
    if not isinstance(elements, list):
        _fail("elements", "Must be a list.")
    if len(elements) > limits.BOARD_MAX_ELEMENTS:
        _fail("elements", f"At most {limits.BOARD_MAX_ELEMENTS} elements are allowed.")
    for index, element in enumerate(elements):
        _validate_element(index, element)

    if "app_state" in board:
        _validate_app_state(board["app_state"])
    return board


def _validate_app_state(app_state):
    if not isinstance(app_state, dict):
        _fail("app_state", "Must be an object.")
    unknown = set(app_state) - APP_STATE_KEYS
    if unknown:
        _fail("app_state", f"Unknown keys: {', '.join(sorted(map(str, unknown)))}.")
    background = app_state.get("viewBackgroundColor")
    if background is not None and (
        not isinstance(background, str) or len(background) > limits.BOARD_BACKGROUND_MAX_LENGTH
    ):
        _fail("app_state", "viewBackgroundColor must be a short string.")
    for key in ("scrollX", "scrollY"):
        value = app_state.get(key)
        if value is not None and (
            not _finite(value) or abs(value) > limits.BOARD_COORDINATE_LIMIT
        ):
            _fail("app_state", f"{key} must be a finite number within bounds.")
    if "zoom" in app_state:
        zoom = app_state["zoom"]
        if not isinstance(zoom, dict) or set(zoom) != {"value"}:
            _fail("app_state", "zoom must be {value: number}.")
        value = zoom["value"]
        if not _finite(value) or not limits.BOARD_ZOOM_MIN <= value <= limits.BOARD_ZOOM_MAX:
            _fail("app_state", "zoom.value is out of range.")


def _validate_element(index, element):
    where = f"Element {index}"
    if not isinstance(element, dict):
        _fail("elements", f"{where}: must be an object.")
    element_id = element.get("id")
    if (
        not isinstance(element_id, str)
        or not element_id
        or len(element_id) > limits.BOARD_ELEMENT_ID_MAX_LENGTH
    ):
        _fail("elements", f"{where}: id must be a non-empty string of at most "
              f"{limits.BOARD_ELEMENT_ID_MAX_LENGTH} characters.")
    if element.get("type") not in limits.BOARD_ELEMENT_TYPES:
        _fail("elements", f"{where}: unsupported element type.")
    for key in _BOUNDED_GEOMETRY:
        value = element.get(key)
        if not _finite(value) or abs(value) > limits.BOARD_COORDINATE_LIMIT:
            _fail("elements", f"{where}: {key} must be a finite number within bounds.")

    custom = element.get("customData")
    if custom is not None:
        if not isinstance(custom, dict):
            _fail("elements", f"{where}: customData must be an object.")
        if "origin" in custom and custom["origin"] not in limits.BOARD_ORIGINS:
            _fail("elements", f"{where}: customData.origin must be 'learner' or 'ai'.")

    _validate_value(where, element, depth=1, key=None)


def _string_cap(key):
    if key in _TEXT_KEYS:
        return limits.BOARD_TEXT_MAX_LENGTH
    if key == "link":
        return limits.BOARD_LINK_MAX_LENGTH
    return limits.BOARD_STRING_MAX_LENGTH


def _validate_value(where, value, depth, key):
    """Bound every value inside an element; `key` is the nearest enclosing object key."""
    if depth > limits.BOARD_ELEMENT_MAX_DEPTH:
        _fail("elements", f"{where}: nested too deeply.")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        if len(value) > _string_cap(key):
            _fail("elements", f"{where}: {key or 'a value'} is too long.")
        return
    if _is_number(value):
        if not math.isfinite(value) or abs(value) > limits.BOARD_NUMBER_ABS_MAX:
            _fail("elements", f"{where}: {key or 'a value'} must be a finite number.")
        return
    if isinstance(value, list):
        if len(value) > limits.BOARD_ELEMENT_LIST_MAX:
            _fail("elements", f"{where}: {key or 'a list'} has too many items.")
        for item in value:
            _validate_value(where, item, depth + 1, key)
        return
    if isinstance(value, dict):
        if len(value) > limits.BOARD_ELEMENT_MAX_KEYS:
            _fail("elements", f"{where}: too many keys.")
        for child_key, child in value.items():
            if len(child_key) > limits.BOARD_STRING_MAX_LENGTH:
                _fail("elements", f"{where}: key is too long.")
            _validate_value(where, child, depth + 1, child_key)
        return
    _fail("elements", f"{where}: unsupported value.")
