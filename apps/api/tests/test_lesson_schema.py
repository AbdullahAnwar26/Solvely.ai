import math
from uuid import uuid4

import pytest
from pydantic import ValidationError

from domain.board_operations import (
    BoardOperationError,
    LessonStepValidationError,
    validate_lesson_step,
)
from domain.lesson_schema import LessonStep


def step_id():
    return str(uuid4())


def element(element_id="learner-1", origin="learner", owner_step=None):
    data = {
        "id": element_id,
        "type": "text",
        "x": 0,
        "y": 0,
        "width": 100,
        "height": 20,
        "customData": {"origin": origin},
    }
    if owner_step is not None:
        data["customData"]["stepId"] = owner_step
    return data


def payload(sid, operations, **overrides):
    data = {
        "schema_version": 1,
        "step_id": sid,
        "description": "Add a rectangle.",
        "alt": "A rectangle appears on the board.",
        "completed": False,
        "operations": operations,
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("value", [True, False, 0, 2])
def test_schema_version_rejects_non_integer_one(value):
    with pytest.raises(ValidationError):
        LessonStep.model_validate(payload(step_id(), [], schema_version=value))


def test_schema_version_accepts_integer_one():
    step = LessonStep.model_validate(payload(step_id(), [], schema_version=1))
    assert step.schema_version == 1


def test_valid_add_update_and_remove_are_normalized(sid=None):
    sid = sid or step_id()
    result = validate_lesson_step(payload(sid, [
        {"type": "add_element", "element": {
            "id": "shape1", "type": "rectangle", "x": 10, "y": 20,
            "width": 100, "height": 50, "strokeColor": "#ffffff",
        }},
        {"type": "update_element", "id": "shape1", "changes": {"x": 11}},
        {"type": "highlight_element", "id": "shape1"},
    ]), {"elements": []}, sid)
    operations = result["operations"]
    assert operations[0]["element"]["id"] == f"ai:{sid}:1"
    assert operations[0]["element"]["customData"]["origin"] == "ai"
    assert operations[1]["element_id"] == f"ai:{sid}:1"


def test_model_rejects_unknown_keys_and_operation():
    with pytest.raises(ValidationError):
        LessonStep.model_validate(payload(step_id(), [], unknown=True))
    sid = step_id()
    with pytest.raises(LessonStepValidationError):
        validate_lesson_step(
            payload(sid, [{"type": "rotate", "element_id": "a"}]), {}, sid
        )


@pytest.mark.parametrize("value", [math.inf, -math.inf, float("nan"), 1_000_001])
def test_bad_geometry_is_rejected(value):
    sid = step_id()
    operations = [{"type": "add_element", "element": {
        "id": "shape1", "type": "rectangle", "x": value, "y": 0,
        "width": 10, "height": 10,
    }}]
    with pytest.raises(BoardOperationError):
        validate_lesson_step(payload(sid, operations), {}, sid)


def test_colour_text_operation_and_frame_limits():
    sid = step_id()
    bad = [
        {"type": "add_element", "element": {
            "id": "a", "type": "text", "x": 0, "y": 0, "width": 10, "height": 10,
            "text": "x" * 20_001,
        }},
        {"type": "add_element", "element": {
            "id": "a", "type": "rectangle", "x": 0, "y": 0, "width": 10, "height": 10,
            "strokeColor": "url(javascript:bad)",
        }},
        {"type": "add_element", "element": {
            "id": "a", "type": "frame", "x": 0, "y": 0, "width": 10, "height": 10,
        }},
    ]
    for operations in bad:
        with pytest.raises((BoardOperationError, ValidationError)):
            validate_lesson_step(payload(sid, [operations]), {}, sid)


def test_learner_target_is_rejected():
    sid = step_id()
    with pytest.raises(BoardOperationError) as exc:
        validate_lesson_step(
            payload(sid, [{"type": "remove_element", "id": "learner-1"}]),
            {"elements": [element()]},
            sid,
        )
    assert exc.value.code == "learner_target"


def test_ai_namespace_must_match_original_step():
    sid = step_id()
    owner = step_id()
    wrong = element(f"ai:{sid}:1", "ai", owner)
    with pytest.raises(BoardOperationError) as exc:
        validate_lesson_step(
            payload(sid, [{"type": "remove_element", "id": f"ai:{sid}:1"}]),
            {"elements": [wrong]},
            sid,
        )
    assert exc.value.code == "ownership_namespace_mismatch"


def test_step_echo_must_match():
    sid = step_id()
    with pytest.raises(BoardOperationError) as exc:
        validate_lesson_step(payload(step_id(), []), {}, sid)
    assert exc.value.code == "step_id_mismatch"


def test_repeated_provisional_ids_and_target_count_are_rejected():
    sid = step_id()
    duplicate = {
        "type": "add_element",
        "element": {"id": "a", "type": "rectangle", "x": 0, "y": 0, "width": 1, "height": 1},
    }
    with pytest.raises(BoardOperationError):
        validate_lesson_step(payload(sid, [duplicate, duplicate]), {}, sid)


def test_forward_provisional_reference_is_normalized():
    sid = step_id()
    result = validate_lesson_step(payload(sid, [
        {"type": "update_element", "id": "shape1", "changes": {"x": 11}},
        {"type": "add_element", "element": {
            "id": "shape1", "type": "rectangle", "x": 10, "y": 20,
            "width": 100, "height": 50,
        }},
    ]), {"elements": []}, sid)
    final_id = f"ai:{sid}:1"
    assert result["operations"][0]["element_id"] == final_id
    assert result["operations"][1]["element"]["id"] == final_id


@pytest.mark.parametrize(
    ("operation"),
    [
        {"type": "set_viewport", "x": math.inf, "y": 0, "zoom": 1},
        {"type": "set_viewport", "x": 0, "y": 0, "zoom": 31},
    ],
)
def test_invalid_viewport_is_rejected(operation):
    sid = step_id()
    with pytest.raises((BoardOperationError, ValidationError)):
        validate_lesson_step(payload(sid, [operation]), {}, sid)


def test_invalid_opacity_is_rejected():
    sid = step_id()
    operation = {"type": "update_element", "id": "learner-1", "changes": {"opacity": 2}}
    with pytest.raises((BoardOperationError, ValidationError)):
        validate_lesson_step(
            payload(sid, [operation]), {"elements": [element()]}, sid
        )


def test_remove_then_update_is_rejected():
    sid = step_id()
    operations = [
        {"type": "remove_element", "id": "learner-2"},
        {"type": "update_element", "id": "learner-2", "changes": {"x": 1}},
    ]
    with pytest.raises(BoardOperationError):
        validate_lesson_step(
            payload(sid, operations),
            {"elements": [element("learner-2", origin="ai", owner_step=sid)]},
            sid,
        )


def test_unowned_ai_element_is_rejected():
    sid = step_id()
    with pytest.raises(BoardOperationError) as exc:
        validate_lesson_step(
            payload(sid, [{"type": "highlight_element", "id": "ai:missing"}]),
            {"elements": [element("ai:missing", origin="ai")]},
            sid,
        )
    assert exc.value.code == "unowned_ai_element"


def add_rectangle(provisional="shape1"):
    return {"type": "add_element", "element": {
        "id": provisional, "type": "rectangle", "x": 10, "y": 20, "width": 100, "height": 50,
    }}


def test_valid_set_viewport_alone_is_accepted_and_has_no_target_or_origin_tag():
    sid = step_id()
    viewport = {"type": "set_viewport", "x": 5, "y": -5, "zoom": 1.5}

    result = validate_lesson_step(payload(sid, [viewport]), {"elements": []}, sid)

    assert result["operations"] == [viewport]


def test_set_viewport_mixed_with_other_operations_keeps_order_and_server_ids():
    sid = step_id()
    viewport = {"type": "set_viewport", "x": 0, "y": 0, "zoom": 1}

    result = validate_lesson_step(
        payload(sid, [add_rectangle(), viewport, {"type": "highlight_element", "id": "shape1"}]),
        {"elements": []},
        sid,
    )

    kinds = [op["type"] for op in result["operations"]]
    assert kinds == ["add_element", "set_viewport", "highlight_element"]
    assert result["operations"][0]["element"]["id"] == f"ai:{sid}:1"
    assert result["operations"][2]["element_id"] == f"ai:{sid}:1"
    assert "origin" not in result["operations"][1]


def test_set_viewport_does_not_count_as_a_target_or_an_added_element():
    from core import limits

    sid = step_id()
    viewports = [
        {"type": "set_viewport", "x": 0, "y": 0, "zoom": 1}
        for _ in range(min(limits.LESSON_MAX_OPERATIONS, 20))
    ]

    result = validate_lesson_step(payload(sid, viewports), {"elements": []}, sid)

    assert len(result["operations"]) == len(viewports)


def test_set_viewport_cannot_hide_a_learner_target_in_the_same_step():
    sid = step_id()
    ops = [
        {"type": "set_viewport", "x": 0, "y": 0, "zoom": 1},
        {"type": "remove_element", "id": "learner-1"},
    ]

    with pytest.raises(BoardOperationError) as error:
        validate_lesson_step(payload(sid, ops), {"elements": [element()]}, sid)

    assert error.value.code == "learner_target"
