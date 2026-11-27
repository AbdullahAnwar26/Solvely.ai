"""Deterministic layout of generated Step content (AD-2, FR-8).

The provider describes *what* to draw (solution lines, a flowchart, a concept map or a code
walkthrough); this module decides *where*. It returns ordinary `add_element` operations with
provisional ids plus one `set_viewport`, ready to go through `validate_lesson_step`. The same
input and Board always give the same output.

Guarantees: no two content blocks (containers, free text, edge labels, and anything already on
the Board) overlap, every text sits inside its container with padding, and the viewport fits the
Step's content on the reference canvas. Arrows are connectors and are excluded from the overlap
rule; a long arrow can cross an unrelated box (see deferred-work).

The operation schema has no `points` or font size, so an arrow is a thin element of the arrow's
length rotated by `angle`, and text is measured for Excalidraw's default font (see core.limits).
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from core import limits

from .board_operations import BoardOperationError, _board_elements
from .lesson_schema import PROVISIONAL_ID_PATTERN

LAYOUT_VERSION = 1


class LayoutError(BoardOperationError):
    """Content that cannot be laid out legibly. Codes: invalid_layout_content, layout_too_large,
    layout_unfit."""


# --- Input content -----------------------------------------------------------------------------


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _text(max_length: int, min_length: int = 1):
    return Field(min_length=min_length, max_length=max_length)


class SequentialSolution(_Model):
    kind: Literal["sequential_solution"]
    lines: list[str] = Field(min_length=1, max_length=limits.LAYOUT_MAX_SOLUTION_LINES)

    @field_validator("lines")
    @classmethod
    def lines_bounded(cls, value: list[str]) -> list[str]:
        for line in value:
            if not line.strip() or len(line) > limits.LAYOUT_LINE_MAX_LENGTH:
                raise ValueError("Solution lines must be 1 to 300 non-blank characters")
        return value


class GraphNode(_Model):
    id: str
    text: str = _text(limits.LAYOUT_NODE_TEXT_MAX_LENGTH)
    shape: Literal["process", "decision", "terminal"] = "process"

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if not PROVISIONAL_ID_PATTERN.fullmatch(value):
            raise ValueError("Invalid node id")
        return value

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Node text must not be blank")
        return value


class GraphEdge(_Model):
    source: str
    target: str
    label: str | None = Field(default=None, max_length=limits.LAYOUT_LABEL_MAX_LENGTH)

    @field_validator("label")
    @classmethod
    def label_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Edge label must not be blank")
        return value


class _Graph(_Model):
    nodes: list[GraphNode] = Field(min_length=1, max_length=limits.LAYOUT_MAX_NODES)
    edges: list[GraphEdge] = Field(default_factory=list, max_length=limits.LAYOUT_MAX_EDGES)

    @model_validator(mode="after")
    def consistent(self):
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("Node ids must be unique")
        known = set(ids)
        seen: set[tuple[str, str]] = set()
        for edge in self.edges:
            if edge.source not in known or edge.target not in known:
                raise ValueError("An edge references an unknown node")
            if edge.source == edge.target:
                raise ValueError("An edge cannot connect a node to itself")
            pair = (edge.source, edge.target)
            if pair in seen:
                raise ValueError("Duplicate edge")
            seen.add(pair)
        return self


class Flowchart(_Graph):
    kind: Literal["flowchart"]


class ConceptMap(_Graph):
    kind: Literal["concept_map"]


class CodeLine(_Model):
    code: str = Field(max_length=limits.LAYOUT_CODE_LINE_MAX_LENGTH)
    note: str | None = Field(default=None, max_length=limits.LAYOUT_NOTE_MAX_LENGTH)

    @field_validator("note")
    @classmethod
    def note_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Note must not be blank")
        return value


class CodeWalkthrough(_Model):
    kind: Literal["code_walkthrough"]
    lines: list[CodeLine] = Field(min_length=1, max_length=limits.LAYOUT_MAX_CODE_LINES)


LayoutContent = Annotated[
    SequentialSolution | Flowchart | ConceptMap | CodeWalkthrough,
    Field(discriminator="kind"),
]
_CONTENT = TypeAdapter(LayoutContent)


# --- Geometry and text measuring --------------------------------------------------------------


@dataclass(frozen=True)
class _Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def overlaps(self, other: "_Box") -> bool:
        return (
            self.x < other.right
            and other.x < self.right
            and self.y < other.bottom
            and other.y < self.bottom
        )


def _cells(char: str) -> int:
    return 2 if ord(char) > 127 else 1


def _width_cells(text: str) -> int:
    return sum(_cells(char) for char in text)


def _chunks(word: str, max_cells: int) -> list[str]:
    pieces, current, used = [], "", 0
    for char in word:
        width = _cells(char)
        if used + width > max_cells:
            pieces.append(current)
            current, used = "", 0
        current += char
        used += width
    if current:
        pieces.append(current)
    return pieces


def _wrap_prose(text: str, max_cells: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            pieces = _chunks(word, max_cells) if _width_cells(word) > max_cells else [word]
            for piece in pieces:
                candidate = piece if not current else f"{current} {piece}"
                if _width_cells(candidate) <= max_cells:
                    current = candidate
                else:
                    lines.append(current)
                    current = piece
        lines.append(current)
    while len(lines) > 1 and not lines[-1]:
        lines.pop()
    return lines


def _wrap_code(text: str, max_cells: int) -> list[str]:
    lines: list[str] = []
    for raw in text.expandtabs(4).split("\n"):
        lines.extend(_chunks(raw, max_cells) if raw else [""])
    return lines


def _measure(lines: list[str]) -> tuple[int, int]:
    widest = max((_width_cells(line) for line in lines), default=1)
    return max(widest, 1) * limits.LAYOUT_CELL_WIDTH, len(lines) * limits.LAYOUT_LINE_HEIGHT


def _round(value: float) -> float:
    return round(value, 2)


@dataclass
class _Layout:
    operations: list[dict[str, Any]] = field(default_factory=list)
    blocks: list[_Box] = field(default_factory=list)
    arrows: list[_Box] = field(default_factory=list)
    _counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def add(
        self,
        prefix: str,
        element_type: str,
        box: _Box,
        text: str | None = None,
        angle: float | None = None,
    ) -> None:
        self._counts[prefix] += 1
        element: dict[str, Any] = {
            "id": f"{prefix}-{self._counts[prefix]}",
            "type": element_type,
            "x": _round(box.x),
            "y": _round(box.y),
            "width": _round(box.w),
            "height": _round(box.h),
        }
        if text is not None:
            element["text"] = text
        if angle is not None:
            element["angle"] = _round(angle)
        self.operations.append({"type": "add_element", "element": element})

    def add_text(self, prefix: str, lines: list[str], x: float, y: float) -> _Box:
        width, height = _measure(lines)
        box = _Box(x, y, width, height)
        self.add(prefix, "text", box, "\n".join(lines))
        return box


# --- Builders ---------------------------------------------------------------------------------


def _sequential(content: SequentialSolution, ox: float, oy: float) -> _Layout:
    layout = _Layout()
    y = oy
    for line in content.lines:
        box = layout.add_text("line", _wrap_prose(line, limits.LAYOUT_PROSE_CELLS), ox, y)
        layout.blocks.append(box)
        y += box.h + limits.LAYOUT_PADDING
    return layout


def _code(content: CodeWalkthrough, ox: float, oy: float) -> _Layout:
    layout = _Layout()
    pad = limits.LAYOUT_PADDING
    rows = []
    for item in content.lines:
        code_lines = _wrap_code(item.code, limits.LAYOUT_CODE_CELLS)
        note_lines = _wrap_prose(item.note, limits.LAYOUT_NOTE_CELLS) if item.note else None
        code_size = _measure(code_lines)
        note_size = _measure(note_lines) if note_lines else (0, 0)
        rows.append((code_lines, note_lines, code_size, note_size))

    code_width = max(row[2][0] for row in rows)
    row_gap = limits.LAYOUT_LINE_HEIGHT // 5
    panel_height = 2 * pad + sum(max(r[2][1], r[3][1]) for r in rows) + row_gap * (len(rows) - 1)
    panel = _Box(ox, oy, code_width + 2 * pad, panel_height)
    layout.add("panel", "rectangle", panel)
    layout.blocks.append(panel)

    notes_x = panel.right + limits.LAYOUT_GAP_X
    y = oy + pad
    for code_lines, note_lines, code_size, note_size in rows:
        layout.add_text("code", code_lines, ox + pad, y)  # inside the panel block
        if note_lines:
            layout.blocks.append(layout.add_text("note", note_lines, notes_x, y))
        y += max(code_size[1], note_size[1]) + row_gap
    return layout


_SHAPE_FACTOR = {"process": 1.0, "terminal": 1.5, "decision": 2.0}
_SHAPE_TYPE = {"process": "rectangle", "terminal": "ellipse", "decision": "diamond"}
_MIN_NODE = (100, 56)


def _layers(count: int, pairs: list[tuple[int, int]]) -> tuple[list[int], set[tuple[int, int]]]:
    """Longest-path layering; edges that close a cycle are treated as reversed."""
    adjacent: list[list[int]] = [[] for _ in range(count)]
    for source, target in pairs:
        adjacent[source].append(target)

    state = [0] * count
    finished: list[int] = []
    back: set[tuple[int, int]] = set()
    for root in range(count):
        if state[root]:
            continue
        state[root] = 1
        stack = [(root, 0)]
        while stack:
            node, index = stack.pop()
            if index < len(adjacent[node]):
                stack.append((node, index + 1))
                nxt = adjacent[node][index]
                if state[nxt] == 0:
                    state[nxt] = 1
                    stack.append((nxt, 0))
                elif state[nxt] == 1:
                    back.add((node, nxt))
            else:
                state[node] = 2
                finished.append(node)

    layer = [0] * count
    for node in reversed(finished):
        for nxt in adjacent[node]:
            if (node, nxt) not in back:
                layer[nxt] = max(layer[nxt], layer[node] + 1)
    return layer, back


def _label_box(
    lines: list[str],
    start: tuple[float, float],
    end: tuple[float, float],
    occupied: list[_Box],
) -> _Box:
    width, height = _measure(lines)
    for t in (0.5, 0.4, 0.6, 0.3, 0.7):
        px = start[0] + (end[0] - start[0]) * t
        py = start[1] + (end[1] - start[1]) * t
        for x in (px + 8, px - 8 - width):
            candidate = _Box(x, py - height / 2, width, height)
            if not any(candidate.overlaps(block) for block in occupied):
                return candidate
    raise LayoutError("layout_unfit", "An edge label could not be placed without overlap.")


def _graph(content: Flowchart | ConceptMap, ox: float, oy: float, existing: list[_Box]) -> _Layout:
    layout = _Layout()
    pad = limits.LAYOUT_PADDING
    index = {node.id: i for i, node in enumerate(content.nodes)}
    pairs = [(index[e.source], index[e.target]) for e in content.edges]
    layer, _ = _layers(len(content.nodes), pairs)

    sizes: list[tuple[list[str], int, int, str]] = []
    for node in content.nodes:
        shape = "terminal" if isinstance(content, ConceptMap) else node.shape
        lines = _wrap_prose(node.text, limits.LAYOUT_NODE_CELLS)
        text_w, text_h = _measure(lines)
        factor = _SHAPE_FACTOR[shape]
        width = max(math.ceil(factor * text_w + 2 * pad), _MIN_NODE[0])
        height = max(math.ceil(factor * text_h + 2 * pad), _MIN_NODE[1])
        sizes.append((lines, width, height, shape))

    # Layers are spaced so the tallest edge label fits between them with padding.
    label_height = max(
        (
            _measure(_wrap_prose(edge.label, limits.LAYOUT_LABEL_CELLS))[1]
            for edge in content.edges
            if edge.label
        ),
        default=0,
    )
    gap_y = max(limits.LAYOUT_GAP_Y, label_height + 2 * pad)

    rows: dict[int, list[int]] = defaultdict(list)
    for i, level in enumerate(layer):
        rows[level].append(i)
    row_widths = {
        level: sum(sizes[i][1] for i in members) + limits.LAYOUT_GAP_X * (len(members) - 1)
        for level, members in rows.items()
    }
    widest = max(row_widths.values())

    boxes: dict[int, _Box] = {}
    y = oy
    for level in sorted(rows):
        members = rows[level]
        band = max(sizes[i][2] for i in members)
        x = ox + (widest - row_widths[level]) / 2
        for i in members:
            lines, width, height, shape = sizes[i]
            box = _Box(x, y + (band - height) / 2, width, height)
            boxes[i] = box
            layout.add("node", _SHAPE_TYPE[shape], box)
            text_w, text_h = _measure(lines)
            layout.add_text(
                "text", lines, box.x + (width - text_w) / 2, box.y + (height - text_h) / 2
            )
            layout.blocks.append(box)
            x += width + limits.LAYOUT_GAP_X
        y += band + gap_y

    for edge, (source, target) in zip(content.edges, pairs, strict=True):
        src, dst = boxes[source], boxes[target]
        forward = layer[target] > layer[source]
        start = (src.x + src.w / 2, src.bottom if forward else src.y)
        end = (dst.x + dst.w / 2, dst.y if forward else dst.bottom)
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        arrow = _Box(mid[0] - length / 2, mid[1] - 0.5, length, 1)
        layout.add("arrow", "arrow", arrow, angle=math.atan2(end[1] - start[1], end[0] - start[0]))
        layout.arrows.append(
            _Box(
                min(start[0], end[0]),
                min(start[1], end[1]),
                abs(end[0] - start[0]),
                abs(end[1] - start[1]),
            )
        )
        if edge.label:
            lines = _wrap_prose(edge.label, limits.LAYOUT_LABEL_CELLS)
            box = _label_box(lines, start, end, layout.blocks + existing)
            layout.add("label", "text", box, "\n".join(lines))
            layout.blocks.append(box)
    return layout


# --- Placement, viewport and entry point -------------------------------------------------------


def _existing_boxes(board_state: object) -> list[_Box]:
    """Conservative bounds of what is already on the Board (rotation widened to a circle)."""
    boxes: list[_Box] = []
    for element in _board_elements(board_state):
        if element.get("isDeleted") is True:
            continue
        values = [element.get(key) for key in ("x", "y", "width", "height")]
        if not all(isinstance(v, int | float) and not isinstance(v, bool) for v in values):
            continue
        x, y, w, h = values
        if not all(math.isfinite(v) for v in values):
            continue
        angle = element.get("angle")
        if isinstance(angle, int | float) and not isinstance(angle, bool) and angle:
            radius = math.hypot(w, h) / 2
            boxes.append(_Box(x + w / 2 - radius, y + h / 2 - radius, 2 * radius, 2 * radius))
        else:
            boxes.append(_Box(x, y, abs(w), abs(h)))
    return boxes


def _origin(existing: list[_Box]) -> tuple[float, float]:
    if not existing:
        return 0.0, 0.0
    return (
        min(box.x for box in existing),
        max(box.bottom for box in existing) + limits.LAYOUT_SECTION_GAP,
    )


def _viewport(bounds: _Box) -> dict[str, Any]:
    margin = limits.LAYOUT_VIEWPORT_MARGIN
    fit_w = (limits.LAYOUT_CANVAS_WIDTH - 2 * margin) / max(bounds.w, 1)
    fit_h = (limits.LAYOUT_CANVAS_HEIGHT - 2 * margin) / max(bounds.h, 1)
    zoom = math.floor(min(1.0, fit_w, fit_h) * 100) / 100
    if zoom < limits.LAYOUT_MIN_ZOOM:
        raise LayoutError(
            "layout_too_large", "The content is too large to show legibly in one Step."
        )
    visible_w = limits.LAYOUT_CANVAS_WIDTH / zoom
    visible_h = limits.LAYOUT_CANVAS_HEIGHT / zoom
    return {
        "type": "set_viewport",
        "x": _round((visible_w - bounds.w) / 2 - bounds.x),
        "y": _round((visible_h - bounds.h) / 2 - bounds.y),
        "zoom": zoom,
    }


def layout_lesson_content(
    content: dict[str, Any] | LayoutContent, board_state: object = None
) -> list[dict[str, Any]]:
    """Lay out `content` below whatever is on the Board.

    Returns the Step's Board Operations: `add_element` operations with provisional ids, then one
    `set_viewport`. Raises LayoutError; nothing is partially returned.
    """
    try:
        parsed = _CONTENT.validate_python(content)
    except ValidationError as exc:
        raise LayoutError("invalid_layout_content", str(exc)) from exc

    existing = _existing_boxes(board_state)
    ox, oy = _origin(existing)
    if isinstance(parsed, SequentialSolution):
        layout = _sequential(parsed, ox, oy)
    elif isinstance(parsed, CodeWalkthrough):
        layout = _code(parsed, ox, oy)
    else:
        layout = _graph(parsed, ox, oy, existing)

    added = len(layout.operations)
    if added + 1 > limits.LESSON_MAX_OPERATIONS or added > limits.LESSON_MAX_ADDED_ELEMENTS:
        raise LayoutError("layout_too_large", "The content needs too many Board elements.")

    for i, block in enumerate(layout.blocks):
        if any(block.overlaps(other) for other in layout.blocks[i + 1 :] + existing):
            raise LayoutError("layout_unfit", "Laid out content would overlap.")

    extent = layout.blocks + layout.arrows
    left = min(box.x for box in extent)
    top = min(box.y for box in extent)
    bounds = _Box(
        left,
        top,
        max(box.right for box in extent) - left,
        max(box.bottom for box in extent) - top,
    )
    limit = limits.BOARD_COORDINATE_LIMIT
    for op in layout.operations:
        element = op["element"]
        if any(abs(element[key]) > limit for key in ("x", "y", "width", "height")):
            raise LayoutError("layout_unfit", "The content falls outside the Board limits.")
    return [*layout.operations, _viewport(bounds)]
