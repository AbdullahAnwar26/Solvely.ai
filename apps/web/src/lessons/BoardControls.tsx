import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";
import { useEffect, useState } from "react";
import { MAX_ZOOM, MIN_ZOOM, fitToContent, nextZoom, zoomTo } from "./viewport";

type Props = {
  api: ExcalidrawImperativeAPI | null;
  zoom: number;
  hasContent: boolean;
};

/**
 * App-level viewport controls for the Board. Undo and redo are not here on purpose: the
 * documented Excalidraw API has no undo/redo method, so Excalidraw's own built-in controls and
 * Ctrl/Cmd+Z shortcuts are used (see ARCHITECTURE_NOTES).
 */
export default function BoardControls({ api, zoom, hasContent }: Props) {
  const percent = `${Math.round(zoom * 100)}%`;
  // Announce the settled zoom only, so a pinch gesture does not flood the screen reader.
  const [announced, setAnnounced] = useState(percent);
  useEffect(() => {
    const timer = window.setTimeout(() => setAnnounced(percent), 300);
    return () => window.clearTimeout(timer);
  }, [percent]);
  const ready = api !== null;
  // Compare after rounding the way the label does, so a button never disables early.
  const atMin = zoom <= MIN_ZOOM + 0.0005;
  const atMax = zoom >= MAX_ZOOM - 0.0005;

  return (
    <div className="board-controls" role="toolbar" aria-label="Board view">
      <button
        type="button"
        className="board-control"
        aria-label="Zoom out"
        disabled={!ready || atMin}
        onClick={() => api && zoomTo(api, nextZoom(zoom, -1))}
      >
        <span aria-hidden="true">−</span>
      </button>
      <button
        type="button"
        className="board-control board-control-wide"
        aria-label="Reset zoom to 100%"
        disabled={!ready}
        onClick={() => api && zoomTo(api, 1)}
      >
        <span aria-hidden="true">{percent}</span>
      </button>
      <button
        type="button"
        className="board-control"
        aria-label="Zoom in"
        disabled={!ready || atMax}
        onClick={() => api && zoomTo(api, nextZoom(zoom, 1))}
      >
        <span aria-hidden="true">+</span>
      </button>
      <button
        type="button"
        className="board-control board-control-wide"
        aria-label="Fit to content"
        disabled={!ready || !hasContent}
        onClick={() => api && fitToContent(api)}
      >
        Fit
      </button>
      <span role="status" aria-live="polite" className="visually-hidden">
        {`Zoom ${announced}`}
      </span>
    </div>
  );
}
