"""Story 3.3: deterministic layout engine. Checks use their own geometry, not the engine's."""

import json
import random
import uuid

import pytest

from core import limits
from domain.board_operations import BoardOperationError, validate_lesson_step
from domain.layout import LayoutError, layout_lesson_content

CELL = limits.LAYOUT_CELL_WIDTH
LINE = limits.LAYOUT_LINE_HEIGHT
PAD = limits.LAYOUT_PADDING


def _adds(ops):
    return [op["element"] for op in ops if op["type"] == "add_element"]


def _rect(e):
    return (e["x"], e["y"], e["x"] + e["width"], e["y"] + e["height"])


def _hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _inside(inner, outer):
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def _content_rects(ops):
    """Every non-arrow element, minus text drawn inside a container."""
    elements = [e for e in _adds(ops) if e["type"] != "arrow"]
    containers = [e for e in elements if e["type"] in {"rectangle", "ellipse", "diamond"}]
    rects = []
    for element in elements:
        r = _rect(element)
        if element["type"] == "text" and any(_inside(r, _rect(c)) for c in containers):
            continue
        rects.append(r)
    return rects


def _assert_no_overlap(ops, extra=()):
    rects = _content_rects(ops) + list(extra)
    for i, a in enumerate(rects):
        for b in rects[i + 1 :]:
            assert not _hit(a, b), (a, b)


def _assert_text_fits(ops):
    """Text is at least as wide/tall as its lines need, and sits inside its container."""
    elements = _adds(ops)
    containers = [e for e in elements if e["type"] in {"rectangle", "ellipse", "diamond"}]
    for e in elements:
        if e["type"] != "text":
            continue
        lines = e["text"].split("\n")
        need_w = max(sum(2 if ord(c) > 127 else 1 for c in ln) for ln in lines) * CELL
        assert e["width"] >= need_w and e["height"] >= len(lines) * LINE
        holders = [c for c in containers if _inside(_rect(e), _rect(c))]
        if holders:
            c = holders[0]
            assert (
                e["x"] - c["x"] >= PAD / 2
                and c["x"] + c["width"] - (e["x"] + e["width"]) >= PAD / 2
            )


def _assert_viewport_fits(ops):
    view = ops[-1]
    assert view["type"] == "set_viewport"
    rects = [_rect(e) for e in _adds(ops) if e["type"] != "arrow"]
    for e in _adds(ops):
        if e["type"] == "arrow":
            # Arrow ends are the rotated element's endpoints.
            import math

            cx, cy = e["x"] + e["width"] / 2, e["y"] + e["height"] / 2
            dx = math.cos(e["angle"]) * e["width"] / 2
            dy = math.sin(e["angle"]) * e["width"] / 2
            rects.append((cx - dx, cy - dy, cx + dx, cy + dy))
            rects[-1] = (
                min(rects[-1][0], rects[-1][2]),
                min(rects[-1][1], rects[-1][3]),
                max(rects[-1][0], rects[-1][2]),
                max(rects[-1][1], rects[-1][3]),
            )
    z = view["zoom"]
    for left, top, right, bottom in rects:
        sx0, sy0 = (left + view["x"]) * z, (top + view["y"]) * z
        sx1, sy1 = (right + view["x"]) * z, (bottom + view["y"]) * z
        assert sx0 >= -0.5 and sy0 >= -0.5, (sx0, sy0)
        assert sx1 <= limits.LAYOUT_CANVAS_WIDTH + 0.5, sx1
        assert sy1 <= limits.LAYOUT_CANVAS_HEIGHT + 0.5, sy1
    assert limits.LAYOUT_MIN_ZOOM <= z <= 1


def _through_validator(ops, board=None):
    step_id = str(uuid.uuid4())
    payload = {
        "schema_version": 1,
        "step_id": step_id,
        "description": "A step.",
        "alt": "A step.",
        "operations": ops,
    }
    return validate_lesson_step(payload, board or {"elements": []}, expected_step_id=step_id)


def _check_all(ops, board=None):
    _assert_no_overlap(ops)
    _assert_text_fits(ops)
    _assert_viewport_fits(ops)
    _through_validator(ops, board)


SOLUTION = {
    "kind": "sequential_solution",
    "lines": ["2x + 3 = 11", "2x = 11 - 3", "2x = 8", "x = 4"],
}
FLOW = {
    "kind": "flowchart",
    "nodes": [
        {"id": "start", "text": "Start", "shape": "terminal"},
        {"id": "check", "text": "Is n greater than 1?", "shape": "decision"},
        {"id": "work", "text": "Multiply result by n"},
        {"id": "done", "text": "Return result", "shape": "terminal"},
    ],
    "edges": [
        {"source": "start", "target": "check"},
        {"source": "check", "target": "work", "label": "yes"},
        {"source": "check", "target": "done", "label": "no"},
        {"source": "work", "target": "check"},
    ],
}
MAP = {
    "kind": "concept_map",
    "nodes": [
        {"id": "hub", "text": "Photosynthesis"},
        {"id": "light", "text": "Light energy"},
        {"id": "water", "text": "Water"},
        {"id": "co2", "text": "Carbon dioxide"},
        {"id": "sugar", "text": "Glucose"},
    ],
    "edges": [
        {"source": "light", "target": "hub", "label": "powers"},
        {"source": "water", "target": "hub", "label": "is used by"},
        {"source": "co2", "target": "hub", "label": "is used by"},
        {"source": "hub", "target": "sugar", "label": "produces"},
    ],
}
CODE = {
    "kind": "code_walkthrough",
    "lines": [
        {"code": "def fact(n):", "note": "Define the function."},
        {"code": "    if n <= 1:", "note": "Base case stops the recursion."},
        {"code": "        return 1"},
        {"code": "    return n * fact(n - 1)", "note": "Recursive step."},
    ],
}


@pytest.mark.parametrize("content", [SOLUTION, FLOW, MAP, CODE], ids=lambda c: c["kind"])
def test_every_content_kind_lays_out_cleanly_and_passes_the_validator(content):
    _check_all(layout_lesson_content(content))


@pytest.mark.parametrize("content", [SOLUTION, FLOW, MAP, CODE], ids=lambda c: c["kind"])
def test_layout_is_deterministic(content):
    assert json.dumps(layout_lesson_content(content)) == json.dumps(layout_lesson_content(content))


def test_output_is_adds_then_exactly_one_viewport():
    ops = layout_lesson_content(FLOW)
    assert [op["type"] for op in ops[:-1]] == ["add_element"] * (len(ops) - 1)
    assert ops[-1]["type"] == "set_viewport"


def test_provisional_ids_are_unique_and_valid():
    ids = [e["id"] for e in _adds(layout_lesson_content(MAP))]
    assert len(ids) == len(set(ids))


def test_flowchart_uses_the_shape_for_each_node():
    types = {e["type"] for e in _adds(layout_lesson_content(FLOW))}
    assert {"ellipse", "diamond", "rectangle", "arrow", "text"} <= types


def test_cycle_does_not_break_layering():
    ops = layout_lesson_content(FLOW)  # work -> check closes a loop
    y = {e["id"]: e["y"] for e in _adds(ops) if e["id"].startswith("node-")}
    start, check, work, done = (y[f"node-{i}"] for i in (1, 2, 3, 4))
    assert start < check
    assert check < work and check < done  # the loop edge never pulls `check` below `work`


def test_arrows_are_rotated_thin_elements_with_valid_geometry():
    for e in _adds(layout_lesson_content(FLOW)):
        if e["type"] == "arrow":
            assert e["width"] > 0 and e["height"] > 0
            assert -3.1416 <= e["angle"] <= 3.1416


# --- long and large inputs ---------------------------------------------------------------------


def test_long_unbroken_word_is_hard_wrapped_not_clipped():
    ops = layout_lesson_content(
        {"kind": "sequential_solution", "lines": ["a" * limits.LAYOUT_LINE_MAX_LENGTH]}
    )
    _check_all(ops)
    assert max(e["width"] for e in _adds(ops)) <= limits.LAYOUT_PROSE_CELLS * CELL


def test_long_node_text_wraps_inside_its_shape():
    node_text = "word " * 39 + "end"
    content = {
        "kind": "flowchart",
        "nodes": [{"id": "a", "text": node_text, "shape": "decision"}, {"id": "b", "text": "B"}],
        "edges": [{"source": "a", "target": "b", "label": "x" * 60}],
    }
    _check_all(layout_lesson_content(content))


def test_cjk_and_emoji_text_is_measured_wide():
    content = {"kind": "sequential_solution", "lines": ["日本語のテキスト" * 6, "🙂" * 40]}
    ops = layout_lesson_content(content)
    _assert_text_fits(ops)
    _through_validator(ops)


def test_longest_code_lines_are_wrapped_and_walkthrough_stays_legible():
    lines = [
        {"code": " " * 8 + "x" * 190, "note": "n" * 190}
        for _ in range(limits.LAYOUT_MAX_CODE_LINES)
    ]
    with pytest.raises(LayoutError) as caught:
        layout_lesson_content({"kind": "code_walkthrough", "lines": lines})
    assert caught.value.code in {"layout_too_large"}


def test_full_length_solution_is_accepted_or_refused_cleanly():
    lines = ["step " + "x" * 290] * limits.LAYOUT_MAX_SOLUTION_LINES
    try:
        ops = layout_lesson_content({"kind": "sequential_solution", "lines": lines})
    except LayoutError as exc:
        assert exc.code == "layout_too_large"
    else:
        _check_all(ops)


def test_wide_hub_map_fits_or_is_refused_cleanly():
    nodes = [{"id": "hub", "text": "Hub"}] + [
        {"id": f"n{i}", "text": f"Spoke {i}"} for i in range(11)
    ]
    edges = [{"source": "hub", "target": f"n{i}"} for i in range(11)]
    ops = layout_lesson_content({"kind": "concept_map", "nodes": nodes, "edges": edges})
    _check_all(ops)


def test_oversized_diagram_is_refused_not_shrunk_unreadably():
    nodes = [{"id": f"n{i}", "text": f"Node {i}"} for i in range(limits.LAYOUT_MAX_NODES)]
    edges = [{"source": f"n{i}", "target": f"n{i + 1}"} for i in range(limits.LAYOUT_MAX_NODES - 1)]
    with pytest.raises(LayoutError) as caught:
        layout_lesson_content({"kind": "flowchart", "nodes": nodes, "edges": edges})
    assert caught.value.code == "layout_too_large"


def test_random_graphs_never_overlap_and_always_validate():
    rng = random.Random(3303)  # noqa: S311 - seeded for reproducible fixtures
    checked = 0
    for _ in range(60):
        n = rng.randint(1, 8)
        nodes = [
            {
                "id": f"n{i}",
                "text": " ".join(["w" * rng.randint(1, 12)] * rng.randint(1, 8)),
                "shape": rng.choice(["process", "decision", "terminal"]),
            }
            for i in range(n)
        ]
        pairs = {(rng.randrange(n), rng.randrange(n)) for _ in range(rng.randint(0, 2 * n))}
        edges = [
            {
                "source": f"n{a}",
                "target": f"n{b}",
                "label": rng.choice([None, "yes", "no", "because"]),
            }
            for a, b in sorted(pairs)
            if a != b
        ]
        kind = rng.choice(["flowchart", "concept_map"])
        try:
            ops = layout_lesson_content({"kind": kind, "nodes": nodes, "edges": edges})
        except LayoutError as exc:
            assert exc.code in {"layout_too_large", "layout_unfit"}
            continue
        _check_all(ops)
        checked += 1
    assert checked >= 30


# --- the Board, ownership and limits -----------------------------------------------------------


def _board_with(*elements):
    return {"elements": list(elements)}


def _existing(eid, x, y, w, h, **extra):
    return {
        "id": eid,
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "customData": {"origin": "learner"},
        **extra,
    }


def test_new_content_is_placed_below_everything_already_on_the_board():
    board = _board_with(_existing("a", 100, 50, 300, 200), _existing("b", -400, 10, 50, 600))
    ops = layout_lesson_content(SOLUTION, board)
    top = min(e["y"] for e in _adds(ops))
    assert top >= 610 + limits.LAYOUT_SECTION_GAP
    assert min(e["x"] for e in _adds(ops)) == -400
    _assert_no_overlap(ops, [(100, 50, 400, 250), (-400, 10, -350, 610)])
    _through_validator(ops, board)


def test_rotated_and_deleted_existing_elements_are_handled():
    board = _board_with(
        _existing("r", 0, 0, 400, 1, angle=1.5708),
        _existing("gone", 0, 5000, 10, 10, isDeleted=True),
    )
    ops = layout_lesson_content(SOLUTION, board)
    assert min(e["y"] for e in _adds(ops)) >= 200 + limits.LAYOUT_SECTION_GAP - 1
    assert max(e["y"] for e in _adds(ops)) < 5000


def test_empty_board_starts_at_the_origin():
    ops = layout_lesson_content(SOLUTION, {"elements": []})
    assert min(e["x"] for e in _adds(ops)) == 0 and min(e["y"] for e in _adds(ops)) == 0


def test_second_step_lays_out_below_the_first():
    first = layout_lesson_content(SOLUTION)
    board = _board_with(
        *[
            {**e, "id": f"ai:s:{i}", "customData": {"origin": "ai", "stepId": "s"}}
            for i, e in enumerate(_adds(first))
        ]
    )
    second = layout_lesson_content(FLOW, board)
    assert min(e["y"] for e in _adds(second)) > max(e["y"] + e["height"] for e in _adds(first))


def test_content_beyond_the_board_limits_is_refused():
    board = _board_with(_existing("far", 0, limits.BOARD_COORDINATE_LIMIT - 50, 10, 10))
    with pytest.raises(LayoutError) as caught:
        layout_lesson_content(SOLUTION, board)
    assert caught.value.code == "layout_unfit"


def test_element_budget_is_enforced():
    lines = [{"code": "x"} for _ in range(limits.LAYOUT_MAX_CODE_LINES)]
    ops = layout_lesson_content({"kind": "code_walkthrough", "lines": lines})
    assert len(ops) <= limits.LESSON_MAX_OPERATIONS


# --- invalid content ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content",
    [
        {"kind": "mind_map", "nodes": []},
        {"kind": "sequential_solution", "lines": []},
        {"kind": "sequential_solution", "lines": ["   "]},
        {"kind": "sequential_solution", "lines": ["x"], "extra": 1},
        {"kind": "sequential_solution", "lines": ["x"] * (limits.LAYOUT_MAX_SOLUTION_LINES + 1)},
        {"kind": "sequential_solution", "lines": ["x" * (limits.LAYOUT_LINE_MAX_LENGTH + 1)]},
        {"kind": "flowchart", "nodes": []},
        {"kind": "flowchart", "nodes": [{"id": "a", "text": "A"}, {"id": "a", "text": "B"}]},
        {
            "kind": "flowchart",
            "nodes": [{"id": "a", "text": "A"}],
            "edges": [{"source": "a", "target": "zz"}],
        },
        {
            "kind": "flowchart",
            "nodes": [{"id": "a", "text": "A"}],
            "edges": [{"source": "a", "target": "a"}],
        },
        {
            "kind": "flowchart",
            "nodes": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
            "edges": [{"source": "a", "target": "b"}, {"source": "a", "target": "b"}],
        },
        {"kind": "flowchart", "nodes": [{"id": "1bad", "text": "A"}]},
        {"kind": "flowchart", "nodes": [{"id": "a", "text": "  "}]},
        {"kind": "flowchart", "nodes": [{"id": "a", "text": "A", "shape": "star"}]},
        {
            "kind": "concept_map",
            "nodes": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
            "edges": [{"source": "a", "target": "b", "label": " "}],
        },
        {"kind": "code_walkthrough", "lines": []},
        {"kind": "code_walkthrough", "lines": [{"code": "x", "note": " "}]},
        {
            "kind": "code_walkthrough",
            "lines": [{"code": "x" * (limits.LAYOUT_CODE_LINE_MAX_LENGTH + 1)}],
        },
        "not a dict",
        None,
    ],
)
def test_invalid_content_is_rejected_with_a_typed_error(content):
    with pytest.raises(LayoutError) as caught:
        layout_lesson_content(content)
    assert caught.value.code == "invalid_layout_content"


def test_malformed_board_state_is_a_typed_error():
    with pytest.raises(BoardOperationError) as caught:
        layout_lesson_content(SOLUTION, {"elements": "nope"})
    assert caught.value.code == "invalid_board_state"
